class SoldProduct:
    def __init__(self, receipt_id, product, quantity):
        self.receipt_id = receipt_id
        self.product = product
        self.quantity = quantity
        self.total_partial = 0.0
        self.calculate_total_partial()

    def calculate_total_partial(self):
        if self.product and self.product.price is not None:
            self.total_partial = self.product.price * self.quantity
        else:
            self.total_partial = 0.0

    def get_code(self):
        return self.product.code

    def get_total_partial(self):
        return self.total_partial
