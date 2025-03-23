# add_products.py
from model.db_connection import DBConnection
from model.product import Product

def main():
    db = DBConnection("data/local.db")  # Ajusta el path si difiere

    # Crear un producto
    product1 = Product(
        code="P100",
        name="Peine para Mascotas",
        cost=2.0,
        price=5.0,
        stock=300,
        category="Accesorios",
        description="Peine ergonómico para perros y gatos"
    )

    # Insertarlo en la BD
    db.add_product(product1)
    print("Producto P100 insertado exitosamente.")

    # Puedes crear e insertar más productos aquí
    product2 = Product(
        code="P200",
        name="Snacks de Pollo",
        cost=3.0,
        price=6.0,
        stock=50,
        category="Alimentos",
        description="Deliciosos snacks de pollo para premiar a tu mascota"
    )
    db.add_product(product2)
    print("Producto P200 insertado exitosamente.")

if __name__ == "__main__":
    main()
