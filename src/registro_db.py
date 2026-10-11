"""Copia persistente del registro de producción en una base SQL (PLAN_ENTREGA B6).

El registro de `observabilidad.py` escribe un JSONL en el disco del proceso, y
en el plan gratuito de Render ese disco se borra en cada despertar: lo que se
registraba en producción no sobrevivía, y el feedback de las entregas 3.1 y 3.3
pedía justo eso, trazas y coste acumulado en producción. Desde el 11-10-2026,
si `REGISTRO_DB_URL` está definida, cada línea va además a Postgres (el
gratuito de Render, `asistente-registro`, en la misma región).

Una tabla, `registro`, con el inquilino, la fecha, el usuario y la línea JSON
entera como texto: el mismo contenido que el fichero, para que leer, resumir,
suprimir y purgar den lo mismo venga de donde venga. La supresión y la purga
de `RETENCION.md` se aplican aquí igual que al fichero, con la misma lápida:
una copia persistente que no se pudiera borrar rompería el derecho de
supresión justo donde los datos duran más.

Funciona con Postgres (`postgresql://...`, con `psycopg`) y con SQLite
(`sqlite:///ruta`), que es lo que usan las pruebas para no necesitar red.
"""
import json
import sqlite3
import threading
from pathlib import Path


class AlmacenRegistro:
    def __init__(self, url: str):
        self.url = url
        self.dialecto = "sqlite" if url.startswith("sqlite:///") else "postgres"
        if self.dialecto == "postgres" and not url.startswith(("postgres://", "postgresql://")):
            raise ValueError("REGISTRO_DB_URL tiene que empezar por postgresql:// o sqlite:///")
        self._marcador = "?" if self.dialecto == "sqlite" else "%s"
        self._conexion = None
        self._lock = threading.Lock()
        self._con_tabla = False

    # --- Conexión ------------------------------------------------------------

    def _conectar(self):
        if self.dialecto == "sqlite":
            ruta = self.url.removeprefix("sqlite:///")
            Path(ruta).parent.mkdir(parents=True, exist_ok=True)
            return sqlite3.connect(ruta, check_same_thread=False, isolation_level=None)
        import psycopg

        return psycopg.connect(self.url, autocommit=True, connect_timeout=10)

    def _ejecutar(self, sql: str, parametros: tuple = (), devolver: bool = False):
        """Ejecuta con una conexión reutilizada; si se cayó, reconecta una vez."""
        sql = sql.replace("?", self._marcador)
        with self._lock:
            for intento in (1, 2):
                try:
                    if self._conexion is None:
                        self._conexion = self._conectar()
                    if not self._con_tabla:
                        self._crear_tabla()
                    cursor = self._conexion.cursor()
                    cursor.execute(sql, parametros)
                    filas = cursor.fetchall() if devolver else None
                    cursor.close()
                    return filas
                except Exception:
                    self._cerrar()
                    if intento == 2:
                        raise
        return None

    def _crear_tabla(self) -> None:
        id_col = "INTEGER PRIMARY KEY" if self.dialecto == "sqlite" else "BIGSERIAL PRIMARY KEY"
        cursor = self._conexion.cursor()
        cursor.execute(
            f"CREATE TABLE IF NOT EXISTS registro (id {id_col}, tenant TEXT NOT NULL, "
            "ts TEXT NOT NULL, usuario TEXT, linea TEXT NOT NULL)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS registro_tenant_ts ON registro (tenant, ts)")
        cursor.close()
        self._con_tabla = True

    def _cerrar(self) -> None:
        try:
            if self._conexion is not None:
                self._conexion.close()
        finally:
            self._conexion = None
            self._con_tabla = False

    # --- Operaciones -----------------------------------------------------------

    def escribir(self, tenant: str, registro: dict) -> None:
        self._ejecutar(
            "INSERT INTO registro (tenant, ts, usuario, linea) VALUES (?, ?, ?, ?)",
            (tenant, registro.get("ts") or "", registro.get("usuario"),
             json.dumps(registro, ensure_ascii=False)),
        )

    def leer(self, tenant: str) -> list[dict]:
        filas = self._ejecutar(
            "SELECT linea FROM registro WHERE tenant = ? ORDER BY id", (tenant,), devolver=True
        )
        salida, ilegibles = [], 0
        for (linea,) in filas or []:
            try:
                salida.append(json.loads(linea))
            except json.JSONDecodeError:
                ilegibles += 1
        if ilegibles:
            salida.append({"_ilegible": ilegibles})
        return salida

    def inquilinos(self) -> list[str]:
        filas = self._ejecutar("SELECT DISTINCT tenant FROM registro", devolver=True)
        return sorted(t for (t,) in filas or [])

    def quitar(self, tenant: str, *, usuario: str | None = None, anteriores_a: str | None = None,
               clave_lapida: str) -> int:
        """Quita las líneas de un usuario o anteriores a una fecha; nunca las lápidas."""
        if (usuario is None) == (anteriores_a is None):
            raise ValueError("se quita por usuario o por fecha, no por las dos ni por ninguna")
        condicion, valor = ("usuario = ?", usuario) if usuario is not None else ("ts < ?", anteriores_a)
        no_lapida = "linea NOT LIKE ?"
        patron = f'%"{clave_lapida}": true%'
        cuenta = self._ejecutar(
            f"SELECT COUNT(*) FROM registro WHERE tenant = ? AND {condicion} AND {no_lapida}",
            (tenant, valor, patron), devolver=True,
        )[0][0]
        if cuenta:
            self._ejecutar(
                f"DELETE FROM registro WHERE tenant = ? AND {condicion} AND {no_lapida}",
                (tenant, valor, patron),
            )
        return int(cuenta)
