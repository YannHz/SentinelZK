# 🛡 SentinelZK

**Sistema de Gestión de Asistencia Inteligente**  
Versión 1.0 — Fase 1 (Prototipo Offline)

---

## Requisitos

- Python **3.8** (obligatorio para compatibilidad con Windows 7)
- Windows 7 / 10 / 11

---

## Instalación

```bash
# 1. Clonar o descomprimir el proyecto
cd SentinelZK

# 2. Crear entorno virtual (recomendado)
python -m venv venv
venv\Scripts\activate       # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
# Editar el archivo .env con la IP de tu reloj ZKTeco
```

---

## Ejecución

```bash
python main.py
```

Al primer arranque:
- Se crea automáticamente `sentinel_core.db`
- Se cargan **8 docentes de prueba** con 4 semanas de logs simulados

---

## Estructura del Proyecto

```
SentinelZK/
├── main.py                  # Punto de entrada
├── requirements.txt
├── .env                     # ← Configurar IP del reloj ZKTeco
│
├── ui/
│   ├── app_window.py        # Ventana principal (Dashboard, Docentes, Reportes)
│   └── forms_personnel.py   # CRUD de docentes y horarios
│
├── logic/
│   ├── attendance_engine.py # Motor de cálculo de tardanzas
│   └── async_workers.py     # Gestión de hilos (UI no-bloqueante)
│
└── data/
    ├── db_manager.py        # Esquema SQLite + Mock Data
    └── report_exporter.py   # Exportador de Excel (.xlsx)
```

---

## Módulos por Fase

| Fase | Estado | Descripción |
|------|--------|-------------|
| 1 | ✅ Completo | GUI + SQLite + Mock Data |
| 2 | 🔜 Pendiente | Integración TCP/IP con uFace 800 |
| 3 | 🔜 Pendiente | Manejo de excepciones (rebotes, olvidos) |
| 4 | 🔜 Pendiente | Compilación con PyInstaller |

---

## Fórmula de Tardanza

```
Minutos_Retraso = Max(0, (Minutos_Reales - Minutos_Oficiales) - Tolerancia)
```

Si `Minutos_Retraso > 0` → Estado: **Tardanza**  
Si no → Estado: **Puntual**

---

## Compilar a .exe (Fase 4)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name SentinelZK main.py
```
