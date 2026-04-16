"""
ui/forms_personnel.py
Formulario para registrar docentes y asignar sus horarios internos.
"""
import customtkinter as ctk
from tkinter import messagebox
from data.db_manager import (
    insertar_personal, obtener_personal, actualizar_personal, eliminar_personal,
    insertar_horario, obtener_horarios, eliminar_horarios
)

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
HORAS = [f"{h:02d}:{m:02d}" for h in range(6, 22) for m in (0, 15, 30, 45)]


class FormPersonal(ctk.CTkFrame):
    """
    Panel izquierdo: lista de docentes + botones CRUD.
    Panel derecho: formulario de datos + horarios.
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(fg_color="transparent")
        self._docente_seleccionado = None
        self._construir_ui()
        self.cargar_lista()

    # ──────────────────────────────────────────
    # CONSTRUCCIÓN DE LA UI
    # ──────────────────────────────────────────

    def _construir_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        # ── Panel izquierdo: Lista ──
        frame_lista = ctk.CTkFrame(self, corner_radius=12)
        frame_lista.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=0)
        frame_lista.grid_rowconfigure(1, weight=1)
        frame_lista.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame_lista, text="👥 Docentes",
                     font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, pady=(16, 8), padx=16, sticky="w")

        self.lista_scroll = ctk.CTkScrollableFrame(frame_lista, label_text="")
        self.lista_scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

        frame_botones_lista = ctk.CTkFrame(frame_lista, fg_color="transparent")
        frame_botones_lista.grid(row=2, column=0, pady=8, padx=8, sticky="ew")

        ctk.CTkButton(frame_botones_lista, text="+ Nuevo", width=90,
                      command=self._nuevo_docente).pack(side="left", padx=4)
        ctk.CTkButton(frame_botones_lista, text="🗑 Eliminar", width=90,
                      fg_color="#c0392b", hover_color="#96281b",
                      command=self._eliminar_docente).pack(side="right", padx=4)

        # ── Panel derecho: Formulario ──
        frame_form = ctk.CTkScrollableFrame(self, corner_radius=12)
        frame_form.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        frame_form.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame_form, text="📋 Datos del Docente",
                     font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, columnspan=2, pady=(16, 12), padx=16, sticky="w")

        # Campos básicos
        self._entries = {}
        campos = [
            ("ID Biométrico", "id_bio"),
            ("Nombre completo", "nombre"),
            ("Departamento / Área", "departamento"),
        ]
        for i, (label, key) in enumerate(campos, start=1):
            ctk.CTkLabel(frame_form, text=label).grid(
                row=i, column=0, sticky="w", padx=16, pady=6)
            entry = ctk.CTkEntry(frame_form, placeholder_text=label)
            entry.grid(row=i, column=1, sticky="ew", padx=16, pady=6)
            self._entries[key] = entry

        # ── Horarios por día ──
        ctk.CTkLabel(frame_form, text="🕐 Horarios (Lunes–Viernes)",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=len(campos) + 1, column=0, columnspan=2,
            pady=(20, 8), padx=16, sticky="w")

        self._horarios_widgets = []
        for i, dia in enumerate(DIAS):
            fila_base = len(campos) + 2 + i
            ctk.CTkLabel(frame_form, text=dia, width=90).grid(
                row=fila_base, column=0, padx=16, pady=4, sticky="w")

            frame_h = ctk.CTkFrame(frame_form, fg_color="transparent")
            frame_h.grid(row=fila_base, column=1, padx=16, pady=4, sticky="ew")

            ctk.CTkLabel(frame_h, text="Entrada:").pack(side="left", padx=(0, 4))
            cb_entrada = ctk.CTkComboBox(frame_h, values=HORAS, width=90)
            cb_entrada.set("07:30")
            cb_entrada.pack(side="left", padx=4)

            ctk.CTkLabel(frame_h, text="Salida:").pack(side="left", padx=(8, 4))
            cb_salida = ctk.CTkComboBox(frame_h, values=HORAS, width=90)
            cb_salida.set("13:00")
            cb_salida.pack(side="left", padx=4)

            ctk.CTkLabel(frame_h, text="Tolerancia (min):").pack(side="left", padx=(8, 4))
            spin_tol = ctk.CTkEntry(frame_h, width=50)
            spin_tol.insert(0, "5")
            spin_tol.pack(side="left", padx=4)

            self._horarios_widgets.append((cb_entrada, cb_salida, spin_tol))

        # Botón guardar
        fila_btn = len(campos) + 2 + len(DIAS) + 1
        ctk.CTkButton(frame_form, text="💾 Guardar Docente",
                      font=ctk.CTkFont(size=13, weight="bold"),
                      height=40, command=self._guardar_docente).grid(
            row=fila_btn, column=0, columnspan=2,
            pady=(20, 16), padx=16, sticky="ew")

    # ──────────────────────────────────────────
    # LÓGICA DE LISTA
    # ──────────────────────────────────────────

    def cargar_lista(self):
        for widget in self.lista_scroll.winfo_children():
            widget.destroy()

        docentes = obtener_personal()
        for doc in docentes:
            btn = ctk.CTkButton(
                self.lista_scroll,
                text=f"  {doc['nombre']}\n  ID: {doc['id_biometrico']}",
                anchor="w",
                font=ctk.CTkFont(size=12),
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray80", "gray30"),
                command=lambda d=doc: self._seleccionar_docente(d)
            )
            btn.pack(fill="x", pady=2, padx=4)

    def _seleccionar_docente(self, doc: dict):
        self._docente_seleccionado = doc
        self._entries["id_bio"].configure(state="normal")
        self._entries["id_bio"].delete(0, "end")
        self._entries["id_bio"].insert(0, doc["id_biometrico"])
        self._entries["id_bio"].configure(state="disabled")  # No editar la PK

        self._entries["nombre"].delete(0, "end")
        self._entries["nombre"].insert(0, doc["nombre"])

        self._entries["departamento"].delete(0, "end")
        self._entries["departamento"].insert(0, doc["departamento"])

        # Cargar horarios
        horarios = obtener_horarios(doc["id_biometrico"])
        horarios_dict = {h["dia_semana"]: h for h in horarios}
        for i, (cb_e, cb_s, spin_t) in enumerate(self._horarios_widgets):
            if i in horarios_dict:
                h = horarios_dict[i]
                cb_e.set(h["hora_entrada"])
                cb_s.set(h["hora_salida"])
                spin_t.delete(0, "end")
                spin_t.insert(0, str(h["tolerancia_minutos"]))

    def _nuevo_docente(self):
        self._docente_seleccionado = None
        for key, entry in self._entries.items():
            entry.configure(state="normal")
            entry.delete(0, "end")
        for cb_e, cb_s, spin_t in self._horarios_widgets:
            cb_e.set("07:30")
            cb_s.set("13:00")
            spin_t.delete(0, "end")
            spin_t.insert(0, "5")

    # ──────────────────────────────────────────
    # OPERACIONES CRUD
    # ──────────────────────────────────────────

    def _guardar_docente(self):
        id_bio     = self._entries["id_bio"].get().strip()
        nombre     = self._entries["nombre"].get().strip()
        depto      = self._entries["departamento"].get().strip()

        if not all([id_bio, nombre, depto]):
            messagebox.showwarning("Campos vacíos", "Completa todos los campos obligatorios.")
            return

        if self._docente_seleccionado:
            actualizar_personal(id_bio, nombre, depto)
        else:
            ok = insertar_personal(id_bio, nombre, depto)
            if not ok:
                messagebox.showerror("Duplicado", f"El ID biométrico '{id_bio}' ya existe.")
                return

        # Guardar horarios
        eliminar_horarios(id_bio)
        for i, (cb_e, cb_s, spin_t) in enumerate(self._horarios_widgets):
            entrada = cb_e.get()
            salida  = cb_s.get()
            try:
                tol = int(spin_t.get())
            except ValueError:
                tol = 5
            insertar_horario(id_bio, i, entrada, salida, tol)

        messagebox.showinfo("Éxito", f"Docente '{nombre}' guardado correctamente.")
        self.cargar_lista()

    def _eliminar_docente(self):
        if not self._docente_seleccionado:
            messagebox.showwarning("Selección", "Selecciona un docente de la lista primero.")
            return
        nombre = self._docente_seleccionado["nombre"]
        confirmar = messagebox.askyesno(
            "Confirmar eliminación",
            f"¿Desactivar a '{nombre}'?\nSu historial se conservará."
        )
        if confirmar:
            eliminar_personal(self._docente_seleccionado["id_biometrico"])
            self._nuevo_docente()
            self.cargar_lista()
