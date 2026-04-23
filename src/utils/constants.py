# Translation dictionary for room names and labels
_STATIC_TRANSLATIONS = {
    "Living Room": "Sala de Estar",
    "Master Bedroom": "Quarto Principal",
    "Bedroom": "Quarto",
    "Bathroom": "Banheiro",
    "Master Bathroom": "Banheiro Principal",
    "Kitchen": "Cozinha",
    "Dining Room": "Sala de Jantar",
    "Garage": "Garagem",
    "Built Area": "Área Construída",
    "Total Area": "Área Total",
    "Bedrooms": "Quartos",
    "Bathrooms": "Banheiros",
    "Style": "Estilo",
    "Traditional": "Tradicional",
    "Modern": "Moderno",
    "Compact": "Compacto",
    "AI-Generated House Plan": "Planta de Casa Gerada por IA",
    "Front of House": "Frente da Casa",
    "Back of House": "Fundo da Casa",
    "Lateral of House": "Laterais da Casa",
    "Hall": "Hall",
    "Corridor": "Corredor",
}


def translate(name: str) -> str:
    """Translate a room name, handling dynamic numbered variants like 'Bedroom 4'."""
    if name in _STATIC_TRANSLATIONS:
        return _STATIC_TRANSLATIONS[name]
    for prefix, pt in (("Bedroom ", "Quarto "), ("Bathroom ", "Banheiro ")):
        if name.startswith(prefix):
            return pt + name[len(prefix):]
    return name


class _TranslationsProxy(dict):
    """Dict-like proxy that translates unknown keys dynamically."""
    def get(self, key, default=None):
        return translate(key) if key else default

    def __getitem__(self, key):
        return translate(key)


TRANSLATIONS = _TranslationsProxy(_STATIC_TRANSLATIONS)

# SVG style definitions
SVG_STYLES = """
    .wall { fill: none; stroke: #333; stroke-width: 3; }
    .room-fill { fill: #f0f0f0; stroke: #333; stroke-width: 1; }
    .door { fill: none; stroke: #8B4513; stroke-width: 2; }
    .door-arc { fill: none; stroke: #8B4513; stroke-width: 2; }
    .door-opening { fill: none; stroke: #999; stroke-width: 0.5; }
    .window { fill: #87CEEB; stroke: #333; stroke-width: 1; }
    .room-label { font-family: Arial; font-size: 12px; text-anchor: middle; fill: #333; }
    .specs { font-family: Arial; font-size: 10px; fill: #666; }
    .terrain { fill: none; stroke: #000; stroke-width: 2; stroke-dasharray: 10,5; }
    .front-line { fill: none; stroke: #0066cc; stroke-width: 2; stroke-dasharray: 5,5; }
    .legend { font-family: Arial; font-size: 10px; fill: #0066cc; }
""" 