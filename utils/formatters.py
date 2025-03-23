# utils/formatters.py

def format_price(price, decimals=0):
    """
    Formatea un número para que se muestre con separador de miles.
    Por defecto, sin decimales. Si decimals > 0, muestra esa cantidad de decimales.
    Devuelve un string en el que el separador de miles es el punto y, en caso de decimales,
    el separador decimal es la coma.
    
    Ejemplos:
        format_price(1000000, decimals=0) -> "1.000.000"
        format_price(1000000.75, decimals=2) -> "1.000.000,75"
    """
    if decimals == 0:
        return f"{price:,.0f}".replace(",", ".")
    else:
        # Primero formatea con el separador de miles y decimales según el formato en inglés:
        formatted = f"{price:,.{decimals}f}"
        # Luego se intercambian: las comas de miles por un carácter temporal, el punto decimal por coma y
        # finalmente el carácter temporal por punto.
        return formatted.replace(",", "X").replace(".", ",").replace("X", ".")
