# initialize_db.py

from model.db_connection import DBConnection
from model.product import Product

def main():
    # 1. Crear/abrir la conexión a la base de datos
    db = DBConnection("data/local.db")

    # 2. Agregar categorías de ejemplo (solo si no existen)
    sample_cats = ["Alimentos", "Juguetes", "Accesorios"]
    existing_cats = db.get_categories()
    for cat in sample_cats:
        if cat not in existing_cats:
            db.add_category(cat)
            print(f"Categoría insertada: {cat}")

    # 3. Agregar productos de ejemplo
    if not db.get_product("P001"):
        product1 = Product(
            code="P001",
            name="Croquetas para Perros",
            cost=10.0,
            price=15.0,
            stock=100,
            category="Alimentos",
            description="Paquete de croquetas premium."
        )
        db.add_product(product1)
        print("Producto P001 insertado.")

    if not db.get_product("P002"):
        product2 = Product(
            code="P002",
            name="Pelota de Goma",
            cost=2.5,
            price=5.0,
            stock=20,
            category="Juguetes",
            description="Pelota resistente para morder."
        )
        db.add_product(product2)
        print("Producto P002 insertado.")

    if not db.get_product("P003"):
        product3 = Product(
            code="P003",
            name="Rascador para Gatos",
            cost=8.0,
            price=15.0,
            stock=10,
            category="Accesorios",
            description="Rascador vertical con base estable."
        )
        db.add_product(product3)
        print("Producto P003 insertado.")

    print("¡Base de datos inicializada con datos de ejemplo!")

if __name__ == "__main__":
    main()
