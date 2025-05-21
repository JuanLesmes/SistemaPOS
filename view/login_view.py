import customtkinter as ctk
from PIL import Image
from customtkinter import CTkImage, CTkLabel
import os, sys


class LoginView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        ctk.set_appearance_mode("light")
        self.configure(width=800, height=600, fg_color="#9db7b1")
        self.pack(fill="both", expand=True)

        self.create_widgets()

    def get_resource_path(self, relative_path):
        if getattr(sys, 'frozen', False):
            base = sys._MEIPASS
        else:
            base = os.path.abspath(".")
        return os.path.join(base, relative_path)

    def create_widgets(self):
        azul_turquesa = "#10a2a7"
        marron_cafe   = "#b57426"
        rojo          = "#D32F2F"
        fondo         = "#9db7b1"

        # --- Panel izquierdo ---
        left = ctk.CTkFrame(self, fg_color=azul_turquesa, width=280)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        container = ctk.CTkFrame(left, fg_color=azul_turquesa, corner_radius=0)
        container.place(relx=0.5, rely=0.5, anchor="center")

        # Título
        title = "Bienvenido a\nMenguante\n- Café y Maíz -"
        ctk.CTkLabel(
            container,
            text=title,
            font=("Segoe UI", 24, "bold"),
            text_color="black",
            justify="center"
        ).pack(pady=30)

        # Estilo común botones
        btn_style = {
            "width": 200,
            "height": 50,
            "corner_radius": 15,
            "font": ("Segoe UI", 16, "bold")
        }

        # Ingreso a Ventas
        ctk.CTkButton(
            container,
            text="Ingreso a Ventas",
            fg_color=marron_cafe,
            hover_color="#935d1e",
            text_color="white",
            command=self.controller.show_sales_view,
            **btn_style
        ).pack(pady=10)

        # Control de Inventario
        ctk.CTkButton(
            container,
            text="Control de Inventario",
            fg_color=marron_cafe,
            hover_color="#935d1e",
            text_color="white",
            command=self.controller.show_admin_view,
            **btn_style
        ).pack(pady=10)

        # Reporte de Ventas
        ctk.CTkButton(
            container,
            text="Reporte de Ventas",
            fg_color=marron_cafe,
            hover_color="#935d1e",
            text_color="white",
            command=self.controller.show_sales_report_view,
            **btn_style
        ).pack(pady=10)

        # Botón Salir
        ctk.CTkButton(
            container,
            text="Salir",
            fg_color=rojo,
            hover_color="#b71c1c",
            text_color="white",
            command=self.exit_app,
            **btn_style
        ).pack(pady=10)

        # --- Panel derecho (logo) ---
        right = ctk.CTkFrame(self, fg_color=fondo, corner_radius=0)
        right.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        logo_container = ctk.CTkFrame(right, fg_color=fondo, corner_radius=0)
        logo_container.place(relx=0.5, rely=0.5, anchor="center")

        logo_path = self.get_resource_path("images/logo.png")
        try:
            pil_img = Image.open(logo_path).resize((300, 300), Image.Resampling.LANCZOS)
            ctk_img = CTkImage(light_image=pil_img, size=(300, 300))
            lbl = CTkLabel(logo_container, image=ctk_img, text="", fg_color=fondo)
            lbl.pack()
        except Exception:
            ctk.CTkLabel(
                logo_container,
                text="LOGO",
                font=("Segoe UI", 32, "bold"),
                text_color=azul_turquesa
            ).pack()

    # 👇 Aquí ya está fuera del método create_widgets
    def exit_app(self):
        try:
            self.controller.root.destroy()
        except AttributeError:
            pass
