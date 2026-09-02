# SistemaPOS

Punto de venta e inventario de escritorio para tiendas pequeñas. Aplicación
Windows en Python (CustomTkinter) con base de datos PostgreSQL local e
impresión de recibos en impresora térmica ESC/POS por USB.

Es la base del producto POS de Inti Nova.

## Qué hace hoy

- Ventas: catálogo por categorías y más vendidos, búsqueda en vivo, lector
  de código de barras, carrito con cambio de cantidades, descuentos por línea
  o por venta (con permiso), cobro en efectivo con botones de billetes,
  teclado numérico y cambio en vivo, tarjeta, transferencia o pago mixto, y
  ventana de resumen. El recibo se imprime solo si el cajero activa
  "Imprimir recibo" antes de cobrar; el cajón monedero se abre al cobrar en
  efectivo si está configurado. Cola de ventas para atender varios clientes a
  la vez: cada venta abierta conserva sus productos y su monto recibido hasta
  que se retoma, y sobrevive a un cierre del programa.
- Cierre de caja por turno: no se vende sin turno abierto; el turno arranca
  con una base, el cierre cuenta el efectivo por denominación, muestra la
  diferencia, imprime el cierre y guarda el historial.
- Inventario: indicadores de valor y existencias, búsqueda y filtro por
  categoría, filas resaltadas con pocas existencias o agotadas según el stock
  mínimo de cada producto, importación y exportación en Excel.
- Gestión de productos: buscar, crear, modificar y dar de baja, IVA por
  producto (0, 5 o 19 %), stock mínimo, ajustes de existencias con motivo y
  kárdex de movimientos.
- Compras a proveedores: alta de proveedores, registro de la factura con sus
  productos; las unidades entran al inventario y el costo se actualiza con
  promedio ponderado.
- Reporte de ventas por rango de fechas con atajos (hoy, ayer, semana, mes),
  totales por método de pago, devoluciones, anulación de ventas y
  devoluciones parciales con motivo, y exportación a Excel.
- Dashboard de ventas por período pensado para tomar decisiones: hallazgos
  escritos en frases, comparación con el período anterior, horas pico, días
  de la semana, evolución diaria, métodos de pago, productos más vendidos y
  más rentables, ventas por categoría, reposición urgente con los días que
  faltan para agotarse y mercancía sin movimiento con el costo inmovilizado.
- Auditoría de todo lo que cambia, con el usuario y el detalle antes y
  después. Las filas salen en verde (crear, entradas de existencias), rojo
  (eliminar, salidas, anulaciones, devoluciones) y amarillo (modificaciones);
  las ventas y los turnos quedan en blanco.
- Inicio de sesión y usuarios con roles: administrador (todo), supervisor
  (vende, descuentos, anulaciones, inventario, compras, reportes) y cajero
  (vende, consulta y gestiona inventario, compras, cierre de caja). Cada
  recibo guarda quién atendió.
- Copias de seguridad: pg_dump automático al primer arranque de cada día,
  copia manual, restauración desde la pantalla y retención de las 30 copias
  más recientes en la carpeta `backups`.
- Asistente de primer arranque: la primera vez pide los datos del negocio, la
  conexión a PostgreSQL (crea la base si no existe), la impresora y la clave
  del administrador, y escribe `.env` y `config.json`.

La paleta, las fuentes y los componentes compartidos viven en `view/theme.py`
y `view/widgets.py`; cualquier cambio visual global se hace ahí.

## Requisitos

- Windows 10 u 11.
- Python 3.11 o superior (desarrollo).
- PostgreSQL 14 o superior instalado en el equipo. Las copias de seguridad
  usan pg_dump y pg_restore de la carpeta bin de PostgreSQL; la aplicación
  los busca sola en Program Files.
- Impresora térmica USB compatible con ESC/POS (opcional; se puede desactivar).

## Configuración

Dos archivos junto al ejecutable (o en la raíz del proyecto en desarrollo).
Ninguno se sube al repositorio. La primera vez que se abre la aplicación, el
asistente de configuración los escribe; también se pueden editar a mano:

1. `.env`: credenciales de PostgreSQL (`DB_HOST`, `DB_PORT`, `DB_NAME`,
   `DB_USER`, `DB_PASSWORD`) y la clave del primer administrador
   (`ADMIN_PASSWORD`). Al arrancar, la aplicación crea el usuario `admin` con
   esa clave si no hay usuarios; después se administran desde la pantalla
   Usuarios.
2. `config.json`: datos del negocio que salen en el recibo (`business`, con
   `logo` opcional apuntando a un PNG o JPG), parámetros de la impresora
   (`printer`, con `open_drawer` para el cajón monedero) y copias de seguridad
   (`backup`: `enabled`, `directory`, `keep`, `pg_bin`).

Para identificar la impresora: `python scripts/find_usb.py` muestra los IDs
USB; `python scripts/list_endpoints.py` muestra los endpoints; y
`python scripts/test_printer.py` imprime un recibo de prueba.

Las tablas se crean y actualizan solas al iniciar, con las migraciones de la
carpeta `migrations/`.

Para probar o capacitar con datos realistas, `python scripts/seed_demo.py`
carga 100 productos de ejemplo en 11 categorías. Se puede repetir sin
duplicar nada.

Para cargar el catálogo de un cliente: en Inventario, "Exportar Excel" genera
el archivo con el formato y una hoja de instrucciones; se completa y se carga
con "Importar Excel". Si hay un solo error, no se importa nada y se muestra
la lista de filas a corregir.

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
se crea y elimina una base temporal en cada ejecución; una de ellas hace una
copia con pg_dump y la restaura con pg_restore.

## Empaquetado e instalador

```bash
pyinstaller SistemaPOS.spec
```

El ejecutable queda en `dist/SistemaPOS.exe`. Al primer arranque abre el
asistente de configuración. `libusb-1.0.dll` viaja dentro del ejecutable.

Para entregar al cliente un instalador de Windows (requiere
[Inno Setup 6](https://jrsoftware.org/isdl.php)):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_installer.ps1
```

Genera `dist/installer/SistemaPOS-Setup-<versión>.exe`, que instala en
`C:\SistemaPOS` con permisos de escritura para todos los usuarios (la
aplicación guarda ahí `.env`, `config.json`, `logs` y `backups`), crea el
acceso directo y abre la aplicación al terminar. Desinstalar no borra los
datos del cliente. La versión sale de `utils/version.py`.

## Estructura

```
run.py                  punto de entrada (abre el asistente si falta configuración)
controller/             lógica de cada pantalla
view/                   interfaz (CustomTkinter); view/theme.py centraliza colores y fuentes
model/                  entidades, permisos, errores de negocio; model/db/ acceso a datos por módulo
migrations/             cambios de esquema en SQL, numerados
utils/                  configuración, asistente inicial, copias, Excel, impresora, lector de códigos
scripts/                seed de demostración, diagnóstico de la impresora, build del instalador
installer/              guion de Inno Setup
tests/                  pruebas con pytest
```
