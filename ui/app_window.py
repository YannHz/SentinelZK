"""
ui/app_window.py
Ventana principal de SentinelZK.
Implementa navegación por secciones: Dashboard, Docentes, Reportes.
"""
import os
import threading
import customtkinter as ctk
from tkinter import messagebox
from datetime import date, timedelta

from ui.forms_personnel import FormPersonal
from logic.attendance_engine import procesar_asistencia, obtener_resumen_rapido
from data.report_exporter import generar_reportes
from logic.async_workers import WorkerThread


# ── Tema ──
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

APP_NAME    = os.getenv("APP_NAME", "SentinelZK")
VERSION     = "1.0.0 — Fase 1"


class AppWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME}  |  {VERSION}")
        self.geometry("1100x680")
        self.minsize(900, 580)

        self._frame_activo = None
        self._construir_layout()
        self._mostrar_dashboard()

    # ──────────────────────────────────────────
    # LAYOUT PRINCIPAL
    # ──────────────────────────────────────────

    def _construir_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ── Barra lateral ──
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(6, weight=1)

        # Logo / nombre
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="#0d1117", corner_radius=0)
        logo_frame.grid(row=0, column=0, sticky="ew")

        ctk.CTkLabel(
            logo_frame,
            text="🛡 SentinelZK",
            font=ctk.CTkFont(family="Consolas", size=18, weight="bold"),
            text_color="#58a6ff",
        ).pack(pady=(20, 4), padx=16)

        ctk.CTkLabel(
            logo_frame,
            text="Sistema de Asistencia",
            font=ctk.CTkFont(size=11),
            text_color="gray60",
        ).pack(pady=(0, 16), padx=16)

        # Botones de navegación
        self._nav_buttons = {}
        nav_items = [
            ("📊  Dashboard",   "dashboard"),
            ("👥  Docentes",    "docentes"),
            ("📄  Reportes",    "reportes"),
        ]
        for i, (texto, clave) in enumerate(nav_items, start=1):
            btn = ctk.CTkButton(
                self.sidebar,
                text=texto,
                anchor="w",
                font=ctk.CTkFont(size=13),
                fg_color="transparent",
                text_color=("gray90", "gray90"),
                hover_color=("gray25", "gray25"),
                corner_radius=8,
                height=40,
                command=lambda c=clave: self._navegar(c),
            )
            btn.grid(row=i, column=0, padx=8, pady=3, sticky="ew")
            self._nav_buttons[clave] = btn

        # Versión al fondo
        ctk.CTkLabel(
            self.sidebar,
            text=f"v{VERSION.split('—')[0].strip()}",
            font=ctk.CTkFont(size=10),
            text_color="gray50",
        ).grid(row=7, column=0, pady=12)

        # ── Área de contenido ──
        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray92", "gray14"))
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

    # ──────────────────────────────────────────
    # NAVEGACIÓN
    # ──────────────────────────────────────────

    def _navegar(self, seccion: str):
        if self._frame_activo:
            self._frame_activo.destroy()

        # Resaltar botón activo
        for clave, btn in self._nav_buttons.items():
            btn.configure(
                fg_color="#1f6feb" if clave == seccion else "transparent"
            )

        if seccion == "dashboard":
            self._mostrar_dashboard()
        elif seccion == "docentes":
            self._mostrar_docentes()
        elif seccion == "reportes":
            self._mostrar_reportes()

    # ──────────────────────────────────────────
    # SECCIÓN: DASHBOARD
    # ──────────────────────────────────────────

    def _mostrar_dashboard(self):
        frame = ctk.CTkFrame(self.content, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self._frame_activo = frame

        # Título
        ctk.CTkLabel(frame, text="Dashboard",
                     font=ctk.CTkFont(size=26, weight="bold")).grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, 4))

        hoy = date.today()
        ctk.CTkLabel(frame,
                     text=f"Semana actual  •  {(hoy - timedelta(days=hoy.weekday())).strftime('%d/%m/%Y')} – {hoy.strftime('%d/%m/%Y')}",
                     font=ctk.CTkFont(size=12),
                     text_color="gray60").grid(
            row=1, column=0, columnspan=4, sticky="w", pady=(0, 20))

        # Tarjetas de métricas (se cargan en hilo)
        self._tarjetas_frame = ctk.CTkFrame(frame, fg_color="transparent")
        self._tarjetas_frame.grid(row=2, column=0, columnspan=4, sticky="ew")
        self._tarjetas_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkLabel(self._tarjetas_frame, text="Cargando métricas...",
                     text_color="gray60").grid(row=0, column=0, columnspan=4)

        # Tabla reciente
        ctk.CTkLabel(frame, text="Últimos registros de esta semana",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=3, column=0, columnspan=4, sticky="w", pady=(24, 8))

        self._tabla_frame = ctk.CTkScrollableFrame(frame, height=300, corner_radius=12)
        self._tabla_frame.grid(row=4, column=0, columnspan=4, sticky="ew")

        # Cargar datos en hilo
        inicio_semana = (hoy - timedelta(days=hoy.weekday())).strftime("%Y-%m-%d")
        fin_semana    = hoy.strftime("%Y-%m-%d")

        WorkerThread(
            tarea=obtener_resumen_rapido,
            args=(inicio_semana, fin_semana),
            callback=lambda res, error: self.after(0, self._actualizar_tarjetas, res, error)
        ).start()

        WorkerThread(
            tarea=procesar_asistencia,
            args=(inicio_semana, fin_semana),
            callback=lambda res, error: self.after(0, self._actualizar_tabla, res, error)
        ).start()

    def _actualizar_tarjetas(self, resumen: dict, error):
        if error or not resumen:
            return
        for w in self._tarjetas_frame.winfo_children():
            w.destroy()

        metricas = [
            ("Total registros", resumen["total_registros"], "#58a6ff", "📋"),
            ("Puntuales",       resumen["puntuales"],       "#3fb950", "✅"),
            ("Tardanzas",       resumen["tardanzas"],       "#d29922", "⚠️"),
            ("Faltas",          resumen["faltas"],          "#f85149", "❌"),
        ]
        for col, (titulo, valor, color, icono) in enumerate(metricas):
            card = ctk.CTkFrame(self._tarjetas_frame, corner_radius=12)
            card.grid(row=0, column=col, padx=8, pady=4, sticky="ew")
            ctk.CTkLabel(card, text=icono, font=ctk.CTkFont(size=28)).pack(pady=(16, 4))
            ctk.CTkLabel(card, text=str(valor),
                         font=ctk.CTkFont(size=32, weight="bold"),
                         text_color=color).pack()
            ctk.CTkLabel(card, text=titulo,
                         font=ctk.CTkFont(size=12),
                         text_color="gray60").pack(pady=(2, 16))

    def _actualizar_tabla(self, resultado, error):
        if error or not resultado:
            return
        _, df_b = resultado
        if df_b is None or df_b.empty:
            return

        for w in self._tabla_frame.winfo_children():
            w.destroy()

        cols = ["Nombre", "Fecha", "Estado", "Min_Tardanza_Día"]
        col_widths = [200, 100, 100, 150]

        # Encabezados
        for j, (col, ancho) in enumerate(zip(cols, col_widths)):
            ctk.CTkLabel(
                self._tabla_frame, text=col,
                font=ctk.CTkFont(weight="bold"), width=ancho,
                fg_color=("gray80", "gray25"), corner_radius=6
            ).grid(row=0, column=j, padx=2, pady=2, sticky="ew")

        COLORES_ESTADO = {
            "Puntual":  ("#d4edda", "#1a3c26"),
            "Tardanza": ("#fff3cd", "#3d2c00"),
            "Falta":    ("#f8d7da", "#3d0008"),
        }

        for i, (_, row) in enumerate(df_b.tail(30).iterrows(), start=1):
            estado = str(row.get("Estado", ""))
            col_par = COLORES_ESTADO.get(estado, ("gray85", "gray20"))
            for j, col in enumerate(cols):
                ctk.CTkLabel(
                    self._tabla_frame,
                    text=str(row.get(col, "—")),
                    width=col_widths[j],
                    fg_color=col_par,
                    corner_radius=4,
                ).grid(row=i, column=j, padx=2, pady=1, sticky="ew")

    # ──────────────────────────────────────────
    # SECCIÓN: DOCENTES
    # ──────────────────────────────────────────

    def _mostrar_docentes(self):
        frame = ctk.CTkFrame(self.content, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        self._frame_activo = frame

        ctk.CTkLabel(frame, text="Gestión de Docentes",
                     font=ctk.CTkFont(size=26, weight="bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 16))

        form = FormPersonal(frame)
        form.grid(row=1, column=0, sticky="nsew")

    # ──────────────────────────────────────────
    # SECCIÓN: REPORTES
    # ──────────────────────────────────────────

    def _mostrar_reportes(self):
        frame = ctk.CTkFrame(self.content, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        frame.grid_columnconfigure(0, weight=1)
        self._frame_activo = frame

        ctk.CTkLabel(frame, text="Generación de Reportes",
                     font=ctk.CTkFont(size=26, weight="bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 4))

        ctk.CTkLabel(frame, text="Exporta los reportes Excel con datos de asistencia procesados.",
                     text_color="gray60").grid(row=1, column=0, sticky="w", pady=(0, 24))

        # Selector de rango de fechas
        card = ctk.CTkFrame(frame, corner_radius=12)
        card.grid(row=2, column=0, sticky="ew", pady=8)
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(card, text="⚙️ Configuración del Reporte",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=20, pady=(16, 8))

        hoy = date.today()
        primer_dia_mes = hoy.replace(day=1)

        ctk.CTkLabel(card, text="Fecha inicio (YYYY-MM-DD):").grid(
            row=1, column=0, padx=20, pady=8, sticky="w")
        self.entry_inicio = ctk.CTkEntry(card, width=160)
        self.entry_inicio.insert(0, primer_dia_mes.strftime("%Y-%m-%d"))
        self.entry_inicio.grid(row=1, column=1, padx=8, pady=8, sticky="w")

        ctk.CTkLabel(card, text="Fecha fin (YYYY-MM-DD):").grid(
            row=2, column=0, padx=20, pady=8, sticky="w")
        self.entry_fin = ctk.CTkEntry(card, width=160)
        self.entry_fin.insert(0, hoy.strftime("%Y-%m-%d"))
        self.entry_fin.grid(row=2, column=1, padx=8, pady=8, sticky="w")

        ctk.CTkLabel(card, text="Carpeta de salida:").grid(
            row=3, column=0, padx=20, pady=8, sticky="w")
        self.entry_carpeta = ctk.CTkEntry(card, width=260, placeholder_text="./reportes")
        self.entry_carpeta.insert(0, "./reportes")
        self.entry_carpeta.grid(row=3, column=1, padx=8, pady=8, sticky="w")

        ctk.CTkButton(
            card, text="📥 Generar Reportes Excel",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=44, command=self._generar_reportes
        ).grid(row=4, column=0, columnspan=3, padx=20, pady=(8, 20), sticky="ew")

        # Log de salida
        ctk.CTkLabel(frame, text="Log de ejecución",
                     font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=3, column=0, sticky="w", pady=(20, 4))

        self.log_box = ctk.CTkTextbox(frame, height=180, corner_radius=10,
                                      font=ctk.CTkFont(family="Consolas", size=12))
        self.log_box.grid(row=4, column=0, sticky="ew")
        self.log_box.configure(state="disabled")

    def _log(self, mensaje: str):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"{mensaje}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _generar_reportes(self):
        inicio  = self.entry_inicio.get().strip()
        fin     = self.entry_fin.get().strip()
        carpeta = self.entry_carpeta.get().strip() or "./reportes"

        self._log(f"[{date.today()}] Iniciando procesamiento {inicio} → {fin}...")

        def tarea():
            df_a, df_b = procesar_asistencia(inicio, fin)
            rutas = generar_reportes(df_a, df_b, carpeta)
            return rutas

        def al_terminar(resultado, error):
            if error:
                self.after(0, self._log, f"[ERROR] {error}")
                self.after(0, messagebox.showerror, "Error", error)
            else:
                ruta_a, ruta_b = resultado
                self.after(0, self._log, f"[OK] Reporte A: {ruta_a}")
                self.after(0, self._log, f"[OK] Reporte B: {ruta_b}")
                self.after(0, self._log, "✅ Reportes generados exitosamente.")
                self.after(0, messagebox.showinfo, "Éxito", "Reportes generados en:\n" + carpeta)

        WorkerThread(tarea=tarea, callback=al_terminar).start()
