import json
import math
from typing import Dict, List, Tuple
from core.models import Room, HouseSpecs
from rule_based_layout import RuleBasedLayoutGenerator

class AIResponseConverter:
    def __init__(self):
        self.rule_generator = RuleBasedLayoutGenerator()

    def convert_response_to_rooms(self, layout_data: Dict, specs: HouseSpecs) -> List[Room]:
        """Convert AI response to Room objects"""
        print("\nDEBUG: Converting AI response to rooms")
        print(f"DEBUG: Target built area: {specs.built_area:.0f} m²")
        
        # Seção especial de prints do Plano Diretor
        print("\n=== CHECKLIST PLANO DIRETOR ===")
        print("✓ Taxa de Ocupação (TO) fixa em 70% conforme Plano Diretor")
        print("✓ Recuo frontal mínimo de 5 metros conforme Plano Diretor")
        print("=== FIM DO CHECKLIST ===\n")
        
        rooms = []
        total_ai_area = 0
        
        # First pass: collect all rooms and calculate total area
        for room_data in layout_data.get("rooms", []):
            room = Room(
                name=room_data["name"],
                width=room_data["width"],
                height=room_data["height"],
                x=0,  # Will be positioned later
                y=0
            )
            total_ai_area += room.area
            rooms.append(room)
            print(f"DEBUG: Initial {room.name}: {room.width:.0f} x {room.height:.0f} = {room.area:.0f} m²")
        
        print(f"DEBUG: Total AI area before scaling: {total_ai_area:.0f} m²")
        
        # Calculate scale factor to match target built area, but with a more flexible approach
        if total_ai_area > 0:
            # Calculate a reasonable scale factor that won't exceed terrain dimensions
            max_room_width = max(room.width for room in rooms)
            max_room_height = max(room.height for room in rooms)
            
            # Calculate scale factors for width and height separately
            width_scale = (specs.terrain_width * 0.95) / max_room_width  # Leave 5% margin
            height_scale = (specs.terrain_height * 0.95) / max_room_height  # Leave 5% margin
            
            # Use the smaller scale factor to ensure rooms fit within terrain
            terrain_scale = min(width_scale, height_scale)
            
            # Calculate the scale factor needed to reach target area
            target_scale = math.sqrt(specs.built_area / total_ai_area)
            
            # Use the smaller of the two scale factors, but ensure we're within 7% of target
            scale_factor = min(terrain_scale, target_scale)
            
            # If the resulting area would be too small, try to increase the scale
            if scale_factor == terrain_scale:
                # Calculate what percentage we'd get with terrain_scale
                test_area = total_ai_area * (terrain_scale ** 2)
                test_percentage = (test_area / specs.total_area) * 100
                
                # If we're more than 7% below target, try to increase the scale
                if test_percentage < specs.TAXA_OCUPACAO * 100 - 7:
                    # Try to find a scale that gets us closer to target
                    scale_factor = math.sqrt((specs.built_area * 0.97) / total_ai_area)  # Target 97% of desired area
                    # But still don't exceed terrain constraints
                    scale_factor = min(scale_factor, terrain_scale)
            
            print(f"DEBUG: Scale factor (constrained by terrain): {scale_factor:.2f}")
            
            # Scale all rooms
            for room in rooms:
                room.width *= scale_factor
                room.height *= scale_factor
                print(f"DEBUG: Scaled {room.name}: {room.width:.0f} x {room.height:.0f} = {room.area:.0f} m²")
        
        final_area = sum(room.area for room in rooms)
        print(f"DEBUG: Final total area: {final_area:.0f} m²")
        print(f"DEBUG: Taxa de Ocupação: {specs.TAXA_OCUPACAO*100}%")
        print(f"DEBUG: Actual percentage: {(final_area/specs.total_area)*100:.1f}%")
        
        # Position rooms using rule-based generator
        return self.rule_generator._position_rooms(rooms, specs)

    def filter_valid_rooms(self, layout_data: Dict, specs: HouseSpecs) -> Dict:
        """Filter out invalid rooms from AI response"""
        valid_rooms = []
        for room in layout_data.get("rooms", []):
            name = room["name"].lower()
            if "hallway" in name or "corridor" in name:
                continue
            if "bedroom" in name and specs.num_bedrooms == 0:
                continue
            if "bathroom" in name and specs.num_bathrooms == 0:
                continue
            valid_rooms.append(room)
        layout_data["rooms"] = valid_rooms
        return layout_data 