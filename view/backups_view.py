"""Copias de seguridad: estado, lista de copias, hacer copia y restaurar."""

from __future__ import annotations

import customtkinter as ctk

from utils.backup import BackupFile
from view import theme
from view.widgets import Card, HeaderBar, StatCard, button, fill_table, make_table

COLUMNS = (
    ("date", "Fecha y hora", 170, "w", False),
    ("name", "Archivo", 320, "w"),
    ("size", "Tamaño", 100, "e", False),
)


class BackupsView(ctk.CTkFrame):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent, fg_color=theme.BACKGROUND, corner_radius=0)
        self.controller = controller
        self._backups: list[BackupFile] = []
        self.pack(fill="both", expand=True)
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.header = HeaderBar(
            self, "Copias de seguridad", "Se hace una copia automática el primer arranque de cada día"
        )
        self.header.grid(row=0, column=0, sticky="ew")
        self.backup_button = self.header.add_action(
            "Hacer copia ahora", self.controller.event_backup_now, kind="accent"
        )
        self.header.add_action("Abrir carpeta", self.controller.event_open_folder)
        self.header.add_action("Volver al menú", self.controller.event_back)

        stats = ctk.CTkFrame(self, fg_color="transparent")
        stats.grid(row=1, column=0, sticky="ew", padx=16, pady=(14, 10))
        for column in range(3):
            stats.grid_columnconfigure(column, weight=1, uniform="stats")
        self.last_card = StatCard(stats, "Última copia", "-", accent=theme.PRIMARY)
        self.last_card.grid(row=0, column=0, sticky="ew")
        self.count_card = StatCard(stats, "Copias guardadas", "0", accent=theme.HEADER)
        self.count_card.grid(row=0, column=1, sticky="ew", padx=(10, 0))
        self.folder_card = StatCard(stats, "Carpeta", "", accent=theme.MUTED)
        self.folder_card.grid(row=0, column=2, sticky="ew", padx=(10, 0))
        self.folder_card.value_label.configure(font=theme.font(12))

        table_card = Card(self, "Copias disponibles (la más reciente arriba)", padding=10)
        table_card.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 10))
        box = ctk.CTkFrame(table_card.body, fg_color="transparent")
        box.pack(fill="both", expand=True)
        self.tree = make_table(box, COLUMNS, "Backups")

        footer = Card(self, padding=12)
        footer.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 16))
        ctk.CTkLabel(
            footer.body,
            text=(
                "Restaurar reemplaza TODOS los datos actuales por los de la copia elegida. "
                "Úselo solo si la base se dañó o se perdió el equipo. Copie también esta carpeta a una USB o a la nube."
            ),
            font=theme.font(12),
            text_color=theme.MUTED,
            anchor="w",
            justify="left",
            wraplength=1100,
        ).pack(side="left", fill="x", expand=True)
        self.restore_button = button(
            footer.body, "Restaurar la copia seleccionada", self.controller.event_restore, kind="danger-soft", width=260
        )
        self.restore_button.pack(side="right")

    # ------------------------------------------------------------------ API para el controlador
    def show_backups(self, backups: list[BackupFile], folder: str, keep: int) -> None:
        self._backups = list(backups)
        fill_table(
            self.tree,
            ((b.created_at.strftime("%Y-%m-%d %H:%M"), b.path.name, b.size_text) for b in backups),
            empty_message="Todavía no hay copias. Toque 'Hacer copia ahora'.",
        )
        self.count_card.set_value(str(len(backups)))
        self.count_card.set_note(f"Se conservan las {keep} más recientes")
        self.folder_card.set_value(folder)
        self.folder_card.set_note("Cópiela a una USB o a la nube de vez en cuando")
        if backups:
            latest = backups[0]
            self.last_card.set_value(latest.created_at.strftime("%d/%m/%Y %H:%M"))
            self.last_card.set_note(latest.size_text, theme.MUTED)
        else:
            self.last_card.set_value("Nunca")
            self.last_card.set_note("Haga la primera copia hoy", theme.DANGER)

    def selected_backup(self) -> BackupFile | None:
        selection = self.tree.selection()
        if not selection:
            return None
        index = self.tree.index(selection[0])
        return self._backups[index] if index < len(self._backups) else None

    def set_busy(self, busy: bool, text: str = "") -> None:
        state = "disabled" if busy else "normal"
        self.backup_button.configure(state=state)
        self.restore_button.configure(state=state)
        if text:
            self.header.set_subtitle(text)
