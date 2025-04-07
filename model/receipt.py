class Receipt:
    def __init__(self, id=0, total=0.0, date=None, time=None, payment_method="Cash"):
        self.id = id
        self.total = total
        self.date = date
        self.time = time
        self.payment_method = payment_method
        self.sold_products = []