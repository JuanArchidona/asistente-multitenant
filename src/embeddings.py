"""Wrapper de embeddings sobre gemini-embedding-001.

Nota: text-embedding-004 fue apagado el 14/01/2026. Usamos gemini-embedding-001,
el modelo estable recomendado. Distinguimos task_type entre indexación de
documentos (RETRIEVAL_DOCUMENT) y consulta (RETRIEVAL_QUERY) para mejorar la
calidad de la recuperación.

Respecto a la 3.1, la dimensionalidad de salida deja de ser una constante del
módulo y pasa a `Config.embed_dims`: es uno de los ejes del barrido (768 es el
valor de producción, 1536 y 3072 son las alternativas que Matryoshka permite sin
cambiar de modelo).
"""
import re
import time

from google import genai
from google.genai import types

from .config import Config

# El plan gratuito limita a 100 peticiones de embedding por minuto. El banco de
# pruebas hace muchas más que la app, así que aquí sí hace falta reintentar: sin
# esto un barrido de configuraciones muere a mitad y hay que empezar de cero.
REINTENTOS = 5
ESPERA_POR_DEFECTO_S = 20.0
_RE_RETRY_DELAY = re.compile(r"retryDelay['\"]?[:\s]+['\"]?(\d+(?:\.\d+)?)")


# Caracteres por token del modelo de embeddings, para estimar cuando no se
# cuenta exacto. Medido el 23-09-2026 con `count_tokens` sobre las 91 consultas
# del golden set de los dos inquilinos: 5.396 caracteres, 1.285 tokens, 14,1
# tokens por consulta. Es la razon de CONSULTAS, que es donde se estima; los
# documentos del corpus dan menos (3,39 y 4,08 en los dos corpus, por el
# markdown), y la ingesta cuenta exacto y escribe la razon real de cada uno
# para poder contrastar esta constante cuando cambie el modelo.
CARACTERES_POR_TOKEN = 4.20


class GeminiEmbedder:
    """Embeddings, con su consumo contabilizado.

    Hasta el 23-09-2026 esta clase no contaba nada y toda cifra de coste del
    proyecto excluia los embeddings sin decirlo (HALLAZGOS.md §35). La API no
    devuelve uso en la respuesta (`metadata` llega vacio para este modelo),
    asi que hay dos caminos y se declara cual se usa:

    - `contar_exacto=True`: una llamada a `count_tokens` por lote antes de
      embeber. Para la ingesta, donde la latencia no importa y el volumen si.
    - `contar_exacto=False`: estimacion por caracteres. Para la consulta,
      donde una llamada mas por pregunta moveria `latencia_retrieve_s`, que
      es una metrica comparada entre ejecuciones.

    Sin `uso` no se contabiliza, y eso es lo que hacen el barrido y las
    pruebas que no lo pasan.
    """

    def __init__(self, cfg: Config, uso=None, contar_exacto: bool = False):
        self.client = genai.Client(api_key=cfg.gemini_api_key)
        self.model = cfg.embed_model
        self.dims = cfg.embed_dims
        self.uso = uso
        self.contar_exacto = contar_exacto

    def _contabilizar(self, textos: list[str]) -> None:
        if self.uso is None:
            return
        if self.contar_exacto:
            resp = self.client.models.count_tokens(model=self.model, contents=textos)
            self.uso.registrar_embeddings(self.model, int(resp.total_tokens or 0), exactos=True)
        else:
            estimados = round(sum(len(t) for t in textos) / CARACTERES_POR_TOKEN)
            self.uso.registrar_embeddings(self.model, estimados, exactos=False)

    def _embed(self, textos: list[str], task_type: str) -> list[list[float]]:
        ultimo = None
        for intento in range(REINTENTOS):
            try:
                resp = self.client.models.embed_content(
                    model=self.model,
                    contents=textos,
                    config=types.EmbedContentConfig(
                        task_type=task_type,
                        output_dimensionality=self.dims,
                    ),
                )
                # Despues de la llamada buena: un reintento por cuota no se
                # cuenta dos veces, y una llamada que falla no se cuenta.
                self._contabilizar(textos)
                return [e.values for e in resp.embeddings]
            except Exception as e:
                mensaje = str(e)
                if "429" not in mensaje and "RESOURCE_EXHAUSTED" not in mensaje:
                    raise
                ultimo = e
                # La API dice cuánto esperar; si no, se usa el valor por defecto.
                m = _RE_RETRY_DELAY.search(mensaje)
                espera = float(m.group(1)) + 1 if m else ESPERA_POR_DEFECTO_S * (intento + 1)
                print(f"[embeddings] cuota agotada, reintento en {espera:.0f}s...")
                time.sleep(espera)
        raise RuntimeError(f"Embeddings: cuota agotada tras {REINTENTOS} intentos: {ultimo}")

    def embed_documentos(self, textos: list[str]) -> list[list[float]]:
        return self._embed(textos, "RETRIEVAL_DOCUMENT")

    def embed_consulta(self, texto: str) -> list[float]:
        return self._embed([texto], "RETRIEVAL_QUERY")[0]

    def embed_consultas(self, textos: list[str]) -> list[list[float]]:
        """Lote de consultas en una sola llamada.

        La app siempre embebe una consulta cada vez, pero el banco embebe
        decenas seguidas. Agrupar convierte 43 peticiones en una, que es la
        diferencia entre caber en la cuota del plan gratuito o no caber.
        """
        vectores: list[list[float]] = []
        for i in range(0, len(textos), 100):  # la API admite 100 por llamada
            vectores.extend(self._embed(textos[i:i + 100], "RETRIEVAL_QUERY"))
        return vectores
