"""
main.py
Punto de entrada de SentinelZK.
Inicializa la base de datos, carga mock data (si aplica) y lanza la GUI.
"""
import os
import sys

# ── Cargar variables de entorno ANTES de cualquier importación interna ──
from dotenv import load_dotenv
load_dotenv()

# ── Agregar el directorio raíz al path para imports relativos ──
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.db_manager import inicializar_db, cargar_mock_data
from ui.app_window import AppWindow


def main():
    print("=" * 50)
    print("  SentinelZK — Sistema de Gestión de Asistencia")
    print("=" * 50)

    # 1. Preparar base de datos
    inicializar_db()

    # 2. Cargar datos de prueba (solo si la DB está vacía)
    cargar_mock_data()

    # 3. Lanzar interfaz gráfica
    app = AppWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
