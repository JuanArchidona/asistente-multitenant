"""Cliente MCP del sistema: la rama de datos estructurados.

Une las dos mitades del concepto original. El RAG responde con documentos; esto
responde con datos de negocio, hablando el protocolo MCP con los servidores que
el inquilino declara en su manifiesto.

## Por qué hay un hilo con su propio bucle de eventos

El SDK de MCP es asíncrono y el resto del sistema es síncrono, deliberadamente:
el agente, el recuperador y el banco de evaluación son código secuencial y
legible, y convertirlo todo a `async` para acomodar una rama sería pagar un
precio grande por un beneficio nulo. La alternativa contraria —abrir y cerrar el
servidor en cada consulta con `anyio.run`— cuesta el arranque de un proceso por
pregunta.

Así que la sesión vive en un hilo con su propio bucle, se abre una vez y se
reutiliza. El coste de arranque se paga al construir el sistema, no en cada
consulta, que es donde se mide la latencia.

## Fallos, ruidosos

Si un servidor no arranca o una herramienta revienta, se propaga. Un `try`
silencioso aquí convertiría "el CRM está caído" en "no tengo esa información",
que es la confusión más cara posible: el usuario reintenta y nadie investiga.
"""
import asyncio
import json
import sys
import threading
from concurrent.futures import Future
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, Self

from mcp import Client, StdioServerParameters

from .tenant import Tenant

RAIZ = Path(__file__).resolve().parents[1]

# Recorte de la salida de una herramienta antes de dársela al modelo. Un
# resultado enorme se come la ventana de contexto y encarece cada consulta sin
# aportar: si hace falta más, el modelo puede acotar la búsqueda y repetir.
MAX_CARACTERES_RESULTADO = 6000


def recortar_resultado(texto: str) -> str:
    """Acota lo que llega al modelo. Se aplica a lo ya redactado (§41)."""
    if len(texto) > MAX_CARACTERES_RESULTADO:
        return texto[:MAX_CARACTERES_RESULTADO] + "\n[...resultado recortado...]"
    return texto

# Arranque: lanzar un proceso por servidor y negociar el protocolo. Si tarda
# mas que esto, algo va mal y es mejor saberlo en el arranque del sistema.
TIMEOUT_ARRANQUE_S = 30
TIMEOUT_CIERRE_S = 10


class HerramientaMCP:
    """Una herramienta publicada por un servidor, con el servidor del que viene."""

    def __init__(
        self,
        servidor: str,
        nombre: str,
        descripcion: str,
        esquema: dict,
        solo_lectura: bool = False,
    ):
        self.servidor = servidor
        self.nombre = nombre
        self.descripcion = descripcion
        self.esquema = esquema
        # Lo que el servidor declara con `readOnlyHint`. Es una pista del
        # servidor, no una garantia: por eso el manifiesto del inquilino tiene
        # que declarar ademas cada escritura, y las dos cosas se contrastan al
        # abrir. Sin anotacion se asume que ESCRIBE: el error barato es exigir
        # una declaracion de mas; el caro, ejecutar una escritura sin aprobar.
        self.solo_lectura = solo_lectura

    @property
    def nombre_expuesto(self) -> str:
        """Nombre que ve el modelo, con el servidor por delante.

        Dos servidores de un mismo inquilino pueden publicar herramientas
        homónimas; sin prefijo, la llamada sería ambigua y se resolvería por
        orden de carga, que es la peor forma de decidir.
        """
        return f"{self.servidor}__{self.nombre}"


class ClienteMCP:
    """Sesiones abiertas contra los servidores MCP de un inquilino."""

    def __init__(self, tenant: Tenant):
        self.tenant = tenant
        self._bucle: asyncio.AbstractEventLoop | None = None
        self._hilo: threading.Thread | None = None
        self._servicio_futuro: Future | None = None
        self._parar: asyncio.Event | None = None
        self._listo = threading.Event()
        self._fallo: BaseException | None = None
        self._sesiones: dict[str, Client] = {}
        self.herramientas: list[HerramientaMCP] = []

    # --- Ciclo de vida ---

    def abrir(self) -> Self:
        if not self.tenant.servidores_mcp:
            return self
        self._bucle = asyncio.new_event_loop()
        self._hilo = threading.Thread(
            target=self._bucle.run_forever, name=f"mcp-{self.tenant.id}", daemon=True
        )
        self._hilo.start()
        self._servicio_futuro = asyncio.run_coroutine_threadsafe(self._servicio(), self._bucle)
        if not self._listo.wait(timeout=TIMEOUT_ARRANQUE_S):
            self.cerrar()
            raise TimeoutError(
                f"Los servidores MCP de {self.tenant.id!r} no arrancaron en "
                f"{TIMEOUT_ARRANQUE_S} s."
            )
        if self._fallo is not None:
            fallo = self._fallo
            self.cerrar()
            raise fallo
        # Fuera de la tarea del servicio a proposito: un fallo dentro del grupo
        # de tareas de anyio llega envuelto en un ExceptionGroup, y quien abre
        # el cliente tiene que recibir un RuntimeError que diga que pasa.
        try:
            self._contrastar_escrituras()
        except RuntimeError:
            self.cerrar()
            raise
        return self

    def cerrar(self) -> None:
        if self._bucle is None:
            return
        try:
            if self._parar is not None and self._servicio_futuro is not None:
                self._bucle.call_soon_threadsafe(self._parar.set)
                self._servicio_futuro.result(timeout=TIMEOUT_CIERRE_S)
        finally:
            self._bucle.call_soon_threadsafe(self._bucle.stop)
            if self._hilo:
                self._hilo.join(timeout=TIMEOUT_CIERRE_S)
            self._bucle = None
            self._hilo = None
            self._servicio_futuro = None
            self._parar = None
            self._listo.clear()
            self._sesiones.clear()
            self.herramientas.clear()

    def __enter__(self) -> Self:
        return self.abrir()

    def __exit__(self, *_excepcion) -> None:
        self.cerrar()

    # --- Operaciones ---

    def invocar(
        self, nombre_expuesto: str, argumentos: dict[str, Any], recortar: bool = True
    ) -> str:
        """Llama a una herramienta y devuelve su resultado como texto.

        `recortar=False` devuelve el resultado entero. Lo usa el agente para
        redactar ANTES de recortar: recortar un JSON lo deja sin ser JSON, y
        un JSON roto no se puede redactar. Se vio el 23-09-2026 en el servicio
        desplegado (HALLAZGOS.md §41): 6.028 caracteres de un resultado
        recortado a 6.000 pasaron al modelo sin redactar. El recorte sigue
        existiendo, pero se aplica a lo ya redactado (`recortar_resultado`).
        """
        # Primero si el cliente está abierto: si no lo está, la lista de
        # herramientas está vacía y el error sería "esa herramienta no existe",
        # que manda a buscar el fallo al sitio equivocado.
        if self._bucle is None and self.tenant.servidores_mcp:
            raise RuntimeError(
                f"El cliente MCP de {self.tenant.id!r} no está abierto. "
                "Usa abrir() o el context manager."
            )
        herramienta = self.buscar(nombre_expuesto)
        if herramienta is None:
            disponibles = [h.nombre_expuesto for h in self.herramientas]
            raise KeyError(
                f"herramienta {nombre_expuesto!r} no publicada por ningún servidor "
                f"de {self.tenant.id!r}. Disponibles: {disponibles}"
            )
        bruto = self._ejecutar(self._invocar(herramienta, argumentos))
        return recortar_resultado(bruto) if recortar else bruto

    def buscar(self, nombre_expuesto: str) -> HerramientaMCP | None:
        for h in self.herramientas:
            if h.nombre_expuesto == nombre_expuesto:
                return h
        return None

    def esquemas_anthropic(self) -> list[dict[str, Any]]:
        """Traduce las herramientas MCP al formato de tool-calling de Anthropic."""
        return [
            {
                "name": h.nombre_expuesto,
                "description": h.descripcion,
                "input_schema": h.esquema or {"type": "object", "properties": {}},
            }
            for h in self.herramientas
        ]

    # --- Interior asíncrono ---

    def _ejecutar(self, corutina):
        if self._bucle is None:
            raise RuntimeError("El cliente MCP no está abierto. Usa abrir() o el context manager.")
        futuro: Future = asyncio.run_coroutine_threadsafe(corutina, self._bucle)
        return futuro.result()

    async def _servicio(self) -> None:
        """Abre las sesiones, espera, y las cierra. Todo en la misma tarea.

        Es la parte no negociable del diseño: las sesiones del SDK usan ámbitos
        de cancelación de anyio, que **tienen que entrarse y salirse desde la
        misma tarea**. Abrir en una tarea y cerrar en otra revienta al salir con
        un error que no menciona nada de esto. Por eso la sesión no se maneja con
        dos llamadas, sino con una corrutina de larga duración que se queda
        esperando a que le pidan parar.
        """
        self._parar = asyncio.Event()
        try:
            async with AsyncExitStack() as pila:
                await self._conectar(pila)
                self._listo.set()
                await self._parar.wait()
        except BaseException as fallo:
            self._fallo = fallo
            self._listo.set()
            raise

    async def _conectar(self, pila: AsyncExitStack) -> None:
        for definicion in self.tenant.servidores_mcp:
            # 'python' en el manifiesto significa "el mismo intérprete que corre
            # el sistema". Escribir una ruta absoluta ahí ataría el manifiesto a
            # una máquina, y confiar en el PATH del sistema es cómo se acaba
            # hablando con un intérprete que no tiene las dependencias.
            comando = sys.executable if definicion.comando == "python" else definicion.comando
            parametros = StdioServerParameters(
                command=comando, args=definicion.args, cwd=str(RAIZ)
            )
            cliente = await pila.enter_async_context(Client(parametros))
            self._sesiones[definicion.nombre] = cliente
            listado = await cliente.list_tools()
            for herramienta in listado.tools:
                anotaciones = herramienta.annotations
                self.herramientas.append(
                    HerramientaMCP(
                        servidor=definicion.nombre,
                        nombre=herramienta.name,
                        descripcion=herramienta.description or "",
                        esquema=herramienta.input_schema or {},
                        solo_lectura=bool(
                            anotaciones and getattr(anotaciones, "read_only_hint", None) is True
                        ),
                    )
                )

    def _contrastar_escrituras(self) -> None:
        """El servidor y el manifiesto tienen que coincidir sobre que escribe.

        Una herramienta que el servidor no marca como solo lectura y el
        manifiesto no declara como escritura no se puede ofrecer al modelo:
        se ejecutaria sin aprobacion humana. Y una escritura declarada que
        ningun servidor publica es un manifiesto desfasado. Las dos cosas
        rompen al abrir, no a mitad de una consulta.
        """
        publicadas = {h.nombre_expuesto: h for h in self.herramientas}
        declaradas = set(self.tenant.escrituras)
        sin_declarar = sorted(
            n for n, h in publicadas.items() if not h.solo_lectura and n not in declaradas
        )
        if sin_declarar:
            raise RuntimeError(
                f"El inquilino {self.tenant.id!r} recibe herramientas que escriben y no "
                f"declara como escritura en su manifiesto: {sin_declarar}. Declaralas en "
                "'escrituras' (y pasaran por aprobacion humana) o marca la herramienta "
                "como readOnlyHint en el servidor."
            )
        no_publicadas = sorted(declaradas - set(publicadas))
        if no_publicadas:
            raise RuntimeError(
                f"El manifiesto de {self.tenant.id!r} declara escrituras que ningun "
                f"servidor publica: {no_publicadas}."
            )

    @property
    def escrituras(self) -> list[str]:
        """Herramientas que escriben, por su nombre expuesto."""
        return [h.nombre_expuesto for h in self.herramientas if not h.solo_lectura]

    async def _invocar(self, herramienta: HerramientaMCP, argumentos: dict) -> str:
        cliente = self._sesiones[herramienta.servidor]
        resultado = await cliente.call_tool(herramienta.nombre, argumentos)
        if resultado.structured_content is not None:
            return json.dumps(resultado.structured_content, ensure_ascii=False)
        textos = [c.text for c in resultado.content if getattr(c, "text", None)]
        return "\n".join(textos)
