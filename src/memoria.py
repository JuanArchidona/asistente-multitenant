"""Memoria entre turnos por reescritura de la consulta (PLAN_ENTREGA C3).

El sistema es de un turno: cada consulta se enruta y se responde sola. La
interfaz pinta un historial y da a entender lo contrario, y un seguimiento
como "¿y la baja?" o "¿y en un alquiler?" llega al enrutador sin el tema del
que habla. El Módulo 2 trató la memoria de los agentes; aquí se mide el
defecto con un banco de conversaciones aparte (`evals/conversaciones.py`) y
se prueba la solución más acotada que existe: antes de enrutar, el modelo
reescribe el seguimiento como una pregunta que se entienda sola, con el
último turno delante. El resto del sistema no cambia, y el control de acceso
tampoco: la consulta reescrita pasa por el mismo `where` que cualquier otra.

Va detrás de `MEMORIA_TURNOS` (`off` por defecto, `reescritura` lo activa),
así que la línea base no se mueve. La reescritura cuesta una llamada más al
modelo por turno con historial, y la traza guarda la consulta original y la
reescrita para que se vea qué se buscó de verdad.
"""

SYSTEM_REESCRITURA = """Reescribes la última pregunta de un empleado para que se entienda sola,
sin el historial de la conversación. Usa el historial solo para completar lo
que falta (el tema, el documento, la persona, el tipo de operación). No
respondas a la pregunta, no añadas datos que no estén en ella o en el
historial y no cambies lo que pide. Si ya se entiende sola, devuélvela igual.
Devuelve SOLO la pregunta reescrita, en español, sin comillas ni explicaciones."""

TURNOS_DE_CONTEXTO = 2
MAX_CARACTERES_RESPUESTA = 600


def contexto_de_historial(historial: list[tuple[str, str]]) -> str:
    """Los últimos turnos como texto, con las respuestas recortadas."""
    lineas = []
    for pregunta, respuesta in historial[-TURNOS_DE_CONTEXTO:]:
        lineas.append(f"Empleado: {pregunta}")
        lineas.append(f"Asistente: {(respuesta or '')[:MAX_CARACTERES_RESPUESTA]}")
    return "\n".join(lineas)


def reescribir(chat, modelo: str, historial: list[tuple[str, str]], consulta: str) -> str:
    """La consulta reescrita para que se entienda sola. Sin historial, la misma."""
    if not historial:
        return consulta
    usuario = (
        f"Historial:\n{contexto_de_historial(historial)}\n\n"
        f"Última pregunta: {consulta}\n\nPregunta reescrita:"
    )
    salida = (chat.completar(SYSTEM_REESCRITURA, usuario, modelo, temperature=0.0) or "").strip()
    salida = salida.strip('"').strip("«»").strip()
    return salida or consulta
