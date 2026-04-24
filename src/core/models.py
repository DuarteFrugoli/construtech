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
    num_social_bathrooms: int
    num_suites: int = 0
    has_dining_room: bool = False
    has_garage: bool = False
    has_living_room: bool = True
    has_kitchen: bool = True
    style: str = "modern"

    # Cômodos extras opcionais
    has_home_office: bool = False
    has_dependencia: bool = False
    has_varanda: bool = False
    has_lavabo: bool = False
    has_area_gourmet: bool = False
    has_area_servico: bool = False

    # Plano Diretor parameters — default: genérico permissivo
    taxa_ocupacao: float = 0.6       # fração do terreno (e.g. 0.6 = 60%)
    coeficiente_aproveitamento: float = 2.0  # área total / área do terreno
    recuo_frontal: float = 3.0       # metros
    recuo_lateral: float = 1.5       # metros
    recuo_fundo: float = 1.5         # metros
    num_pavimentos: int = 2          # gabarito máximo
    taxa_permeabilidade: float = 0.15  # fração mínima permeável (e.g. 0.15 = 15%)

    def __post_init__(self):
        if self.num_social_bathrooms < 0:
            raise ValueError("num_social_bathrooms must be non-negative")
        if self.num_suites < 0:
            raise ValueError("num_suites must be non-negative")
        if self.num_suites > self.num_bedrooms:
            raise ValueError("num_suites cannot exceed num_bedrooms")

    @property
    def total_area(self) -> float:
        return self.terrain_width * self.terrain_height

    @property
    def built_area(self) -> float:
        return self.total_area * self.taxa_ocupacao

    @property
    def num_bathrooms(self) -> int:
        return self.num_social_bathrooms + self.num_suites
