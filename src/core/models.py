from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional

@dataclass
class Door:
    x: float
    y: float
    width: float
    height: float
    is_horizontal: bool

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
    def area(self) -> float:
        return self.width * self.height

@dataclass
class HouseSpecs:
    terrain_width: float  # in meters
    terrain_height: float  # in meters
    num_bedrooms: int
    num_bathrooms: int
    has_dining_room: bool = False
    has_garage: bool = False
    style: str = "modern"
    
    # Constants for building regulations
    TAXA_OCUPACAO = 0.7  # 70% of terrain area
    RECUO_FRONTAL = 5.0  # 5 meters front setback
    
    @property
    def total_area(self) -> float:
        return self.terrain_width * self.terrain_height
    
    @property
    def built_area(self) -> float:
        return self.total_area * self.TAXA_OCUPACAO
    
    @property
    def has_living_room(self) -> bool:
        return True  # Always include living room
    
    @property
    def has_kitchen(self) -> bool:
        return True  # Always include kitchen

    @classmethod
    def get_dimensions(cls) -> Tuple[float, float]:
        """Get fixed door dimensions"""
        return 3.0, 7.0  # Fixed width and height