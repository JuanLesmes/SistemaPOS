# view/auditlog_view.py
import json
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from tkcalendar import DateEntry
from datetime import date

class AuditLogView(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Configuración de grid para panel fijo sin sash
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=500)

        # ————— Filtro de fecha —————
        filtro = ctk.CTkFrame(self, fg_color="#ececec")
        filtro.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10,0))
        filtro.grid_columnconfigure(1, weight=1)

        self.date_picker = DateEntry(
            filtro, date_pattern="yyyy-MM-dd",
            background="white", foreground="black", borderwidth=1
        )
        self.date_picker.grid(row=0, column=0, padx=(0,5), pady=5)

        ctk.CTkButton(
            filtro, text="Cargar Logs", width=120,
            command=self._on_click_load
        ).grid(row=0, column=1, sticky="w", pady=5)

        ctk.CTkButton(
            filtro,
            text="Volver al Menú",
            fg_color="#f7b267",         
            hover_color="#c7853a",      
            text_color="black",          
            command=self.controller.event_back,
            font=("Segoe UI", 12),      
            corner_radius=8             
        ).grid(row=0, column=2, sticky="e", padx=(10, 5), pady=5)


        # ----- Panel izquierdo: resumen -----
        frame_left = ttk.Frame(self)
        frame_left.grid(row=1, column=0, sticky="nsew", padx=(10,5), pady=10)

        cols = ("timestamp","action","code")
        self.tree = ttk.Treeview(
            frame_left, columns=cols, show="headings", selectmode="browse", height=20
        )
        for c in cols:
            self.tree.heading(c, text=c.capitalize())
            self.tree.column(c, width=120, stretch=False)

        vsb = ttk.Scrollbar(frame_left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        frame_left.grid_rowconfigure(0, weight=1)
        frame_left.grid_columnconfigure(0, weight=1)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # ----- Panel derecho: detalles antes/después -----
        frame_right = ttk.Frame(self)
        frame_right.grid(row=1, column=1, sticky="nsew", padx=(5,10), pady=10)
        frame_right.grid_rowconfigure(1, weight=1)
        frame_right.grid_columnconfigure(0, weight=1)

        lbl = ctk.CTkLabel(
            frame_right,
            text="Modificaciones (Antes → Después):",
            font=("Segoe UI", 12, "bold")
        )
        lbl.grid(row=0, column=0, sticky="w", padx=5, pady=(0,5))

        # Definimos la tabla de detalles
        detail_cols = ("field", "before", "after")
        self.details_table = ttk.Treeview(
            frame_right, columns=detail_cols, show="headings", height=20
        )
        self.details_table.heading("field", text="Campo")
        self.details_table.heading("before", text="Antes")
        self.details_table.heading("after", text="Después")
        self.details_table.column("field",  width=100, stretch=False)
        self.details_table.column("before", width=200, stretch=True)
        self.details_table.column("after",  width=200, stretch=True)

        vsb2 = ttk.Scrollbar(
            frame_right, orient="vertical", command=self.details_table.yview
        )
        hsb2 = ttk.Scrollbar(
            frame_right, orient="horizontal", command=self.details_table.xview
        )
        self.details_table.configure(
            yscrollcommand=vsb2.set,
            xscrollcommand=hsb2.set
        )

        self.details_table.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0,5))
        vsb2.grid(row=1, column=1, sticky="ns")
        hsb2.grid(row=2, column=0, sticky="ew")

        # Carga inicial
        today = date.today().strftime("%Y-%m-%d")
        self.date_picker.set_date(today)
        self._load_logs_for_date(today)

    def _on_click_load(self):
        date_str = self.date_picker.get_date().strftime("%Y-%m-%d")
        self._load_logs_for_date(date_str)

    def _load_logs_for_date(self, date_str):
        logs = self.controller.db.get_logs_by_date(date_str)
        # Guarda sólo detalles en lista paralela
        self._logs = []
        # Limpia resumen y detalles
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for iid in self.details_table.get_children():
            self.details_table.delete(iid)

        # Llena resumen
        for idx, row in enumerate(logs):
            if isinstance(row, dict):
                ts      = row.get("timestamp")
                action  = row.get("action")
                code    = row.get("code")
                details = row.get("details")
            else:
                ts, action, code, details, *_ = row
            self.tree.insert("", "end", iid=str(idx), values=(ts, action, code))
            self._logs.append(details or "")

        # Auto‑selecciona y muestra la primera fila
        children = self.tree.get_children()
        if children:
            first = children[0]
            self.tree.selection_set(first)
            self._on_select(None)

    def _on_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        raw = self._logs[idx]
        try:
            data = json.loads(raw)
        except Exception:
            data = {"raw": raw}
        before = data.get("before", {})
        after  = data.get("after", {})
        # Limpia tabla de detalles
        for iid in self.details_table.get_children():
            self.details_table.delete(iid)
        # Inserta cada campo
        keys = sorted(set(before) | set(after))
        for key in keys:
            val_before = before.get(key, "")
            val_after  = after.get(key, "")
            self.details_table.insert(
                "", "end",
                values=(key, str(val_before), str(val_after))
            )