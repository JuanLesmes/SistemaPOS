"""Carga 100 productos de ejemplo de una tienda de barrio en la base configurada.

Sirve para probar y capacitar con datos realistas: varias categorías, códigos
de barras EAN-13 y códigos internos alfanuméricos (frutas, pan, huevos),
presentaciones por unidad, paquete, kilo, litro y gramo, productos agotados y
con pocas existencias.

Uso, desde la raíz del proyecto con el entorno virtual activo:

    python scripts/seed_demo.py

Es seguro repetirlo: los códigos que ya existen se saltan.
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from model.db_connection import DBConnection  # noqa: E402
from model.errors import AppError, DuplicateProductError  # noqa: E402
from model.product import Product  # noqa: E402
from utils.config import load_settings  # noqa: E402

BEBIDAS = "Bebidas"
LACTEOS = "Lácteos y huevos"
ABARROTES = "Granos y abarrotes"
ASEO_HOGAR = "Aseo del hogar"
ASEO_PERSONAL = "Aseo personal"
SNACKS = "Snacks y dulces"
PANADERIA = "Panadería"
CARNES = "Carnes frías"
FRUVER = "Frutas y verduras"
LICORES = "Licores y cigarrillos"
VARIOS = "Papelería y varios"

# (código, nombre, categoría, costo, precio, existencias, descripción)
PRODUCTS: list[tuple[str, str, str, int, int, int, str]] = [
    # ---------------------------------------------------------------- bebidas
    ("7702004003508", "Coca-Cola 1.5 L", BEBIDAS, 3200, 4500, 24, "Botella PET 1.5 litros"),
    ("7702004001351", "Coca-Cola 400 ml", BEBIDAS, 1500, 2200, 36, "Botella personal 400 ml"),
    ("7702004002211", "Gaseosa Postobón Manzana 1.5 L", BEBIDAS, 2900, 4000, 18, "Botella PET 1.5 litros"),
    ("7702004008909", "Gaseosa Colombiana 350 ml", BEBIDAS, 1300, 2000, 40, "Lata 350 ml"),
    ("7702090011203", "Agua Cristal 600 ml", BEBIDAS, 900, 1500, 48, "Botella 600 ml"),
    ("7702090011654", "Agua Cristal 5 L", BEBIDAS, 4200, 6000, 6, "Garrafa 5 litros"),
    ("7702354001126", "Jugo Hit Mora 500 ml", BEBIDAS, 1700, 2500, 20, "Botella 500 ml"),
    ("7702354009845", "Jugo Hit Mango 1 L", BEBIDAS, 2800, 4000, 10, "Caja Tetra Pak 1 litro"),
    ("7702001012345", "Pony Malta 330 ml", BEBIDAS, 1600, 2300, 30, "Botella 330 ml"),
    ("7702001040110", "Cerveza Águila 330 ml", BEBIDAS, 2100, 3000, 60, "Botella 330 ml, venta a mayores de edad"),
    ("7702001045566", "Cerveza Poker 330 ml", BEBIDAS, 2100, 3000, 0, "Botella 330 ml, agotada en este momento"),
    ("7702001098765", "Vive 100 Original 240 ml", BEBIDAS, 1800, 2800, 15, "Bebida energizante 240 ml"),
    ("7891991010115", "Red Bull 250 ml", BEBIDAS, 5200, 7500, 8, "Lata 250 ml"),
    # ---------------------------------------------------------------- lácteos y huevos
    ("7702001121111", "Leche Alpina entera 1 L", LACTEOS, 3600, 4600, 20, "Caja 1 litro"),
    ("7702001121128", "Leche Alpina deslactosada 1 L", LACTEOS, 4200, 5300, 12, "Caja 1 litro"),
    ("7702001122224", "Leche Colanta bolsa 1 L", LACTEOS, 3200, 4100, 25, "Bolsa 1 litro"),
    ("7702001133335", "Yogur Alpina fresa 200 g", LACTEOS, 1900, 2700, 14, "Vaso 200 gramos"),
    ("7702001144446", "Queso campesino Colanta 500 g", LACTEOS, 9800, 13500, 5, "Bloque 500 gramos"),
    ("7702001155557", "Mantequilla Alpina 250 g", LACTEOS, 6800, 9200, 3, "Barra 250 gramos, quedan pocas"),
    ("7702001155564", "Arequipe Alpina 250 g", LACTEOS, 4300, 6000, 8, "Vaso 250 gramos"),
    ("HUEVO-30", "Huevos AA cubeta x 30", LACTEOS, 15500, 19000, 12, "Cubeta de 30 unidades, sin código de barras"),
    ("HUEVO-01", "Huevo AA unidad", LACTEOS, 520, 700, 90, "Se vende por unidad"),
    # ---------------------------------------------------------------- granos y abarrotes
    ("7702029001019", "Arroz Diana 500 g", ABARROTES, 1900, 2600, 40, "Bolsa 500 gramos"),
    ("7702029001026", "Arroz Diana 1 kg", ABARROTES, 3700, 4900, 30, "Bolsa 1 kilo"),
    ("7702029001033", "Arroz Diana 5 kg", ABARROTES, 17500, 22500, 6, "Bulto pequeño 5 kilos"),
    ("7702029002023", "Fríjol cargamanto 500 g", ABARROTES, 5200, 7000, 15, "Bolsa 500 gramos"),
    ("7702029002030", "Lenteja 500 g", ABARROTES, 2900, 4000, 20, "Bolsa 500 gramos"),
    ("7702029003037", "Azúcar Manuelita 1 kg", ABARROTES, 3900, 5200, 25, "Bolsa 1 kilo"),
    ("7702029004041", "Panela El Trapiche 1 kg", ABARROTES, 3600, 4800, 18, "Paquete 1 kilo, 2 unidades"),
    ("7702029005058", "Sal Refisal 500 g", ABARROTES, 1100, 1700, 30, "Bolsa 500 gramos"),
    ("7702029006065", "Aceite Premier 1 L", ABARROTES, 8500, 11000, 14, "Botella 1 litro"),
    ("7702029006072", "Aceite Premier 3 L", ABARROTES, 24000, 30500, 4, "Garrafa 3 litros"),
    ("7702029007079", "Harina de maíz Doñarepa 1 kg", ABARROTES, 3800, 5100, 22, "Bolsa 1 kilo"),
    ("7702029007086", "Harina de trigo Haz de Oros 1 kg", ABARROTES, 3100, 4300, 16, "Bolsa 1 kilo"),
    ("7702029008083", "Pasta Doria espagueti 500 g", ABARROTES, 2400, 3400, 28, "Paquete 500 gramos"),
    ("7702029009090", "Café Sello Rojo 250 g", ABARROTES, 8900, 11800, 12, "Bolsa 250 gramos"),
    ("7702029009106", "Chocolate Corona 500 g", ABARROTES, 7600, 9900, 10, "Caja 500 gramos, 16 pastillas"),
    ("7702029010102", "Avena Quaker 400 g", ABARROTES, 4600, 6200, 9, "Bolsa 400 gramos"),
    ("7702029011119", "Atún Van Camps 170 g", ABARROTES, 4800, 6500, 24, "Lata 170 gramos en aceite"),
    ("7702029012126", "Salsa de tomate Fruco 200 g", ABARROTES, 2300, 3200, 15, "Doypack 200 gramos"),
    ("7702029013133", "Mayonesa Fruco 190 g", ABARROTES, 3400, 4600, 11, "Doypack 190 gramos"),
    # ---------------------------------------------------------------- aseo del hogar
    ("7702191001011", "Jabón Rey 300 g", ASEO_HOGAR, 1800, 2600, 30, "Barra 300 gramos"),
    ("7702191002028", "Detergente Fab 1 kg", ASEO_HOGAR, 7900, 10500, 12, "Bolsa 1 kilo"),
    ("7702191002035", "Detergente Fab 500 g", ASEO_HOGAR, 4200, 5800, 18, "Bolsa 500 gramos"),
    ("7702191003042", "Blanqueador Clorox 1 L", ASEO_HOGAR, 3300, 4600, 14, "Botella 1 litro"),
    ("7702191004059", "Límpido Patojito 2 L", ASEO_HOGAR, 3900, 5400, 9, "Garrafa 2 litros"),
    ("7702191005066", "Lavaplatos Axion 450 g", ASEO_HOGAR, 4100, 5600, 16, "Crema 450 gramos"),
    ("7702191006073", "Esponja Bon Bril x 3", ASEO_HOGAR, 2600, 3700, 20, "Paquete de 3 unidades"),
    ("7702191007080", "Papel higiénico Familia x 4", ASEO_HOGAR, 5900, 7900, 22, "Paquete de 4 rollos"),
    ("7702191007097", "Papel higiénico Familia x 12", ASEO_HOGAR, 15800, 20500, 7, "Paquete de 12 rollos"),
    ("7702191008094", "Servilletas Familia x 100", ASEO_HOGAR, 2700, 3800, 13, "Paquete de 100 servilletas"),
    ("7702191009101", "Bolsas de basura negras x 10", ASEO_HOGAR, 2200, 3200, 25, "Paquete de 10 bolsas"),
    ("7702191010117", "Fósforos El Rey x 10", ASEO_HOGAR, 1500, 2300, 2, "Paquete de 10 cajas, quedan pocos"),
    # ---------------------------------------------------------------- aseo personal
    ("7702010001010", "Jabón Protex 110 g", ASEO_PERSONAL, 2400, 3400, 24, "Barra 110 gramos"),
    ("7702010002027", "Shampoo Sedal 350 ml", ASEO_PERSONAL, 9800, 12900, 8, "Frasco 350 ml"),
    ("7702010002034", "Shampoo Head & Shoulders sachet 18 ml", ASEO_PERSONAL, 700, 1200, 60, "Sobre 18 ml"),
    ("7702010003034", "Crema dental Colgate 75 ml", ASEO_PERSONAL, 4300, 5900, 18, "Tubo 75 ml"),
    ("7702010004041", "Cepillo de dientes Oral-B", ASEO_PERSONAL, 3900, 5500, 12, "Unidad"),
    ("7702010005058", "Desodorante Rexona 50 ml", ASEO_PERSONAL, 8200, 11000, 10, "Roll-on 50 ml"),
    ("7702010006065", "Toallas Nosotras x 10", ASEO_PERSONAL, 5100, 7000, 15, "Paquete de 10 unidades"),
    ("7702010007072", "Pañales Winny etapa 3 x 30", ASEO_PERSONAL, 34000, 43000, 4, "Paquete de 30 pañales"),
    ("7702010008089", "Máquina de afeitar Gillette x 2", ASEO_PERSONAL, 4600, 6500, 9, "Paquete de 2 unidades"),
    ("7702010009096", "Crema Nivea 100 ml", ASEO_PERSONAL, 7700, 10500, 6, "Lata 100 ml"),
    # ---------------------------------------------------------------- snacks y dulces
    ("7702025001018", "Papas Margarita natural 105 g", SNACKS, 3200, 4500, 30, "Bolsa familiar 105 gramos"),
    ("7702025001025", "Papas Margarita pollo 25 g", SNACKS, 900, 1500, 50, "Bolsa personal 25 gramos"),
    ("7702025002022", "De Todito 165 g", SNACKS, 5200, 7000, 12, "Bolsa 165 gramos"),
    ("7702025003039", "Chocorramo 65 g", SNACKS, 1900, 2700, 40, "Unidad 65 gramos"),
    ("7702025004046", "Ponqué Gala 45 g", SNACKS, 1300, 2000, 35, "Unidad 45 gramos"),
    ("7702025005053", "Galletas Festival x 4 tacos", SNACKS, 3800, 5200, 16, "Paquete de 4 tacos"),
    ("7702025006060", "Galletas Saltín Noel x 3 tacos", SNACKS, 4100, 5600, 14, "Paquete de 3 tacos"),
    ("7702025007077", "Chocolatina Jet 12 g", SNACKS, 500, 900, 120, "Unidad 12 gramos"),
    ("7702025008084", "Bon Bon Bum x 24", SNACKS, 7800, 10500, 6, "Bolsa de 24 unidades"),
    ("7702025009091", "Chicles Trident x 6", SNACKS, 1400, 2200, 30, "Paquete de 6 unidades"),
    ("7702025010107", "Maní La Especial 50 g", SNACKS, 1600, 2400, 25, "Bolsa 50 gramos"),
    ("7702025012121", "Paleta Crem Helado", SNACKS, 1800, 2800, 15, "Unidad, refrigerada"),
    ("7702025013138", "Wafer Bianchi 40 g", SNACKS, 800, 1300, 0, "Unidad 40 gramos, agotado"),
    # ---------------------------------------------------------------- panadería
    ("7702035001017", "Pan tajado Bimbo 450 g", PANADERIA, 4600, 6200, 8, "Bolsa 450 gramos"),
    ("7702035002024", "Pandebono x 5", PANADERIA, 3000, 4500, 10, "Paquete de 5 unidades"),
    ("7702035003031", "Tostadas Bimbo 100 g", PANADERIA, 2900, 4100, 12, "Paquete 100 gramos"),
    ("PAN-001", "Pan francés unidad", PANADERIA, 300, 500, 60, "Se vende por unidad, sin código de barras"),
    ("PAN-002", "Almojábana unidad", PANADERIA, 900, 1500, 18, "Se vende por unidad, sin código de barras"),
    # ---------------------------------------------------------------- carnes frías
    ("7702042001016", "Salchicha Zenú 460 g", CARNES, 8900, 11800, 6, "Paquete 460 gramos, refrigerado"),
    ("7702042002023", "Salchichón cervecero Zenú 250 g", CARNES, 5600, 7500, 9, "Paquete 250 gramos, refrigerado"),
    ("7702042003030", "Jamón Zenú 250 g", CARNES, 7100, 9600, 5, "Paquete 250 gramos, refrigerado"),
    ("7702042004047", "Mortadela Zenú 250 g", CARNES, 4300, 6000, 7, "Paquete 250 gramos, refrigerado"),
    ("7702042005054", "Chorizo santarrosano x 5", CARNES, 9800, 13000, 4, "Paquete de 5 unidades, refrigerado"),
    # ---------------------------------------------------------------- frutas y verduras
    ("FRU-001", "Papa pastusa 1 kg", FRUVER, 2200, 3200, 50, "Se vende por kilo"),
    ("FRU-002", "Tomate chonto 1 kg", FRUVER, 3100, 4500, 30, "Se vende por kilo"),
    ("FRU-003", "Cebolla cabezona 1 kg", FRUVER, 2600, 3800, 25, "Se vende por kilo"),
    ("FRU-004", "Banano unidad", FRUVER, 250, 400, 80, "Se vende por unidad"),
    ("FRU-005", "Aguacate Hass unidad", FRUVER, 1800, 2800, 15, "Se vende por unidad"),
    ("FRU-006", "Limón Tahití 1 kg", FRUVER, 2400, 3500, 20, "Se vende por kilo"),
    # ---------------------------------------------------------------- licores y cigarrillos
    (
        "7702049001015",
        "Aguardiente Antioqueño 375 ml",
        LICORES,
        24000,
        30000,
        6,
        "Media botella 375 ml, mayores de edad",
    ),
    ("7702049002022", "Ron Medellín 375 ml", LICORES, 27000, 34000, 3, "Media botella 375 ml, quedan pocas"),
    ("7702049003039", "Cigarrillos Marlboro x 20", LICORES, 9000, 11500, 10, "Cajetilla de 20 unidades"),
    ("7702049003046", "Cigarrillo Marlboro unidad", LICORES, 450, 700, 200, "Se vende por unidad"),
    # ---------------------------------------------------------------- papelería y varios
    ("7702056001014", "Cuaderno cosido Norma 100 hojas", VARIOS, 3200, 4600, 12, "Unidad, 100 hojas cuadriculadas"),
    ("7702056003038", "Pilas Duracell AA x 2", VARIOS, 6200, 8500, 10, "Blíster de 2 pilas"),
    ("7702056004045", "Bombillo LED 9 W", VARIOS, 5800, 8000, 8, "Unidad, luz blanca"),
    ("REC-5000", "Recarga celular $5.000", VARIOS, 4800, 5000, 30, "Cualquier operador, se vende por unidad"),
]


def main() -> int:
    codes = [row[0] for row in PRODUCTS]
    assert len(codes) == len(set(codes)), "Hay códigos repetidos en la lista de ejemplo"

    try:
        settings = load_settings()
        db = DBConnection(settings.database)
    except AppError as exc:
        print(f"Error: {exc}")
        return 1

    created = skipped = 0
    try:
        for code, name, category, cost, price, stock, description in PRODUCTS:
            product = Product(
                code=code,
                name=name,
                cost=Decimal(cost),
                price=Decimal(price),
                stock=stock,
                category=category,
                description=description,
            )
            try:
                db.add_product(product)
                created += 1
            except DuplicateProductError:
                skipped += 1
    except AppError as exc:
        print(f"Error cargando '{name}': {exc}")
        return 1
    finally:
        db.close()

    print(f"Productos creados: {created}. Ya existían y se saltaron: {skipped}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
