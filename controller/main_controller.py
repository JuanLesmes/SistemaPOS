# controller/main_controller.py
import tkinter as tk
from controller.voucher_view_controller import VoucherViewController
from model.db_connection import DBConnection  # <-- para BD

class MainController:
    def __init__(self, root):
        self.root = root
        self.root.title("InventoryManagement")

        # Creamos la instancia de la BD
        self.db = DBConnection("data/local.db")

        from view.login_view import LoginView
        from view.admin_view import AdminView
        from view.product_management_view import ProductManagementView
        from view.sales_report_view import SalesReportView
        from view.voucher_view import VoucherView

        # LoginView
        self.frame_login = tk.Frame(self.root)
        self.login_view = LoginView(self.frame_login, self)

        # AdminView
        self.frame_admin = tk.Frame(self.root)
        from controller.admin_view_controller import AdminViewController
        self.admin_view_controller = AdminViewController(self.frame_admin, self, self.db)

        # ProductManagementView
        self.frame_product_mgmt = tk.Frame(self.root)
        from controller.product_management_view_controller import ProductManagementViewController
        self.product_mgmt_controller = ProductManagementViewController(self.frame_product_mgmt, self, self.db)


        # SalesView + Controller
        self.frame_sales = tk.Frame(self.root)
        from controller.sales_view_controller import SalesViewController
        self.sales_view_controller = SalesViewController(self.frame_sales, self, self.db)
        # NOTA: Esto internamente crea "sales_view_controller.view"

        # SalesReportView
        self.frame_sales_report = tk.Frame(self.root)
        from controller.sales_report_view_controller import SalesReportViewController
        self.sales_report_controller = SalesReportViewController(self.frame_sales_report, self, self.db)
        
        # Mostramos la vista principal
        self.show_login_view()

    def show_login_view(self):
        self.hide_all_frames()
        self.frame_login.pack(fill="both", expand=True)

    def show_admin_view(self):
        self.hide_all_frames()
        self.frame_admin.pack(fill="both", expand=True)

    def show_product_management_view(self):
        self.hide_all_frames()
        self.frame_product_mgmt.pack(fill="both", expand=True)

    def show_sales_view(self):
        self.hide_all_frames()
        self.frame_sales.pack(fill="both", expand=True)
        # Aqui ya se está mostrando la vista con la lógica unida

    def show_sales_report_view(self):
        self.hide_all_frames()
        self.frame_sales_report.pack(fill="both", expand=True)



    def show_voucher_view(self, receipt, change_due):
        # Aquí es donde mostramos el Recibo SÓLO cuando lo necesitamos.
        from controller.voucher_view_controller import VoucherViewController
        self.voucher_controller = VoucherViewController(self.root, self)
        print("Creando voucher_view_controller en el init de MainController")


        # Llenar la data
        # (puedes crear la lista de productos, fecha/hora, etc.)
        productos_list = []
        for sp in receipt.sold_products:
            productos_list.append((sp.quantity, sp.product.name, sp.total_partial))

        fecha_str = receipt.date.strftime("%d/%m/%Y")
        hora_str = receipt.time.strftime("%H:%M")

        # Recibo ID con ceros a la izquierda
        voucher_id = str(receipt.id).zfill(10)

        self.voucher_controller.load_data(
            receipt_id=voucher_id,
            fecha_emision=fecha_str,
            hora_emision=hora_str,
            productos=productos_list,
            total=receipt.total_sale,
            vueltas=change_due
        )

    def load_data(self, receipt, change_due):
        self.view.load_receipt_data(receipt, change_due)


    def hide_all_frames(self):
        for widget in self.root.winfo_children():
            widget.pack_forget()
