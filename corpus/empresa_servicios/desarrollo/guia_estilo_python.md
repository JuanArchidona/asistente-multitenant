# Guía de Estilo de Desarrollo — Equipo de Ingeniería

## Lenguaje y versiones
El estándar es Python 3.11 o superior. Todo proyecto nuevo usa `uv` como gestor de
paquetes y entorno, con `pyproject.toml` como única fuente de dependencias.

## Estilo de código
- Se sigue PEP 8 con líneas de hasta 100 caracteres.
- Formateo y linting con `ruff`. El CI rechaza cualquier PR que no pase `ruff check`.
- Type hints obligatorios en funciones públicas. Se valida con `mypy` en modo estricto.

## Gestión de secretos
Las credenciales nunca se versionan. Se usan ficheros `.env` (en `.gitignore`) y se
versiona únicamente `.env.example` con placeholders. Las claves en CI van por secretos
del repositorio, nunca en texto plano.

## Control de versiones
- Rama principal: `main`, protegida. No se hace push directo.
- Los commits siguen Conventional Commits (`feat:`, `fix:`, `docs:`, etc.).
- Toda funcionalidad entra por Pull Request con al menos una revisión aprobada.

## Estructura de proyectos
La lógica vive en `src/`. Cada módulo tiene una responsabilidad única. Los tests
en `tests/`, ejecutados con `pytest`. La cobertura mínima exigida es del 70%.
