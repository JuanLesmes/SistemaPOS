class Product:
    def __init__(self, code, name, cost, price, stock, category, description):
        self.code = code
        self.name = name
        self.cost = cost
        self.price = price
        self.stock = stock
        self.category = category
        self.description = description

    def __str__(self):
        return f"{self.code} | {self.name} | {self.category} | Stock: {self.stock} | Precio: ${self.price}"