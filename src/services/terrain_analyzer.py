"""
Terrain analysis module for house plan generation.
"""
import requests
import math
from typing import Tuple, List, Dict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NOMINATIM_HEADERS = {"User-Agent": "Construtech/1.0 (house plan generator)"}

class TerrainAnalyzer:
    def __init__(self):
        pass

    def get_coordinates(self, address: str) -> Tuple[float, float]:
        """Get geographical coordinates from address using Nominatim (OpenStreetMap)."""
        try:
            response = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": address, "format": "json", "limit": 1},
                headers=NOMINATIM_HEADERS,
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            if not data:
                raise ValueError(f"Endereço não encontrado: {address}")

            return float(data[0]["lat"]), float(data[0]["lon"])

        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting coordinates: {e}")
            raise RuntimeError("Erro ao buscar coordenadas. Verifique o endereço informado.")

    def get_elevations(self, points: List[Tuple[float, float]]) -> List[float]:
        """Get elevation data for points using Open-Elevation API."""
        try:
            locations = [{"latitude": lat, "longitude": lng} for lat, lng in points]

            response = requests.post(
                "https://api.open-elevation.com/api/v1/lookup",
                json={"locations": locations},
                timeout=20,
            )
            response.raise_for_status()
            data = response.json()

            return [result["elevation"] for result in data["results"]]

        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting elevations: {e}")
            raise RuntimeError("Erro ao buscar dados de elevação.")

    def analyze_terrain(self, address: str) -> Dict:
        """
        Analyze terrain characteristics for a given address.
        Returns elevation data, slope information, and other relevant metrics.
        """
        try:
            # Get coordinates
            lat, lng = self.get_coordinates(address)
            
            # Create a grid of points around the location (5x5 grid)
            points = []
            for i in range(-2, 3):
                for j in range(-2, 3):
                    # Approximate 10 meters in degrees (roughly)
                    points.append((lat + i*0.0001, lng + j*0.0001))
            
            # Get elevations for all points
            elevations = self.get_elevations(points)
            
            # Calculate metrics
            min_elevation = min(elevations)
            max_elevation = max(elevations)
            height_diff = max_elevation - min_elevation
            
            # Calculate slope inclinations
            slopes = []
            for i in range(len(points)-1):
                for j in range(i+1, len(points)):
                    lat1, lng1 = points[i]
                    lat2, lng2 = points[j]
                    elev1 = elevations[i]
                    elev2 = elevations[j]
                    
                    # Calculate horizontal distance (approximate)
                    horizontal_dist = math.sqrt((lat2-lat1)**2 + (lng2-lng1)**2) * 111000  # Convert to meters
                    if horizontal_dist > 0:
                        slope = abs(elev2 - elev1) / horizontal_dist
                        slopes.append(slope)
            
            avg_slope = sum(slopes) / len(slopes) if slopes else 0
            max_slope = max(slopes) if slopes else 0
            
            return {
                "address": address,
                "coordinates": {"lat": lat, "lng": lng},
                "elevation": {
                    "min": min_elevation,
                    "max": max_elevation,
                    "difference": height_diff
                },
                "slope": {
                    "average": avg_slope,
                    "maximum": max_slope,
                    "average_percentage": avg_slope * 100,
                    "maximum_percentage": max_slope * 100
                },
                "warnings": self._generate_warnings(avg_slope, max_slope, height_diff)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing terrain: {str(e)}")
            raise RuntimeError(str(e))

    def _generate_warnings(self, avg_slope: float, max_slope: float, height_diff: float) -> List[str]:
        """Generate warnings based on terrain characteristics."""
        warnings = []
        
        if max_slope >= 0.35:  # 35% slope
            warnings.append("Terreno com declividade superior a 35% - Área não edificável")
        elif max_slope >= 0.30:  # 30% slope
            warnings.append("Terreno com declividade superior a 30% - Requer laudo técnico")
            
        if height_diff > 5:  # More than 5 meters height difference
            warnings.append("Grande variação de altura no terreno - Pode requerer estudo geotécnico")
            
        return warnings 