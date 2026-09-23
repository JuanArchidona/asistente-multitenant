"""Pruebas del registro de producción.

Lo que se prueba aquí no es que escriba un fichero, es que el fichero sirva para
responder las preguntas por las que existe: cuánto se ha gastado por cliente,
cuántas veces actuó el control de acceso y cuántas consultas salieron
degradadas. Un log que no distingue eso es un fichero que crece.
"""
import json
from dataclasses import replace

import pytest

from src.agent import Sistema
from src.observabilidad import CLAVE_FALLO, Registro, inquilinos, leer, resumir
from src.retriever import Recuperacion, Recuperado


def _traza(**cambios) -> dict:
    base = {
        "consulta": "¿Cuántos días de vacaciones?",
        "tenant": "empresa_servicios",
        "usuario": "ana",
        "categoria": "rrhh",
        "confianza_enrutador": 0.9,
        "fallback_enrutador": False,
        "fuentes_usadas": [{"archivo": "convenio_colectivo.md", "distancia": 0.2}],
        "contexto_recuperado": ["texto largo del fragmento"],
        "contexto_vacio": False,
        "denegados_por_permiso": [],
        "respuesta": "Son 23 días laborables.",
        "latencia_router_s": 0.4,
        "latencia_retrieve_s": 0.3,
        "latencia_generacion_s": 1.1,
    }
    base.update(cambios)
    return base


# --- Qué se guarda y qué no ---

def test_no_guarda_la_respuesta_pero_si_su_huella(tmp_path):
    """Decisión deliberada: la respuesta es el texto más largo y el que más
    probablemente arrastre datos del corpus. Para diagnosticar bastan la
    categoría, las fuentes y la configuración."""
    r = Registro("empresa_servicios", raiz=tmp_path).componer(_traza(), None)

    assert "respuesta" not in r
    assert r["respuesta_chars"] == len("Son 23 días laborables.")
    assert r["respuesta_hash"]
    # El contexto recuperado tampoco: es el corpus entero troceado.
    assert "contexto_recuperado" not in r


def test_la_consulta_si_se_guarda(tmp_path):
    """Sin ella no se puede responder 'quién preguntó qué', que es requisito
    explícito de la capa de gobernanza."""
    r = Registro("empresa_servicios", raiz=tmp_path).componer(_traza(), None)

    assert r["consulta"] == "¿Cuántos días de vacaciones?"
    assert r["usuario"] == "ana"


def test_guardar_respuesta_es_opt_in(tmp_path):
    reg = Registro("empresa_servicios", raiz=tmp_path, guardar_respuesta=True)

    assert reg.componer(_traza(), None)["respuesta"] == "Son 23 días laborables."


def test_un_campo_nuevo_de_la_traza_entra_solo(tmp_path):
    """Si mañana el agente añade una señal, el registro la recoge sin que haya
    que acordarse de tocar dos sitios."""
    r = Registro("t", raiz=tmp_path).componer(_traza(senal_nueva="valor"), None)

    assert r["senal_nueva"] == "valor"


# --- Las señales que hacen útil el log ---

def test_el_filtro_retuvo_no_significa_que_alguien_pidiera_lo_prohibido(tmp_path):
    """Medido contra consultas reales: el anexo confidencial vive en la fuente
    `rrhh`, así que el filtro lo retiene en TODA consulta de recursos humanos,
    incluida preguntar por los días de vacaciones. La señal describe la
    recuperación, no la intención, y unirlas fue el error del §20."""
    r = Registro("t", raiz=tmp_path).componer(
        _traza(denegados_por_permiso=["anexo_confidencial_plantilla.md"],
               contexto_vacio=False), None
    )

    assert r["filtro_retuvo"] is True
    assert r["sin_acceso_a_lo_pedido"] is False


def test_quedarse_sin_nada_por_permisos_si_es_una_senal_de_verdad(tmp_path):
    """Recuperación vacía habiendo material retenido: lo pedido SOLO lo
    respondía material protegido."""
    r = Registro("t", raiz=tmp_path).componer(
        _traza(denegados_por_permiso=["anexo_confidencial_plantilla.md"],
               fuentes_usadas=[], contexto_vacio=True), None
    )

    assert r["sin_acceso_a_lo_pedido"] is True


def test_la_rama_se_deduce_de_lo_que_paso_no_de_lo_que_se_pretendia(tmp_path):
    reg = Registro("t", raiz=tmp_path)

    documental = reg.componer(_traza(), None)
    estructurada = reg.componer(
        _traza(herramientas_invocadas=[{"herramienta": "crm__estado_operacion"}],
               campos_redactados=["parte_compradora.dni"]),
        None,
    )

    assert documental["rama"] == "documental"
    assert estructurada["rama"] == "estructurada"
    assert estructurada["herramientas"] == ["crm__estado_operacion"]
    assert estructurada["redaccion_aplicada"] is True


def test_el_coste_de_la_consulta_viaja_al_registro(tmp_path):
    uso = {"llamadas": 2, "tokens_entrada": 700, "tokens_salida": 120,
           "coste_usd_estimado": 0.0013}

    r = Registro("t", raiz=tmp_path).componer(_traza(), uso)

    assert r["coste_usd"] == 0.0013 and r["llamadas"] == 2


# --- Escritura ---

def test_escribe_una_linea_por_consulta_y_un_fichero_por_inquilino(tmp_path):
    """Un fichero por inquilino por la misma razón que una colección de Chroma
    por inquilino: el aislamiento no depende de acordarse del filtro al leer."""
    Registro("empresa_servicios", raiz=tmp_path).anotar(_traza(), None)
    Registro("empresa_servicios", raiz=tmp_path).anotar(_traza(consulta="otra"), None)
    Registro("agencia_inmobiliaria", raiz=tmp_path).anotar(
        _traza(tenant="agencia_inmobiliaria", consulta="de la agencia"), None
    )

    assert inquilinos(tmp_path) == ["agencia_inmobiliaria", "empresa_servicios"]
    assert len(leer("empresa_servicios", tmp_path)) == 2
    agencia = leer("agencia_inmobiliaria", tmp_path)
    assert len(agencia) == 1 and agencia[0]["consulta"] == "de la agencia"


def test_un_fallo_al_registrar_no_tumba_la_consulta(tmp_path, monkeypatch):
    """El usuario ya ha recibido su respuesta. Perder la anotación es malo;
    devolverle un error porque el log falló es peor."""
    reg = Registro("t", raiz=tmp_path)
    monkeypatch.setattr(
        "src.observabilidad.json.dumps", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("disco lleno"))
    )

    assert reg.anotar(_traza(), None) is None
    assert reg.fallos == 1 and "disco lleno" in reg.ultimo_error


def test_una_linea_corrupta_se_salta_pero_se_cuenta(tmp_path):
    """Es lo que deja un proceso que murió escribiendo. Un lector que la
    esconde convierte un log incompleto en uno que parece completo."""
    reg = Registro("t", raiz=tmp_path)
    reg.anotar(_traza(), None)
    with reg.ruta.open("a", encoding="utf-8") as f:
        f.write('{"ts": "rota", sin cerrar\n')
    reg.anotar(_traza(), None)

    registros = leer("t", tmp_path)
    resumen = resumir(registros)

    assert resumen["consultas"] == 2
    assert resumen["_lineas_ilegibles"] == 1


# --- Agregación ---

def test_el_resumen_responde_a_las_preguntas_de_produccion(tmp_path):
    reg = Registro("t", raiz=tmp_path)
    uso = {"llamadas": 2, "tokens_entrada": 600, "tokens_salida": 100,
           "coste_usd_estimado": 0.002}
    reg.anotar(_traza(usuario="ana"), uso)
    reg.anotar(_traza(usuario="luis", denegados_por_permiso=["anexo.md"]), uso)
    reg.anotar(_traza(usuario="ana", categoria="otro", contexto_vacio=True), uso)

    r = resumir(leer("t", tmp_path))

    assert r["consultas"] == 3
    assert r["coste_usd_acumulado"] == pytest.approx(0.006)
    assert r["coste_usd_por_consulta"] == pytest.approx(0.002)
    assert r["usuarios_distintos"] == 2
    assert r["filtro_retuvo_documentos"] == 1
    assert r["consultas_degradadas"] == 1
    assert r["por_categoria"] == {"rrhh": 2, "otro": 1}


def test_sin_registros_no_se_inventa_un_cero(tmp_path):
    """Cero consultas y coste cero no son lo mismo: lo primero significa que no
    hay nada que medir."""
    r = resumir([])

    assert r["consultas"] == 0
    assert "coste_usd_acumulado" not in r


# --- Integración con el agente ---

class _RetrieverFalso:
    def recuperar_con_control(self, consulta, fuente, usuario=None):
        return Recuperacion([Recuperado("texto", "rrhh", "convenio_colectivo.md", 0.2)], [])


def test_el_banco_no_contamina_el_log_de_produccion(cfg, chat_falso, tmp_path):
    """El banco y la producción comparten `Sistema`. Si el registro se activara
    solo, un barrido de once configuraciones metería cientos de consultas
    sintéticas aquí y 'cuánto ha costado atender a este cliente' dejaría de
    tener respuesta."""
    chat = chat_falso(['{"categoria": "rrhh", "confianza": 0.9, "justificacion": "x"}', "23 días."])
    sistema = Sistema(cfg, chat=chat)  # sin registro, como lo crea el banco
    sistema._retriever = _RetrieverFalso()

    sistema.responder("¿vacaciones?")

    assert inquilinos(tmp_path) == []


def test_con_registro_la_consulta_queda_anotada_con_su_coste(cfg, chat_falso, tmp_path):
    chat = chat_falso(['{"categoria": "rrhh", "confianza": 0.9, "justificacion": "x"}', "23 días."])
    registro = Registro(cfg.tenant.id, raiz=tmp_path)
    sistema = Sistema(cfg, chat=chat, registro=registro)
    sistema._retriever = _RetrieverFalso()

    sistema.responder("¿vacaciones?")

    filas = leer(cfg.tenant.id, tmp_path)
    assert len(filas) == 1
    fila = filas[0]
    assert fila["consulta"] == "¿vacaciones?"
    assert fila["categoria"] == "rrhh"
    # El coste es el de ESTA consulta, no el acumulado de la sesión.
    assert fila["llamadas"] == 2
    assert fila["tokens_entrada"] == 20


def test_dos_consultas_no_se_reparten_mal_el_coste(cfg, chat_falso, tmp_path):
    """Restar dos instantáneas del acumulado sería más corto y estaría mal: la
    segunda consulta heredaría el gasto de la primera."""
    chat = chat_falso([
        '{"categoria": "rrhh", "confianza": 0.9, "justificacion": "x"}', "23 días.",
        '{"categoria": "rrhh", "confianza": 0.9, "justificacion": "x"}', "Otra cosa.",
    ])
    registro = Registro(cfg.tenant.id, raiz=tmp_path)
    sistema = Sistema(cfg, chat=chat, registro=registro)
    sistema._retriever = _RetrieverFalso()

    sistema.responder("primera")
    sistema.responder("segunda")

    filas = leer(cfg.tenant.id, tmp_path)
    assert [f["llamadas"] for f in filas] == [2, 2]
    assert [f["tokens_entrada"] for f in filas] == [20, 20]
    # Y el acumulado de la sesión sí suma las dos.
    assert sistema.chat.uso.tokens_entrada == 40


def test_el_registro_es_por_inquilino_tambien_desde_el_agente(cfg, cfg_factory, chat_falso, tmp_path):
    from src.tenant import cargar_tenant
    otro = cfg_factory(tenant=cargar_tenant("agencia_inmobiliaria"))

    for c, consulta in ((cfg, "de la empresa"), (otro, "de la agencia")):
        chat = chat_falso([
            json.dumps({"categoria": "rrhh" if c is cfg else "procesos",
                        "confianza": 0.9, "justificacion": "x"}),
            "respuesta",
        ])
        sistema = Sistema(c, chat=chat, registro=Registro(c.tenant.id, raiz=tmp_path))
        sistema._retriever = _RetrieverFalso()
        sistema.responder(consulta)

    assert inquilinos(tmp_path) == ["agencia_inmobiliaria", "empresa_servicios"]
    assert leer("empresa_servicios", tmp_path)[0]["consulta"] == "de la empresa"
    assert leer("agencia_inmobiliaria", tmp_path)[0]["consulta"] == "de la agencia"


def test_replace_de_config_sigue_funcionando(cfg):
    """Guardia barata: `cfg_factory` usa `replace`, y añadir un campo sin valor
    por defecto a `Config` lo rompería lejos de aquí."""
    assert replace(cfg, top_k=9).top_k == 9


# --- Consultas que no llegaron a responder ---

class _ChatQueRevienta:
    """Un proveedor con la clave revocada: la primera llamada lanza."""

    def __init__(self):
        from src.provider import Uso
        self.uso = Uso()

    def completar(self, *_a, **_k):
        raise PermissionError("Error code: 401 - API key is invalid.")


def test_una_consulta_que_revienta_queda_anotada_como_fallo_y_se_propaga(cfg, tmp_path):
    """Medido en el simulacro del plan de incidentes (§46): con una clave
    revocada, el registro quedaba exactamente igual que si nadie hubiera
    preguntado. Un incidente que la observabilidad no ve no se detecta por la
    observabilidad."""
    registro = Registro(cfg.tenant.id, raiz=tmp_path)
    sistema = Sistema(cfg, chat=_ChatQueRevienta(), registro=registro)

    with pytest.raises(PermissionError):
        sistema.responder("¿vacaciones?")

    filas = leer(cfg.tenant.id, tmp_path)
    assert len(filas) == 1
    assert filas[0][CLAVE_FALLO] == "PermissionError"
    assert filas[0]["consulta"] == "¿vacaciones?"
    assert "401" in filas[0]["mensaje"]


def test_los_fallos_se_cuentan_aparte_y_no_bajan_las_medias(tmp_path):
    registro = Registro("empresa_servicios", raiz=tmp_path)
    registro.anotar(_traza(latencia_generacion_s=1.1), {"llamadas": 2, "coste_usd_estimado": 0.01})
    registro.anotar_fallo("¿vacaciones?", "ana", PermissionError("401"))
    registro.anotar_fallo("¿nómina?", "ana", TimeoutError("sin respuesta"))

    resumen = resumir(leer("empresa_servicios", tmp_path))
    assert resumen["consultas"] == 1
    assert resumen["consultas_fallidas"] == 2
    assert resumen["fallos_por_tipo"] == {"PermissionError": 1, "TimeoutError": 1}
    # Las medias son de la consulta respondida, no diluidas por los fallos.
    assert resumen["coste_usd_por_consulta"] == pytest.approx(0.01)
    assert resumen["latencia_media_s"] == pytest.approx(1.8)


def test_solo_fallos_no_es_un_registro_vacio(tmp_path):
    registro = Registro("empresa_servicios", raiz=tmp_path)
    registro.anotar_fallo("¿vacaciones?", "ana", PermissionError("401"))
    resumen = resumir(leer("empresa_servicios", tmp_path))
    assert resumen["consultas"] == 0
    assert resumen["consultas_fallidas"] == 1


def test_el_mensaje_del_fallo_se_recorta(tmp_path):
    registro = Registro("empresa_servicios", raiz=tmp_path)
    registro.anotar_fallo("q", "ana", RuntimeError("x" * 1000))
    assert len(leer("empresa_servicios", tmp_path)[0]["mensaje"]) == 200
