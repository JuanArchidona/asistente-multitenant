"""Registro de lo que pasa en producción, por inquilino.

## Por qué existe

El feedback docente de la entrega 3.1 pedía dos cosas que siguen abiertas:
instrumentar trazas **en producción** y llevar el coste **acumulado**. La 3.3
resolvió la mitad de laboratorio: el banco guarda cada traza en
`reports/<etiqueta>/` y reporta coste por caso. Pero una consulta real no deja
nada. `Sistema.responder()` devuelve una traza completa y quien la llama la tira.

Hoy eso se ha vuelto medible y por tanto innegable: la consola del proveedor
atribuye a la clave del proyecto un 22 % más de lo que el repositorio
contabiliza (`docs/HALLAZGOS.md` §16). **`reports/` mide el banco, no el
sistema en uso.** Este módulo cubre lo segundo.

## Por qué es opt-in

El banco y la producción comparten la clase `Sistema`. Si el registro se
activara solo, cada barrido de once configuraciones inyectaría cientos de
consultas sintéticas en el log de producción, y la pregunta "cuánto ha costado
atender a este cliente" dejaría de tener respuesta. Se activa desde el punto de
entrada de producción y desde ningún otro sitio.

## Por qué JSONL y no una base de datos

Un registro de auditoría que se puede reescribir no es evidencia. JSONL es
**solo-añadir** por construcción, se lee con `grep`, no tiene esquema que migrar
y sobrevive a que el proceso muera a media escritura sin corromper lo anterior.
El precio es que agregar exige recorrer el fichero; a este volumen no se nota, y
cuando se note, el fichero sigue siendo la fuente y el agregado un derivado.

## Un fichero por inquilino

Misma razón que la colección de Chroma por inquilino (`CLAUDE.md` §4): el
aislamiento estructural no depende de que un filtro esté bien escrito en todas
las rutas de lectura. Mezclar inquilinos en un fichero y separarlos al consultar
deja la separación en manos de no olvidarse nunca del `where`.

## Qué se guarda y qué no

Se guarda la **consulta**, porque sin ella no se puede responder "quién preguntó
qué", que es un requisito explícito de la capa de gobernanza
(`docs/ALCANCE.md` §4, punto 7).

## Una señal separada en tres, y por qué

La primera versión guardaba un `control_actuo` que unía "el filtro retuvo algo"
con "se redactaron campos". Ejecutándolo contra consultas reales se vio que era
engañoso: el anexo confidencial vive en la fuente `rrhh`, así que el filtro lo
retiene en **toda** consulta de recursos humanos, incluida "cuántos días de
vacaciones tengo". El panel decía "el control actuó en el 100 % de las
consultas", que cualquiera lee como "todos intentan acceder a datos protegidos".

Ahora son tres campos con significados distintos: `filtro_retuvo` (ruidoso, casi
constante por fuente), `sin_acceso_a_lo_pedido` (la recuperación se quedó vacía
habiendo material retenido: alguien pidió lo que no le toca) y
`redaccion_aplicada` (la herramienta devolvió campos sensibles para esa consulta
concreta). Ver `docs/HALLAZGOS.md` §20.

**No se guarda la respuesta**, solo su longitud y un hash. Es una decisión, no
un descuido: la respuesta es el texto más largo y con más probabilidad de
arrastrar datos del corpus, y para diagnosticar ya están la categoría, las
fuentes recuperadas y la configuración, que permiten reproducirla. Quien
necesite el texto lo activa con `guardar_respuesta=True` y asume lo que eso
implica. El hash permite saber si dos consultas dieron la misma respuesta sin
tener que guardarla.
"""
import hashlib
import json
import os
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

RAIZ_POR_DEFECTO = Path("data/observabilidad")

# Campos de la traza que no se copian al registro: o son enormes, o son el texto
# que se ha decidido no guardar.
_EXCLUIDOS = {"contexto_recuperado", "respuesta", "consulta", "herramientas_invocadas"}


def _hash(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:16]


class Registro:
    """Escribe una línea por consulta en el log del inquilino.

    Nunca lanza. Un fallo al registrar no puede tumbar una consulta que el
    usuario ya ha hecho: el sistema ha respondido bien y perder la anotación es
    peor que nada, pero mucho menos peor que devolver un error. Eso sí, **no se
    traga el fallo en silencio**: lo deja en `ultimo_error` y lo cuenta, para
    que el informe pueda decir que el registro está cojo en vez de aparentar
    que no pasó nada.
    """

    def __init__(
        self,
        tenant_id: str,
        raiz: Path | str = RAIZ_POR_DEFECTO,
        guardar_respuesta: bool = False,
    ):
        self.tenant_id = tenant_id
        self.ruta = Path(raiz) / tenant_id / "trazas.jsonl"
        self.guardar_respuesta = guardar_respuesta
        self.fallos = 0
        self.ultimo_error: str | None = None
        self._lock = threading.Lock()

    def anotar(self, traza: dict, uso: dict | None = None) -> dict | None:
        """Compone y escribe el registro. Devuelve lo escrito, o None si falló."""
        try:
            registro = self.componer(traza, uso)
            linea = json.dumps(registro, ensure_ascii=False)
            with self._lock:
                self.ruta.parent.mkdir(parents=True, exist_ok=True)
                with self.ruta.open("a", encoding="utf-8") as f:
                    f.write(linea + "\n")
            return registro
        except Exception as e:  # noqa: BLE001 -- ver docstring de la clase
            with self._lock:
                self.fallos += 1
                self.ultimo_error = f"{type(e).__name__}: {e}"
            return None

    def anotar_accion(self, evento: str, accion: dict, usuario: str, extra: dict | None = None) -> dict | None:
        """Una línea por cada paso de una acción con aprobación humana.

        `evento` es `propuesta`, `aprobada` o `rechazada`. Va al mismo log que
        las consultas, con la clave `_accion`, para que la auditoría de "quién
        aprobó qué" esté en el mismo sitio que "quién preguntó qué". El resumen
        las cuenta aparte: no son consultas.
        """
        try:
            registro = {
                CLAVE_ACCION: evento,
                "ts": datetime.now(UTC).isoformat(timespec="seconds"),
                "tenant": self.tenant_id,
                "usuario": usuario,
                "id_accion": accion.get("id"),
                "herramienta": accion.get("herramienta"),
                "argumentos": accion.get("argumentos"),
                "propuesta_por": accion.get("usuario"),
                **(extra or {}),
            }
            with self._lock:
                self.ruta.parent.mkdir(parents=True, exist_ok=True)
                with self.ruta.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(registro, ensure_ascii=False) + "\n")
            return registro
        except Exception as e:  # noqa: BLE001 -- misma regla que anotar()
            with self._lock:
                self.fallos += 1
                self.ultimo_error = f"{type(e).__name__}: {e}"
            return None

    def componer(self, traza: dict, uso: dict | None) -> dict:
        respuesta = traza.get("respuesta") or ""
        denegados = traza.get("denegados_por_permiso") or []
        redactados = traza.get("campos_redactados") or []
        herramientas = [
            p["herramienta"] for p in (traza.get("herramientas_invocadas") or [])
            if "herramienta" in p
        ]

        registro = {
            "ts": datetime.now(UTC).isoformat(timespec="seconds"),
            "tenant": traza.get("tenant", self.tenant_id),
            "usuario": traza.get("usuario"),
            "consulta": traza.get("consulta"),
            "categoria": traza.get("categoria"),
            "confianza": traza.get("confianza_enrutador"),
            "fallback_enrutador": bool(traza.get("fallback_enrutador")),
            # La rama se deduce de lo que la traza trae, no de un parámetro: así
            # el registro describe lo que pasó y no lo que se pretendía.
            "rama": "estructurada" if "herramientas_invocadas" in traza
            else ("documental" if traza.get("fuentes_usadas") is not None else "sin_fuente"),
            "archivos": sorted({f["archivo"] for f in (traza.get("fuentes_usadas") or [])}),
            "herramientas": herramientas,
            # Tres señales, deliberadamente separadas. Juntarlas en un
            # "el control actuó" fue el primer intento y era engañoso: ver §20.
            "denegados_por_permiso": denegados,
            "campos_redactados": redactados,
            # Ruidosa por construcción: un documento restringido en una fuente
            # se retiene en TODA consulta a esa fuente, pregunte lo que pregunte
            # el usuario. Describe la recuperación, no la intención.
            "filtro_retuvo": bool(denegados),
            # Significativa: la recuperación se quedó vacía Y había algo
            # retenido, o sea que lo pedido SOLO lo respondía material
            # protegido. Aquí sí hubo alguien pidiendo lo que no le toca.
            "sin_acceso_a_lo_pedido": bool(denegados) and bool(traza.get("contexto_vacio")),
            # Significativa: la herramienta devolvió campos sensibles para ESTA
            # consulta y la redacción los sustituyó. Depende de la pregunta.
            "redaccion_aplicada": bool(redactados),
            "contexto_vacio": bool(traza.get("contexto_vacio")),
            "respuesta_chars": len(respuesta),
            "respuesta_hash": _hash(respuesta) if respuesta else None,
            "latencia_total_s": round(
                traza.get("latencia_router_s", 0.0)
                + traza.get("latencia_retrieve_s", 0.0)
                + traza.get("latencia_generacion_s", 0.0),
                3,
            ),
            "latencias": {
                "router_s": traza.get("latencia_router_s"),
                "retrieve_s": traza.get("latencia_retrieve_s"),
                "generacion_s": traza.get("latencia_generacion_s"),
            },
            "error": traza.get("error"),
        }

        if uso:
            registro["llamadas"] = uso.get("llamadas")
            registro["tokens_entrada"] = uso.get("tokens_entrada")
            registro["tokens_salida"] = uso.get("tokens_salida")
            registro["coste_usd"] = uso.get("coste_usd_estimado")
            # Los embeddings de la consulta, aparte (§37), y la señal de que el
            # coste es un suelo si algún modelo no tiene precio (§28, §35). Sin
            # esto el registro diría "esta consulta costó X" con la misma
            # seguridad tanto si X lo incluye todo como si no.
            embebidos = sum(
                m.get("tokens_embebidos", 0) for m in (uso.get("por_modelo") or {}).values()
            )
            if embebidos:
                registro["tokens_embebidos"] = embebidos
            if uso.get("modelos_sin_precio"):
                registro["modelos_sin_precio"] = uso["modelos_sin_precio"]

        if self.guardar_respuesta:
            registro["respuesta"] = respuesta

        # Cualquier campo nuevo de la traza entra solo. Si mañana el agente
        # añade una señal, el registro la recoge sin que haya que acordarse.
        for clave, valor in traza.items():
            if clave not in _EXCLUIDOS and clave not in registro:
                registro[clave] = valor

        return registro


def desde_config(cfg, raiz: Path | str = RAIZ_POR_DEFECTO) -> Registro:
    """Registro del inquilino activo.

    `OBS_GUARDAR_RESPUESTA=1` guarda además el texto de la respuesta. Apagado
    por defecto: ver el encabezado del módulo.
    """
    return Registro(
        cfg.tenant.id,
        raiz=raiz,
        guardar_respuesta=os.getenv("OBS_GUARDAR_RESPUESTA", "") == "1",
    )


# --- Lectura ---------------------------------------------------------------


def leer(tenant_id: str, raiz: Path | str = RAIZ_POR_DEFECTO) -> list[dict]:
    """Lee el log de un inquilino, saltando líneas corruptas y contándolas.

    Una línea a medias es lo que deja un proceso que murió escribiendo. Se
    salta, pero se devuelve la cuenta en `_lineas_ilegibles` del resumen: un
    lector que las esconde convierte un log incompleto en uno que parece
    completo.
    """
    ruta = Path(raiz) / tenant_id / "trazas.jsonl"
    if not ruta.is_file():
        return []
    registros, ilegibles = [], 0
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        if not linea.strip():
            continue
        try:
            registros.append(json.loads(linea))
        except json.JSONDecodeError:
            ilegibles += 1
    if ilegibles:
        registros.append({"_ilegible": ilegibles})
    return registros


# --- Retencion y supresion ------------------------------------------------
#
# El registro guarda quien pregunto que. Es la trazabilidad que pide el
# articulo 12 del AI Act y, a la vez, un dato personal del usuario que pregunta
# (RGPD): la consulta puede decir cosas de quien la hace. Dos caminos, y los
# dos dejan rastro de si mismos:
#
#   - `borrar_usuario`: derecho de supresion. Quita todas las lineas de un
#     usuario y deja UNA lapida que dice cuantas se quitaron y cuando, con el
#     usuario en hash: la auditoria sigue sabiendo que hubo un borrado sin
#     conservar a quien.
#   - `purgar`: retencion. Quita las lineas mas viejas que N dias y deja la
#     misma lapida. La politica esta en docs/RETENCION.md.
#
# Los dos reescriben el fichero, y el encabezado del modulo dice que un
# registro que se puede reescribir no es evidencia. La contradiccion es real y
# se resuelve asi: la reescritura solo QUITA lineas, nunca cambia ninguna, y
# siempre anade una lapida. Un registro del que se ha borrado algo lo dice; uno
# manipulado no. Las lineas ilegibles se conservan tal cual: no se sabe de
# quien son, y borrarlas seria borrar sin saber que.

CLAVE_LAPIDA = "_borrado"
CLAVE_ACCION = "_accion"


def _reescribir(ruta: Path, conservar, motivo: dict) -> dict:
    """Reescribe el log conservando las lineas para las que `conservar` es
    True y anadiendo una lapida con `motivo`. Devuelve la lapida."""
    lineas = ruta.read_text(encoding="utf-8").splitlines() if ruta.is_file() else []
    quedan, quitadas, ilegibles = [], 0, 0
    for linea in lineas:
        if not linea.strip():
            continue
        try:
            registro = json.loads(linea)
        except json.JSONDecodeError:
            ilegibles += 1
            quedan.append(linea)  # no se sabe de quien es: se conserva
            continue
        if CLAVE_LAPIDA in registro or conservar(registro):
            quedan.append(linea)
        else:
            quitadas += 1
    lapida = {
        CLAVE_LAPIDA: True,
        "ts": datetime.now(UTC).isoformat(timespec="seconds"),
        "lineas_quitadas": quitadas,
        "lineas_ilegibles_conservadas": ilegibles,
        **motivo,
    }
    if quitadas:
        quedan.append(json.dumps(lapida, ensure_ascii=False))
        tmp = ruta.with_suffix(".jsonl.tmp")
        tmp.write_text("\n".join(quedan) + "\n", encoding="utf-8")
        tmp.replace(ruta)  # atomico en el mismo sistema de ficheros
    return lapida


def borrar_usuario(tenant_id: str, usuario: str, raiz: Path | str = RAIZ_POR_DEFECTO) -> dict:
    """Supresion (RGPD art. 17): quita todas las consultas de un usuario y deja
    una lapida con su hash. Devuelve la lapida, con `lineas_quitadas`."""
    ruta = Path(raiz) / tenant_id / "trazas.jsonl"
    return _reescribir(
        ruta,
        conservar=lambda r: r.get("usuario") != usuario,
        motivo={"motivo": "supresion_usuario", "usuario_hash": _hash(usuario)},
    )


def purgar(tenant_id: str, dias: int, raiz: Path | str = RAIZ_POR_DEFECTO, ahora=None) -> dict:
    """Retencion: quita las consultas con mas de `dias` dias. Devuelve la lapida."""
    if dias < 1:
        raise ValueError("la retencion se expresa en dias enteros positivos")
    ahora = ahora or datetime.now(UTC)
    limite = (ahora - timedelta(days=dias)).isoformat(timespec="seconds")
    ruta = Path(raiz) / tenant_id / "trazas.jsonl"
    return _reescribir(
        ruta,
        conservar=lambda r: (r.get("ts") or "") >= limite,
        motivo={"motivo": "retencion", "dias": dias, "anteriores_a": limite},
    )


def inquilinos(raiz: Path | str = RAIZ_POR_DEFECTO) -> list[str]:
    raiz = Path(raiz)
    if not raiz.is_dir():
        return []
    return sorted(d.name for d in raiz.iterdir() if (d / "trazas.jsonl").is_file())


def _percentil(valores: list[float], p: float) -> float:
    if not valores:
        return 0.0
    orden = sorted(valores)
    return orden[min(len(orden) - 1, round((len(orden) - 1) * p))]


def resumir(registros: list[dict]) -> dict:
    """Agrega un log en las cifras que responden a las preguntas de producción."""
    ilegibles = sum(r.get("_ilegible", 0) for r in registros)
    lapidas = [r for r in registros if CLAVE_LAPIDA in r]
    acciones = [r for r in registros if CLAVE_ACCION in r]
    filas = [
        r for r in registros
        if "_ilegible" not in r and CLAVE_LAPIDA not in r and CLAVE_ACCION not in r
    ]
    n = len(filas)
    if not n:
        return {
            "consultas": 0,
            "borrados": len(lapidas),
            "lineas_borradas": sum(lp.get("lineas_quitadas", 0) for lp in lapidas),
            "acciones": {
                e: sum(1 for a in acciones if a.get(CLAVE_ACCION) == e)
                for e in ("propuesta", "aprobada", "rechazada")
            },
            "_lineas_ilegibles": ilegibles,
        }

    lat = [r.get("latencia_total_s") or 0.0 for r in filas]
    coste = sum(r.get("coste_usd") or 0.0 for r in filas)
    por_categoria: dict[str, int] = {}
    por_rama: dict[str, int] = {}
    por_usuario: dict[str, int] = {}
    for r in filas:
        por_categoria[r.get("categoria") or "?"] = por_categoria.get(r.get("categoria") or "?", 0) + 1
        por_rama[r.get("rama") or "?"] = por_rama.get(r.get("rama") or "?", 0) + 1
        por_usuario[r.get("usuario") or "?"] = por_usuario.get(r.get("usuario") or "?", 0) + 1

    degradadas = [r for r in filas if r.get("error") or r.get("contexto_vacio")]
    return {
        "consultas": n,
        "desde": min(r.get("ts", "") for r in filas),
        "hasta": max(r.get("ts", "") for r in filas),
        "coste_usd_acumulado": round(coste, 6),
        "coste_usd_por_consulta": round(coste / n, 6),
        "tokens_entrada": sum(r.get("tokens_entrada") or 0 for r in filas),
        "tokens_salida": sum(r.get("tokens_salida") or 0 for r in filas),
        "latencia_media_s": round(sum(lat) / n, 3),
        "latencia_p95_s": round(_percentil(lat, 0.95), 3),
        # Separadas a propósito: la primera es casi constante por fuente y la
        # segunda es la que señala a alguien pidiendo lo que no le toca.
        "filtro_retuvo_documentos": sum(1 for r in filas if r.get("filtro_retuvo")),
        "sin_acceso_a_lo_pedido": sum(1 for r in filas if r.get("sin_acceso_a_lo_pedido")),
        "redaccion_aplicada": sum(1 for r in filas if r.get("redaccion_aplicada")),
        "consultas_degradadas": len(degradadas),
        "tasa_degradadas": round(len(degradadas) / n, 4),
        "fallback_enrutador": sum(1 for r in filas if r.get("fallback_enrutador")),
        "por_categoria": dict(sorted(por_categoria.items(), key=lambda kv: -kv[1])),
        "por_rama": dict(sorted(por_rama.items(), key=lambda kv: -kv[1])),
        "usuarios_distintos": len(por_usuario),
        # Que hubo borrados se dice; cuantas lineas, tambien. Un resumen que
        # los escondiera haria pasar un registro podado por uno entero.
        "borrados": len(lapidas),
        "lineas_borradas": sum(lp.get("lineas_quitadas", 0) for lp in lapidas),
        # Human-in-the-loop: cuántas escrituras se propusieron y qué pasó con
        # ellas. Una propuesta sin aprobar ni rechazar sigue pendiente.
        "acciones": {
            e: sum(1 for a in acciones if a.get(CLAVE_ACCION) == e)
            for e in ("propuesta", "aprobada", "rechazada")
        },
        "_lineas_ilegibles": ilegibles,
    }
