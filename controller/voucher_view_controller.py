# controller/voucher_view_controller.py

import tkinter as tk

class VoucherViewController:
    def __init__(self, parent, main_controller):
        self.parent = parent
        self.main_controller = main_controller

        from view.voucher_view import VoucherView
        self.view = VoucherView(self.parent, self)

        # PROBLEMA: Estás volviendo a crear el mismo controlador recursivamente
        # self.voucher_controller = VoucherViewController(self.root, self)
        # ↑ Esto hay que eliminarlo.

    def load_data(self, receipt_id, fecha_emision, hora_emision, productos, total, vueltas):
        self.view.load_receipt_data(
            receipt_id,
            fecha_emision,
            hora_emision,
            productos,
            total,
            vueltas
        )

    def event_go_back_to_sales(self):
        # Cierra la ventana Toplevel del voucher
        self.view.destroy()
        # Regresa a la vista de ventas
        self.main_controller.show_sales_view()
