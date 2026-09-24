"""Interfaz desplegada del asistente multi-tenant.

    uv sync --group app
    uv run streamlit run app.py

Es el punto de entrada de producción para personas: aquí se registra cada
consulta (observabilidad opt-in, `src/observabilidad.py`), se aplica el tope
de gasto blando y se muestra el aviso del artículo 50 del AI Act que declara
cada inquilino en su manifiesto.

Lo que decide la arquitectura, y no la interfaz:

- **El inquilino lo fija la credencial**, no un desplegable. Un usuario de la
  empresa de servicios no puede ver la agencia ni eligiendo mal.
- **Los roles viajan con la credencial** al control de acceso, que actúa
  dentro de la búsqueda y al salir de la herramienta, igual que en el banco.
- **Un `Sistema` por inquilino**, en caché del proceso: los clientes de los
  proveedores y el índice se abren una vez.
- **El índice se reconstruye si no existe**: el sistema de ficheros de Render
  es efímero y el corpus versionado es la fuente de verdad (decisión de la
  entrega 3.1, que aquí se hereda).

Lo que NO hace, y está escrito en docs/DESPLIEGUE.md: cargar documentos,
gestionar usuarios desde la interfaz, ni sustituir el tope duro del prepago.
"""
import streamlit as st

from src.acceso import cargar_directorio, tope_superado
from src.agent import Sistema
from src.config import Config, load_config
from src.ingest import construir_indice, indice_existe
from src.observabilidad import desde_config, leer, resumir

st.set_page_config(page_title="Asistente multi-tenant", layout="wide")


@st.cache_resource
def directorio():
    return cargar_directorio()


@st.cache_resource
def config_de(tenant_id: str) -> Config:
    # La interfaz nunca evalúa: no exige las claves del juez. El primer
    # despliegue en Render se paró tras el login por exigirlas (§38).
    return load_config(tenant_id, con_juez=False)


@st.cache_resource
def sistema_de(tenant_id: str) -> Sistema:
    cfg = config_de(tenant_id)
    return Sistema(cfg, registro=desde_config(cfg))


def asegurar_indice(cfg: Config) -> None:
    clave = f"indice_ok_{cfg.tenant.id}"
    if st.session_state.get(clave):
        return
    if not indice_existe(cfg):
        with st.spinner(f"Construyendo el índice de {cfg.tenant.nombre}..."):
            info = construir_indice(cfg)
        st.toast(f"Índice construido: {info['documentos']} fragmentos, {info['tokens_embebidos']} tokens de embeddings")
    st.session_state[clave] = True


# --- Autenticación ----------------------------------------------------------

try:
    usuarios = directorio()
except ValueError as error:
    st.error(str(error))
    st.stop()

import os

# Render expone el commit desplegado en RENDER_GIT_COMMIT. Verlo en pantalla es
# lo que permite saber qué versión se está probando: el primer despliegue
# mostró un commit en la página del blueprint y otro en la del servicio.
VERSION = os.getenv("RENDER_GIT_COMMIT", "local")[:7]

if "credencial" not in st.session_state:
    st.title("Asistente multi-tenant")
    st.caption(f"Versión {VERSION}")
    if usuarios.es_de_ejemplo:
        st.warning(
            "Este despliegue usa **las credenciales de ejemplo** (`usuarios.example.json`, "
            "contraseña `cambiar`). Vale para una demostración; no para un cliente."
        )
    with st.form("acceso"):
        usuario = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Entrar", type="primary"):
            credencial = usuarios.verificar(usuario.strip(), password)
            if credencial is None:
                st.error("Usuario o contraseña incorrectos.")
            else:
                st.session_state.credencial = credencial
                st.session_state.historial = []
                st.rerun()
    st.stop()

credencial = st.session_state.credencial
try:
    cfg = config_de(credencial.tenant)
except SystemExit as error:
    st.error(f"Configuración inválida para el inquilino {credencial.tenant!r}: {error}")
    st.stop()
persona = credencial.como_usuario()

# --- Barra lateral: quién, dónde, cuánto -------------------------------------

with st.sidebar:
    st.title(cfg.tenant.nombre)
    st.caption(f"{persona.nombre} · roles: {', '.join(persona.roles) or 'ninguno'}")
    if st.button("Salir"):
        del st.session_state.credencial
        st.rerun()
    st.divider()
    superado, gastado, tope = tope_superado()
    st.metric("Gasto registrado (todos los inquilinos)", f"{gastado:.4f} USD", help=(
        "Lo que suma el registro de producción. Excluye los embeddings y todo lo que "
        "no pase por esta interfaz: es un suelo (HALLAZGOS.md §16 y §37)."
    ))
    st.caption(f"Tope blando: {tope:.2f} USD. El tope duro es el prepago del proveedor.")
    propio = resumir(leer(cfg.tenant.id))
    if propio.get("consultas"):
        st.caption(
            f"Este inquilino: {propio['consultas']} consultas, "
            f"{propio['coste_usd_acumulado']:.4f} USD, p95 {propio['latencia_p95_s']} s."
        )
    escrituras = propio.get("acciones") or {}
    if any(escrituras.values()):
        st.caption(
            f"Escrituras: {escrituras.get('propuesta', 0)} propuestas, "
            f"{escrituras.get('aprobada', 0)} aprobadas, {escrituras.get('rechazada', 0)} rechazadas."
        )
    st.divider()
    st.markdown(
        f"**Proveedor:** {cfg.provider}  \n**Enrutador:** `{cfg.model_router}`  \n"
        f"**Generador:** `{cfg.model_generator}`  \n**Embeddings:** `{cfg.embed_model}`  \n"
        f"**Versión:** `{VERSION}`"
    )
    st.caption(
        f"AI Act: {cfg.tenant.ai_act.clasificacion.replace('_', ' ')}"
        + (f", anexo III {', '.join(cfg.tenant.ai_act.puntos_anexo_iii)} con excepción 6.3"
           if cfg.tenant.ai_act.puntos_anexo_iii else "")
    )

# --- Conversación ------------------------------------------------------------

st.title("Asistente interno")
# Artículo 50.1: quien interactúa sabe que es una IA. El texto lo declara el inquilino.
st.info(cfg.tenant.ai_act.aviso_usuario)

asegurar_indice(cfg)

for mensaje in st.session_state.historial:
    with st.chat_message(mensaje["rol"]):
        st.markdown(mensaje["texto"])
        if mensaje.get("meta"):
            with st.expander("Traza"):
                st.json(mensaje["meta"])

# --- Acciones pendientes de aprobación (human-in-the-loop) -------------------
#
# El modelo propone escrituras; solo se ejecutan cuando la persona pulsa
# Aprobar, y cada decisión queda en el registro de producción con quién y cuándo.
acciones = st.session_state.get("acciones") or {}
if acciones:
    st.subheader("Acciones pendientes de tu aprobación")
    st.caption(
        "El asistente ha propuesto escribir en el sistema. No se ejecuta nada hasta que apruebes."
    )
    for id_accion, accion in list(acciones.items()):
        with st.container(border=True):
            st.markdown(f"**{accion['herramienta']}** (id `{id_accion}`), propuesta por `{accion['usuario']}`")
            st.json(accion["argumentos"])
            col_a, col_r = st.columns(2)
            # El resultado se guarda en el historial ANTES del rerun: un
            # st.success seguido de st.rerun no llega a verse (visto en
            # Render, E-0008), y la referencia VIS es lo que la demo enseña.
            if col_a.button("Aprobar", key=f"aprobar_{id_accion}", type="primary"):
                try:
                    resultado = sistema_de(cfg.tenant.id).aprobar(id_accion, usuario=persona)
                except (KeyError, PermissionError) as error:
                    st.error(str(error))
                else:
                    del st.session_state["acciones"][id_accion]
                    st.session_state.historial.append({
                        "rol": "assistant",
                        "texto": (
                            f"**Acción `{id_accion}` aprobada por `{persona.id}`** y ejecutada. "
                            f"Resultado:\n\n```json\n{resultado['resultado'][:600]}\n```"
                        ),
                        "meta": resultado,
                    })
                    st.rerun()
            if col_r.button("Rechazar", key=f"rechazar_{id_accion}"):
                try:
                    salida = sistema_de(cfg.tenant.id).rechazar(id_accion, usuario=persona, motivo="rechazada en la interfaz")
                except KeyError as error:
                    st.error(str(error))
                else:
                    del st.session_state["acciones"][id_accion]
                    st.session_state.historial.append({
                        "rol": "assistant",
                        "texto": f"**Acción `{id_accion}` rechazada por `{persona.id}`.** No se ha ejecutado nada.",
                        "meta": salida,
                    })
                    st.rerun()

categorias = ", ".join(c.nombre for c in cfg.tenant.categorias)
consulta = st.chat_input(f"Pregunta sobre {categorias}...")
if consulta:
    superado, gastado, tope = tope_superado()
    if superado:
        st.error(
            f"Tope de gasto alcanzado: {gastado:.4f} USD registrados frente a un tope de "
            f"{tope:.2f} USD. No se atienden más consultas hasta que se revise."
        )
        st.stop()

    st.session_state.historial.append({"rol": "user", "texto": consulta})
    with st.chat_message("user"):
        st.markdown(consulta)

    with st.chat_message("assistant"):
        with st.spinner("Enrutando, recuperando y respondiendo..."):
            try:
                traza = sistema_de(cfg.tenant.id).responder(consulta, usuario=persona)
            except Exception as error:  # noqa: BLE001 -- frontera de UI: el fallo se muestra, no se traga
                st.error(f"La consulta falló: {type(error).__name__}: {error}")
                st.stop()
        st.markdown(traza["respuesta"])
        meta = {k: v for k, v in traza.items() if k not in ("respuesta", "contexto_recuperado")}
        for accion in traza.get("acciones_pendientes") or []:
            st.session_state.setdefault("acciones", {})[accion["id"]] = accion
        if traza.get("denegados_por_permiso"):
            st.caption(
                f"Retenido por permiso: {', '.join(traza['denegados_por_permiso'])}. "
                "Tu rol no alcanza esos documentos."
            )
        if traza.get("campos_redactados"):
            st.caption(f"Campos redactados: {', '.join(traza['campos_redactados'])}.")
        with st.expander("Traza"):
            st.json(meta)

    st.session_state.historial.append(
        {"rol": "assistant", "texto": traza["respuesta"], "meta": meta}
    )
    # La tarjeta de aprobación se pinta ANTES de procesar la consulta, así que
    # una acción recién propuesta no se ve hasta la siguiente pasada. Visto en
    # Render (E-0008): se fuerza la pasada aquí.
    if traza.get("acciones_pendientes"):
        st.rerun()
