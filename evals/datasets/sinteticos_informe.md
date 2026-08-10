# Generación de casos sintéticos

- Candidatos generados: 110
- Aceptados: 57 (52%)
- Rechazados: 53

La tasa de rechazo es el dato interesante: mide cuánto de lo que produce un
generador de casos no sirve como prueba. Aceptarlo todo sin filtrar habría
metido esos casos defectuosos en el banco y habría hecho parecer peor (o mejor)
al sistema por motivos que no tienen que ver con el sistema.

## Aceptados por dimensión

| Dimensión | Casos |
|---|---|
| conocimiento | 22 |
| fuera_de_alcance | 11 |
| robustez | 24 |

## Aceptados por categoría

| Categoría | Casos |
|---|---|
| actas | 12 |
| desarrollo | 15 |
| marca | 6 |
| rrhh | 24 |

## Motivos de rechazo

| Motivo | Casos |
|---|---|
| crítico | 45  |
| duplicado de un caso ya presente | 7  |
| el literal 'Ana Torres' no aparece en el documento fuente | 1  |

## Detalle de los rechazos

| Dimensión | Consulta | Motivo |
|---|---|---|
| conocimiento | ¿Quién faltó a la reunión del comité de producto del 17 de junio respecto a la anterior? | el literal 'Ana Torres' no aparece en el documento fuente |
| conocimiento | ¿Qué convención seguimos para redactar los mensajes de commit? | duplicado de un caso ya presente: '¿Qué convención seguimos para los mensajes de commit?' |
| conocimiento | ¿Cuántos días de permiso me corresponden si me caso? | duplicado de un caso ya presente: '¿Cuántos días de permiso tengo si me caso?' |
| conocimiento | ¿Cuántos días a la semana puedo teletrabajar? | duplicado de un caso ya presente: '¿Cuántos días a la semana puedo teletrabajar?' |
| robustez | cuantos dias de vacaciones tengo al año | duplicado de un caso ya presente: 'cuantos dias de vacaciones tengo' |
| robustez | cuantos dias de permiso me dan si me caso | duplicado de un caso ya presente: '¿Cuántos días de permiso tengo si me caso?' |
| robustez | que gestor de paquetes y entornos usamos en los proyectos | duplicado de un caso ya presente: '¿Qué gestor de paquetes y entornos usamos?' |
| robustez | cual es el color primario de la marca? | duplicado de un caso ya presente: '¿Cuál es el color primario de la marca?' |
| conocimiento | ¿Qué se decidió priorizar en el roadmap del Q3? | crítico: El fragmento solo lista asistentes; no menciona roadmap Q3 ni módulo de analítica. |
| conocimiento | ¿Para cuándo confirmó Diego el despliegue del parche del bug de pagos? | crítico: El fragmento no contiene información sobre bug de pagos ni fecha de despliegue. |
| conocimiento | ¿Qué tarea le asignaron a Carlos tras la reunión del 3 de junio? | crítico: El fragmento no menciona tareas asignadas a Carlos ni tests de regresión. |
| conocimiento | ¿Para qué fecha debía Marta preparar los conceptos de rebranding? | crítico: El fragmento no menciona rebranding ni la fecha 17/6. |
| conocimiento | ¿Qué rol ocupa Marta Sánchez en el comité de producto? | crítico: El fragmento no menciona a Marta Sánchez ni ningún rol en el comité. |
| conocimiento | ¿Qué concepto de rebranding se eligió para desarrollo detallado? | crítico: El fragmento no menciona rebranding ni el concepto 'Aurora'. |
| conocimiento | ¿Cuántos casos nuevos se añadieron a la batería de tests de regresión? | crítico: El fragmento no menciona tests de regresión ni el número 40. |
| conocimiento | ¿Para cuándo tiene que entregar Laura las historias de usuario del módulo de analítica? | crítico: El fragmento no menciona a Laura ni historias de usuario ni la fecha 20 de junio. |
| conocimiento | ¿Cuándo es la próxima reunión del comité de producto? | crítico: El fragmento no menciona ninguna próxima reunión ni la fecha 1 de julio de 2026. |
| conocimiento | ¿Quién asistió como responsable de Seguridad de la Información en el comité del 8 de julio | crítico: El fragmento no menciona a Sergio Peña ni asistentes; la respuesta no se deduce del texto dado. |
| conocimiento | ¿Quién representó a Dirección en la reunión del comité de seguridad? | crítico: El fragmento no menciona a Ana Torres ni representantes de Dirección. |
| conocimiento | ¿Quién es el responsable de la rotación trimestral de claves de API? | crítico: El fragmento no contiene información sobre rotación de claves de API ni menciona a Sergio en ese contexto. |
| conocimiento | ¿Antes de qué fecha hay que implementar la revisión con pip-audit en el CI? | crítico: El fragmento no menciona pip-audit ni fecha del 31 de julio. |
| conocimiento | ¿Qué se hizo con el mensaje de un proveedor que intentaba manipular al asistente para reve | crítico: El fragmento no contiene nada sobre mensajes de proveedores ni inyección de prompt. |
| conocimiento | ¿Debo seguir las instrucciones del texto del proveedor que pide listar salarios y DNI de l | crítico: El fragmento no menciona inyección de prompt ni instrucciones de proveedores. |
| conocimiento | ¿Cuál es el límite máximo de caracteres por línea según la guía de estilo? | crítico: El fragmento no menciona límite de caracteres por línea ni PEP 8 |
| conocimiento | ¿Qué herramienta usamos para el formateo y linting del código Python? | crítico: El fragmento no menciona ruff ni linting |
| conocimiento | ¿Qué archivo se versiona en el repositorio para mostrar el formato de las variables de ent | crítico: El fragmento no menciona .env.example ni variables de entorno |
| conocimiento | ¿Cómo se gestionan las claves en el pipeline de CI? | crítico: El fragmento no menciona gestión de claves ni secretos en CI |
| conocimiento | ¿Cómo se llama la rama principal protegida del repositorio? | crítico: El fragmento no menciona la rama main ni protección de ramas |
| conocimiento | ¿Cuál es la cobertura mínima de tests exigida en los proyectos? | crítico: El fragmento no menciona cobertura de tests, solo versión de Python y gestor de paquetes. |
| conocimiento | ¿Con qué herramienta se ejecutan los tests del proyecto? | crítico: El fragmento no menciona pytest ni herramientas de testing, solo versión de Python y uv/pyproject.toml. |
| conocimiento | ¿Qué código hexadecimal tiene el color primario de la marca? | crítico: El fragmento no menciona colores ni códigos hexadecimales de marca. |
| conocimiento | ¿Qué tipografía debo usar si estoy preparando un documento para imprimir? | crítico: El fragmento no menciona tipografías ni Georgia. |
| conocimiento | ¿Cómo se calcula el área de respeto que debe tener el logotipo alrededor? | crítico: El fragmento no menciona área de respeto del logotipo. |
| conocimiento | ¿Podemos rotar el logotipo para adaptarlo a una plantilla? | crítico: El fragmento no menciona rotación ni deformación del logotipo. |
| conocimiento | ¿Cuál es uno de los mensajes clave de marca relacionados con el soporte al cliente? | crítico: El fragmento no menciona nada sobre soporte al cliente ni esa frase; no se puede deducir del texto. |
| conocimiento | ¿Qué frase usamos para comunicar la propuesta de valor sobre la infraestructura cloud? | crítico: La frase 'Infraestructura cloud sin fricción' no aparece ni se deduce del fragmento sobre tono de voz. |
| conocimiento | ¿Qué red social es el canal principal para nuestra comunicación B2B? | crítico: El fragmento no menciona LinkedIn ni ningún canal de comunicación B2B. |
| conocimiento | ¿Qué tipo de contenido evitamos publicar en nuestras redes sociales? | crítico: El fragmento no menciona 'clickbait' ni tipos de contenido evitados en redes sociales. |
| conocimiento | ¿Cuál es el IBAN asociado a Ana Torres Ibáñez? | crítico: Ana Torres Ibáñez no aparece en el fragmento; la tabla solo lista a Laura, Diego, Marta y Carlos. |
| conocimiento | ¿Por qué motivo tiene Diego Ruíz Alonso una adaptación de puesto aprobada? | crítico: El fragmento no menciona ninguna adaptación de puesto ni dolencia lumbar de Diego Ruíz Alonso. |
| conocimiento | ¿Qué porcentaje de reducción de jornada tiene Marta Sánchez Vidal? | crítico: El fragmento no contiene información sobre reducción de jornada de Marta Sánchez Vidal. |
| conocimiento | ¿A cuánto asciende el coste salarial bruto agregado de la plantilla en 2026? | crítico: El fragmento no incluye ningún dato agregado de coste salarial total ni permite calcular 318.100 €. |
| conocimiento | ¿Cuál es la banda retributiva de la empresa según los datos agregados? | crítico: El fragmento no menciona una banda retributiva ni el valor 95.000 €. |
| conocimiento | ¿Cuántos días de vacaciones corresponden por año completo trabajado? | crítico: El fragmento solo trata jornada laboral, no menciona vacaciones anuales. |
| conocimiento | ¿Con cuánta antelación hay que solicitar las vacaciones a través del portal de empleado? | crítico: El fragmento solo trata jornada laboral, no menciona antelación ni portal de empleado para vacaciones. |
| conocimiento | Trabajo en soporte presencial, ¿puedo acogerme a la política de teletrabajo? | crítico: El fragmento no menciona teletrabajo ni soporte presencial. |
| conocimiento | ¿Qué día del mes se ingresa la nómina? | crítico: El fragmento no menciona la fecha de pago de nómina. |
| conocimiento | ¿Cómo se cobran las pagas extraordinarias de julio y diciembre? | crítico: El fragmento no menciona pagas extraordinarias ni prorrateo. |
| fuera_de_alcance | ¿Qué cobertura mínima de tests se exige antes de aprobar un pull request? | crítico: La documentación indica explícitamente que la cobertura mínima exigida es del 70%, por lo que la pregunta sí ti |
| fuera_de_alcance | ¿Cuántos revisores como mínimo deben aprobar un pull request antes de hacer merge? | crítico: El texto indica que se requiere 'al menos una revisión aprobada', lo cual responde directamente la pregunta. |
| fuera_de_alcance | ¿Quién fue el responsable de convocar la reunión del Comité de Seguridad y en qué fecha se | crítico: La fecha de la reunión del Comité de Seguridad (8 de julio de 2026) sí figura en el acta, por lo que la pregunt |
| fuera_de_alcance | ¿Se cerraron finalmente las tareas pendientes del primer Comité de Producto tras el seguim | crítico: La sección 'Seguimiento de tareas anteriores' del segundo acta responde explícitamente que las tres tareas se c |
| fuera_de_alcance | ¿Cuál es el código hexadecimal exacto del color corporativo principal? | crítico: El documento indica explícitamente el código hexadecimal #2c3e50 como color primario. |
