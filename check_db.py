# check_db.py

from model.db_connection import DBConnection

def main():
    db = DBConnection("data/local.db")

    print("Categorías en la BD:")
    categories = db.get_categories()
    print(categories)

    print("\nProductos (stock > 0):")
    products = db.get_products()
    for p in products:
        print(f"Code={p.code}, Name={p.name}, Stock={p.stock}, Category={p.category}")

if __name__ == "__main__":
    main()
