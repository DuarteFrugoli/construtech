import math
import logging
from typing import Dict, List
from core.models import Room, HouseSpecs
from generators.rule_based_generator import RuleBasedLayoutGenerator

logger = logging.getLogger(__name__)


class AIResponseConverter:
    def __init__(self):
        self.rule_generator = RuleBasedLayoutGenerator()

    def convert_response_to_rooms(self, layout_data: Dict, specs: HouseSpecs) -> List[Room]:
        """Convert AI response to Room objects"""
        rooms = []
        total_ai_area = 0

        for room_data in layout_data.get("rooms", []):
            name = room_data.get("name", "Room")
            width = room_data.get("width", 0)
            height = room_data.get("height", 0)
            if not width or not height:
                logger.warning(f"Skipping room with missing dimensions: {room_data}")
                continue
            room = Room(name=name, width=float(width), height=float(height), x=0, y=0)
            total_ai_area += room.area
            rooms.append(room)

        if not rooms:
            logger.warning("No valid rooms from AI response. Falling back to rule-based.")
            return self.rule_generator.generate_layout(specs)

        if total_ai_area > 0:
            max_room_width = max(room.width for room in rooms)
            max_room_height = max(room.height for room in rooms)

            width_scale = (specs.terrain_width * 0.95) / max_room_width
            height_scale = (specs.terrain_height * 0.95) / max_room_height
            terrain_scale = min(width_scale, height_scale)

            target_scale = math.sqrt(specs.built_area / total_ai_area)
            scale_factor = min(terrain_scale, target_scale)

            if scale_factor == terrain_scale:
                test_area = total_ai_area * (terrain_scale ** 2)
                test_percentage = (test_area / specs.total_area) * 100
                if test_percentage < specs.taxa_ocupacao * 100 - 7:
                    scale_factor = min(
                        math.sqrt((specs.built_area * 0.97) / total_ai_area),
                        terrain_scale
                    )

            for room in rooms:
                room.width *= scale_factor
                room.height *= scale_factor

        return self.rule_generator._position_rooms(rooms, specs)

    def filter_valid_rooms(self, layout_data: Dict, specs: HouseSpecs) -> Dict:
        """Filter out invalid rooms from AI response"""
        valid_rooms = []
        for room in layout_data.get("rooms", []):
            name = room.get("name", "").lower()
            if "hallway" in name or "corridor" in name:
                continue
            if "bedroom" in name and specs.num_bedrooms == 0:
                continue
            if "bathroom" in name and specs.num_bathrooms == 0:
                continue
            valid_rooms.append(room)
        layout_data["rooms"] = valid_rooms
        return layout_data

        return layout_data 