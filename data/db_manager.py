"""
data/db_manager.py
Capa de Acceso a Datos: Esquema SQLite y todas las consultas CRUD.
"""
import sqlite3
import os
from datetime import datetime, date, time, timedelta
import random
from typing import Optional

DB_PATH = os.getenv("DB_PATH", "sentinel_core.db")

# ──────────────────────────────────────────────
# CONEXIÓN
# ──────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    """Retorna una conexión con claves foráneas activas."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


# ──────────────────────────────────────────────
# CREACIÓN DEL ESQUEMA
# ──────────────────────────────────────────────

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS personal (
    id_biometrico   TEXT PRIMARY KEY,
    nombre          TEXT NOT NULL,
    departamento    TEXT NOT NULL,
    estado          TEXT NOT NULL DEFAULT 'activo'  -- activo | inactivo
);

CREATE TABLE IF NOT EXISTS horarios_internos (
    id_horario          INTEGER PRIMARY KEY AUTOINCREMENT,
    id_biometrico       TEXT NOT NULL,
    dia_semana          INTEGER NOT NULL,   -- 0=Lun, 1=Mar, ..., 4=Vie
    hora_entrada        TEXT NOT NULL,      -- 'HH:MM'
    hora_salida         TEXT NOT NULL,      -- 'HH:MM'
    tolerancia_minutos  INTEGER NOT NULL DEFAULT 5,
    FOREIGN KEY (id_biometrico) REFERENCES personal(id_biometrico)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS logs_asistencia (
    id_log          INTEGER PRIMARY KEY AUTOINCREMENT,
    id_biometrico   TEXT NOT NULL,
    fecha_hora      TEXT NOT NULL,          -- 'YYYY-MM-DD HH:MM:SS'
    tipo_marcacion  TEXT NOT NULL,          -- 'Entrada' | 'Salida'
    FOREIGN KEY (id_biometrico) REFERENCES personal(id_biometrico)
        ON DELETE CASCADE
);
"""

def inicializar_db():
    """Crea las tablas si no existen."""
    with get_connection() as conn:
        conn.executescript(SCHEMA_SQL)
    print("[DB] Esquema inicializado correctamente.")


# ──────────────────────────────────────────────
# CRUD: PERSONAL
# ──────────────────────────────────────────────

def insertar_personal(id_bio: str, nombre: str, departamento: str) -> bool:
    """Inserta un nuevo docente. Retorna True si fue exitoso."""
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO personal (id_biometrico, nombre, departamento) VALUES (?, ?, ?)",
                (id_bio, nombre, departamento)
            )
        return True
    except sqlite3.IntegrityError:
        return False  # id_biometrico duplicado

def obtener_personal() -> list:
    """Retorna todos los docentes activos."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM personal WHERE estado = 'activo' ORDER BY nombre"
        ).fetchall()
    return [dict(r) for r in rows]

def actualizar_personal(id_bio: str, nombre: str, departamento: str):
    with get_connection() as conn:
        conn.execute(
            "UPDATE personal SET nombre=?, departamento=? WHERE id_biometrico=?",
            (nombre, departamento, id_bio)
        )

def eliminar_personal(id_bio: str):
    """Marca como inactivo (soft delete) para preservar historial."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE personal SET estado='inactivo' WHERE id_biometrico=?",
            (id_bio,)
        )


# ──────────────────────────────────────────────
# CRUD: HORARIOS
# ──────────────────────────────────────────────

def insertar_horario(id_bio: str, dia: int, entrada: str, salida: str, tolerancia: int = 5):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO horarios_internos
               (id_biometrico, dia_semana, hora_entrada, hora_salida, tolerancia_minutos)
               VALUES (?, ?, ?, ?, ?)""",
            (id_bio, dia, entrada, salida, tolerancia)
        )

def obtener_horarios(id_bio: str) -> list:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM horarios_internos WHERE id_biometrico=? ORDER BY dia_semana",
            (id_bio,)
        ).fetchall()
    return [dict(r) for r in rows]

def obtener_horario_dia(id_bio: str, dia: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            """SELECT * FROM horarios_internos
               WHERE id_biometrico=? AND dia_semana=?""",
            (id_bio, dia)
        ).fetchone()
    return dict(row) if row else None

def eliminar_horarios(id_bio: str):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM horarios_internos WHERE id_biometrico=?", (id_bio,)
        )


# ──────────────────────────────────────────────
# CRUD: LOGS DE ASISTENCIA
# ──────────────────────────────────────────────

def insertar_log(id_bio: str, fecha_hora: str, tipo: str):
    """tipo: 'Entrada' | 'Salida'"""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO logs_asistencia (id_biometrico, fecha_hora, tipo_marcacion) VALUES (?, ?, ?)",
            (id_bio, fecha_hora, tipo)
        )

def obtener_logs_rango(fecha_inicio: str, fecha_fin: str) -> list:
    """Retorna logs entre dos fechas 'YYYY-MM-DD' (inclusive)."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT l.*, p.nombre, p.departamento
               FROM logs_asistencia l
               JOIN personal p ON l.id_biometrico = p.id_biometrico
               WHERE DATE(l.fecha_hora) BETWEEN ? AND ?
               ORDER BY l.fecha_hora""",
            (fecha_inicio, fecha_fin)
        ).fetchall()
    return [dict(r) for r in rows]

def limpiar_logs():
    """Limpia logs (solo para desarrollo/pruebas)."""
    with get_connection() as conn:
        conn.execute("DELETE FROM logs_asistencia")


# ──────────────────────────────────────────────
# MOCK DATA
# ──────────────────────────────────────────────

DOCENTES_MOCK = [
    ("001", "Ana García López",      "Matemáticas"),
    ("002", "Carlos Mendoza Ruiz",   "Comunicación"),
    ("003", "María Torres Vda.",     "Ciencias"),
    ("004", "Jorge Quispe Mamani",   "Historia"),
    ("005", "Lucía Flores Conde",    "Educación Física"),
    ("006", "Roberto Chávez Pinto",  "Arte"),
    ("007", "Patricia Salas Vega",   "Inglés"),
    ("008", "Héctor Lima Cano",      "Computación"),
]

# Horarios base (lunes a viernes) — algunos con horario corrido, otros partido
HORARIOS_MOCK = {
    "001": ("07:30", "13:00", 5),
    "002": ("07:45", "13:15", 5),
    "003": ("08:00", "13:00", 10),
    "004": ("07:30", "12:30", 5),
    "005": ("08:00", "14:00", 10),
    "006": ("07:45", "13:00", 5),
    "007": ("08:00", "13:30", 5),
    "008": ("07:30", "13:00", 5),
}

def cargar_mock_data():
    """
    Inserta personal, horarios y logs de asistencia simulados
    para las últimas 4 semanas laborales.
    Solo ejecuta si la tabla personal está vacía.
    """
    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM personal").fetchone()[0]
    if count > 0:
        print("[DB] Mock data ya existe, se omite la carga.")
        return

    print("[DB] Cargando mock data...")

    # 1. Personal
    for id_bio, nombre, depto in DOCENTES_MOCK:
        insertar_personal(id_bio, nombre, depto)

    # 2. Horarios (lunes a viernes para cada docente)
    for id_bio, (entrada, salida, tol) in HORARIOS_MOCK.items():
        for dia in range(5):  # 0=Lun … 4=Vie
            insertar_horario(id_bio, dia, entrada, salida, tol)

    # 3. Logs simulados — 4 semanas hacia atrás desde hoy
    hoy = date.today()
    # Ir al lunes de la semana actual
    lunes = hoy - timedelta(days=hoy.weekday())
    # Retroceder 4 semanas
    inicio = lunes - timedelta(weeks=4)

    random.seed(42)  # Reproducibilidad

    for id_bio, (hora_entrada_str, hora_salida_str, tolerancia) in HORARIOS_MOCK.items():
        h_ent = time(*map(int, hora_entrada_str.split(":")))
        h_sal = time(*map(int, hora_salida_str.split(":")))

        fecha_iter = inicio
        while fecha_iter < hoy:
            if fecha_iter.weekday() < 5:  # Solo días laborales
                # 10% probabilidad de falta
                if random.random() < 0.10:
                    fecha_iter += timedelta(days=1)
                    continue

                # Generar tardanza aleatoria: -2 a +15 minutos
                delta_entrada = random.randint(-2, 15)
                dt_entrada = datetime.combine(fecha_iter, h_ent) + timedelta(minutes=delta_entrada)

                # Salida: -5 a +10 minutos respecto a horario
                delta_salida = random.randint(-5, 10)
                dt_salida = datetime.combine(fecha_iter, h_sal) + timedelta(minutes=delta_salida)

                insertar_log(id_bio, dt_entrada.strftime("%Y-%m-%d %H:%M:%S"), "Entrada")
                insertar_log(id_bio, dt_salida.strftime("%Y-%m-%d %H:%M:%S"), "Salida")

            fecha_iter += timedelta(days=1)

    print(f"[DB] Mock data cargada: {len(DOCENTES_MOCK)} docentes, 4 semanas de logs.")
