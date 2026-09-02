# SistemaPOS

Punto de venta e inventario de escritorio para tiendas pequeñas. Aplicación
Windows en Python (CustomTkinter) con base de datos PostgreSQL local e
impresión de recibos en impresora térmica ESC/POS por USB.

Es la base del producto POS de Inti Nova.

## Qué hace hoy

- Ventas con lector de código de barras, cobro en efectivo, tarjeta o
  transferencia y ventana de resumen. El recibo se imprime solo si el cajero
  activa "Imprimir recibo" antes de cobrar.
- Inventario: productos, categorías, existencias, valorización.
- Reporte de ventas por rango de fechas con exportación a Excel.
- Auditoría de cambios del catálogo.

## Requisitos

- Windows 10 u 11.
- Python 3.11 o superior (desarrollo).
- PostgreSQL 14 o superior con una base de datos creada (por defecto `inventario`).
- Impresora térmica USB compatible con ESC/POS (opcional; se puede desactivar).

## Configuración

Dos archivos junto al ejecutable (o en la raíz del proyecto en desarrollo).
Ninguno se sube al repositorio.

1. `.env`: copiar desde `.env.example` y escribir la clave de PostgreSQL
   (`DB_PASSWORD`) y la clave temporal de administración (`ADMIN_PASSWORD`).
2. `config.json`: copiar desde `config.example.json` y ajustar los datos del
   negocio que salen en el recibo y los parámetros de la impresora.

Para identificar la impresora: `python scripts/find_usb.py` muestra los IDs
USB; `python scripts/list_endpoints.py` muestra los endpoints; y
`python scripts/test_printer.py` imprime un recibo de prueba.

Las tablas se crean y actualizan solas al iniciar, con las migraciones de la
carpeta `migrations/`.

## Desarrollo

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements-dev.txt
python run.py
```

Calidad de código y pruebas:

```bash
ruff check .
ruff format .
pytest
```

Las pruebas de base de datos se saltan a menos que existan las variables
`TEST_DB_HOST`, `TEST_DB_PORT`, `TEST_DB_USER` y `TEST_DB_PASSWORD`. Con ellas
se crea y elimina una base temporal en cada ejecución.

## Empaquetado

```bash
pyinstaller SistemaPOS.spec
```

El ejecutable queda en `dist/SistemaPOS.exe`. Al primer arranque copia junto a
él las plantillas `.env.example` y `config.example.json`; hay que renombrarlas
y completarlas antes de volver a abrirlo. `libusb-1.0.dll` viaja dentro del
ejecutable.

## Estructura

```
run.py                  punto de entrada
controller/             lógica de cada pantalla
view/                   interfaz (CustomTkinter); view/theme.py centraliza colores y fuentes
model/                  acceso a datos, entidades, errores de negocio y migraciones
migrations/             cambios de esquema en SQL, numerados
utils/                  configuración, rutas, logging, impresora, lector de códigos
scripts/                herramientas de diagnóstico de la impresora
tests/                  pruebas con pytest
```
