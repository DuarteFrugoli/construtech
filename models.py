from dataclasses import dataclass
from typing import List, Dict, Tuple

@dataclass
class Door:
    x: float
    y: float
    width: float = 3.0  # Fixed door width in feet
    height: float = 7.0  # Fixed door height in feet
    is_horizontal: bool = False  # Whether the door is on a horizontal wall

    @classmethod
    def get_dimensions(cls) -> Tuple[float, float]:
        """Get fixed door dimensions"""
        return 3.0, 7.0  # Fixed width and height

@dataclass
class Room:
    name: str
    width: float
    height: float
    x: float
    y: float
    required: bool = True
    min_area: float = 0
    doors: List[Door] = None
    windows: List[Dict] = None
    
    def __post_init__(self):
        if self.doors is None:
            self.doors = []
        if self.windows is None:
            self.windows = []
    
    @property
    def area(self):
        return self.width * self.height

@dataclass
class HouseSpecs:
    terrain_width: float  # Terrain width in feet
    terrain_height: float  # Terrain height in feet
    num_bedrooms: int
    num_bathrooms: int
    has_kitchen: bool = False  # Changed to False by default
    has_living_room: bool = False  # Changed to False by default
    has_dining_room: bool = False
    has_garage: bool = False
    style: str = "modern"  # modern, traditional, compact
    
    # Taxa de Ocupação fixa conforme Plano Diretor
    TAXA_OCUPACAO: float = 0.70  # 70% fixo
    
    # Recuo frontal conforme Plano Diretor
    RECUO_FRONTAL: float = 16.4  # 5 metros em pés
    
    @property
    def total_area(self) -> float:
        """Calculate total terrain area in sq ft"""
        return self.terrain_width * self.terrain_height
    
    @property
    def built_area(self) -> float:
        """Calculate built area based on Taxa de Ocupação fixa"""
        return self.total_area * self.TAXA_OCUPACAO 