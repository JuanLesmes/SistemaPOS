import tkinter as tk
from controller.voucher_view_controller import VoucherViewController
from controller.product_management_view_controller import ProductManagementViewController
from model.db_connection import DBConnection

class MainController:
    def __init__(self, root):
        self.root = root
        self.root.title("InventoryManagement")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Configuración de la base de datos
        try:
            self.db = DBConnection(
                db_name="inventario",
                user="postgres",
                password="x",
                host="localhost",
                port="5432"
            )
        except Exception as e:
            tk.messagebox.showerror("Error de conexión", str(e))
            self.root.destroy()
            return

        # Inicializar vistas y controladores UNA VEZ
        self._initialize_controllers()
        self.show_login_view()

    def _initialize_controllers(self):
        """Inicializa todos los controladores y frames al inicio."""
        from controller.admin_view_controller import AdminViewController
        from controller.product_management_view_controller import ProductManagementViewController
        from controller.sales_view_controller import SalesViewController
        from controller.sales_report_view_controller import SalesReportViewController
        from view.login_view import LoginView

        # Frame de Login
        self.frame_login = tk.Frame(self.root)
        self.login_view = LoginView(self.frame_login, self)

        # Frame de Administración
        self.frame_admin = tk.Frame(self.root)
        self.admin_controller = AdminViewController(self.frame_admin, self, self.db)
        
        # Frame de Productos
        self.frame_product_mgmt = tk.Frame(self.root)
        self.product_mgmt_controller = ProductManagementViewController(
            self.frame_product_mgmt, 
            self, 
            self.db
        )

        # Frame de Ventas (reutilizado)
        self.frame_sales = tk.Frame(self.root)
        self.sales_controller = SalesViewController(self.frame_sales, self, self.db)

        # Frame de Reportes
        self.frame_sales_report = tk.Frame(self.root)
        self.report_controller = SalesReportViewController(self.frame_sales_report, self, self.db)

    def on_close(self):
        """Cierra la aplicación correctamente."""
        self.db.close_connection()
        self.root.destroy()

    # --------------------------
    # Métodos para mostrar vistas
    # --------------------------
    def show_login_view(self):
        self._show_frame(self.frame_login)

    def show_admin_view(self):
        self._show_frame(self.frame_admin)

    def show_product_management_view(self):
        self.hide_all_frames()
        self.frame_product_mgmt.pack(fill="both", expand=True)
        self.product_mgmt_controller.view.set_categories(self.db.get_categories())

    def show_sales_view(self):
        """Muestra el frame de ventas existente."""
        self.hide_all_frames()
        self.frame_sales.pack(fill="both", expand=True)
        self.sales_controller.initialize()
        self.sales_controller.activate_barcode_reader()

    def show_sales_report_view(self):
        self._show_frame(self.frame_sales_report    )

    def show_voucher_view(self, receipt, change_due):
        """Muestra el voucher como ventana emergente (Toplevel)."""
        # No afecta a los frames principales
        VoucherViewController(self.root, self, receipt, change_due)

    def _show_frame(self, frame):
        """Muestra un frame y oculta los demás."""
        self.hide_all_frames()
        frame.pack(fill="both", expand=True)

    def hide_all_frames(self):
        """Oculta todos los frames principales."""
        for widget in self.root.winfo_children():
            if isinstance(widget, tk.Frame):
                widget.pack_forget()
        
    def get_current_voucher_controller(self):
        return self.current_voucher_controller
    
    def refresh_all_categories(self):
        updated_cats = self.db.get_categories()
        self.admin_controller.view.set_categories(["Todas"] + updated_cats)  # <-- admin_controller
        if hasattr(self, "product_mgmt_controller"):
            self.product_mgmt_controller.view.set_categories(updated_cats)