# utils/formatters.py

def format_price(price, decimals=0):
    """
    Formatea números o strings numéricos al formato COP.
    """
    # Si es string, quitar puntos y comas, luego convertir a float
    if isinstance(price, str):
        # Eliminar todos los caracteres no numéricos excepto dígitos y comas/puntos decimales
        clean_price = price.replace(".", "").replace(",", ".")
        try:
            price = float(clean_price)
        except ValueError:
            return "0"  # O manejar el error como prefieras
    
    if decimals == 0:
        return f"{price:,.0f}".replace(",", ".")
    else:
        formatted = f"{price:,.{decimals}f}"
        return formatted.replace(",", "X").replace(".", ",").replace("X", ".")
