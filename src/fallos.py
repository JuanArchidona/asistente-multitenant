"""Qué se le dice al usuario cuando una consulta no se puede atender (PLAN_ENTREGA B5).

El tutor lo pidió con un ejemplo (grabación del 6-10, 1:15): si la parte
inteligente se rompe, que el usuario no se quede colgado, que reciba una
respuesta del tipo "no podemos atenderte ahora, acércate a la oficina". Hasta
el 11-10 los tres canales decían "no se pudo atender (TipoDeError)" y la web
enseñaba la excepción: el fallo se registraba (§46) pero el usuario no sabía
qué hacer.

Esto no es un fallback silencioso, que la regla del proyecto prohíbe: no se
inventa una respuesta ni se cambia de modelo sin decirlo. Se dice que el
sistema ha fallado, de qué clase de fallo se trata y a quién acudir, y el
fallo se sigue registrando con su clase. El "a quién acudir" lo declara cada
inquilino en su manifiesto (`contacto_alternativo`), así que dar de alta un
cliente sigue sin exigir código.

La conmutación automática a otro proveedor se descartó con números: la de
Gemini está medida (§57) y cambia el enrutado (cobertura del riesgo 0,636 a
1,0 en el heredado, pierde las preguntas de actas), así que activarla en mitad
de una caída cambiaría el comportamiento del control de acceso sin que nadie
lo hubiera decidido. Queda como contingencia manual, con `LLM_PROVIDER`.
"""

PROVEEDOR_NO_DISPONIBLE = "proveedor_no_disponible"
LIMITE_DE_TASA = "limite_de_tasa"
CREDENCIAL = "credencial"
OTRO = "otro"

_NOMBRES_CAIDA = {
    "APIConnectionError", "APITimeoutError", "InternalServerError", "OverloadedError",
    "ServiceUnavailableError", "ServerError", "ConnectError", "ReadTimeout",
}
_NOMBRES_CREDENCIAL = {"AuthenticationError", "PermissionDeniedError", "ClientAuthError"}

_EXPLICACION = {
    PROVEEDOR_NO_DISPONIBLE: (
        "El servicio de IA del que depende el asistente no responde en este momento. "
        "Prueba de nuevo en unos minutos."
    ),
    LIMITE_DE_TASA: (
        "El servicio de IA está recibiendo más peticiones de las que admite. "
        "Prueba de nuevo en unos minutos."
    ),
    CREDENCIAL: (
        "El asistente está fuera de servicio por un problema de configuración. "
        "El fallo ha quedado registrado para el equipo técnico."
    ),
    OTRO: "Ha ocurrido un error interno. El fallo ha quedado registrado para el equipo técnico.",
}


def clasificar(error: BaseException) -> str:
    """Clase del fallo, por el código HTTP si lo trae y si no por el tipo.

    No importa los SDK de los proveedores: los errores de Anthropic llevan
    `status_code` y los de Google `code`, y el nombre de la clase basta para
    los de red.
    """
    estado = getattr(error, "status_code", None) or getattr(error, "code", None)
    nombre = type(error).__name__
    if estado == 429 or nombre == "RateLimitError" or "límite de tasa" in str(error):
        return LIMITE_DE_TASA
    if estado in (401, 403) or nombre in _NOMBRES_CREDENCIAL:
        return CREDENCIAL
    if (isinstance(estado, int) and estado >= 500) or nombre in _NOMBRES_CAIDA or isinstance(
        error, (TimeoutError, ConnectionError)
    ):
        return PROVEEDOR_NO_DISPONIBLE
    return OTRO


def mensaje_para_el_usuario(error: BaseException, contacto_alternativo: str = "") -> str:
    """Texto determinista para el usuario: qué ha pasado y a quién acudir."""
    clase = clasificar(error)
    partes = [f"La consulta no se pudo atender ({type(error).__name__}).", _EXPLICACION[clase]]
    if contacto_alternativo:
        partes.append(contacto_alternativo)
    return " ".join(partes)
