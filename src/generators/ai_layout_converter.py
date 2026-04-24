import logging
import math
from typing import Dict, List
from core.models import Room, HouseSpecs
from generators.rule_based_generator import RuleBasedLayoutGenerator

logger = logging.getLogger(__name__)


class AIResponseConverter:
    def __init__(self):
        self.rule_generator = RuleBasedLayoutGenerator()

    def _normalize_room_name(
        self,
        name: str,
        specs: HouseSpecs,
        suite_bathroom_count: int,
        social_bathroom_count: int,
    ) -> tuple[str, int, int]:
        lower_name = name.lower()
        if "bathroom" not in lower_name:
            return name, suite_bathroom_count, social_bathroom_count

        # Only treat as suite bathroom if explicitly named so
        if "suite" in lower_name or "master bathroom" in lower_name:
            normalized = self.rule_generator._suite_bathroom_name(suite_bathroom_count)
            return normalized, suite_bathroom_count + 1, social_bathroom_count

        # Everything else is a social bathroom
        social_bathroom_count += 1
        normalized = f"Bathroom {social_bathroom_count}" if specs.num_social_bathrooms > 1 else "Bathroom"
        return normalized, suite_bathroom_count, social_bathroom_count

    def convert_response_to_rooms(self, layout_data: Dict, specs: HouseSpecs) -> List[Room]:
        """Convert AI response to Room objects"""
        rooms = []
        suite_bathroom_count = 0
        social_bathroom_count = 0

        for room_data in layout_data.get("rooms", []):
            name = room_data.get("name", "Room")
            name, suite_bathroom_count, social_bathroom_count = self._normalize_room_name(
                name,
                specs,
                suite_bathroom_count,
                social_bathroom_count,
            )
            width = room_data.get("width", 0)
            height = room_data.get("height", 0)
            if not width or not height:
                logger.warning(f"Skipping room with missing dimensions: {room_data}")
                continue
            room = Room(name=name, width=float(width), height=float(height), x=0, y=0)
            rooms.append(room)

        if not rooms:
            logger.warning("No valid rooms from AI response. Falling back to rule-based.")
            return self.rule_generator.generate_layout(specs)

        # Safety scale: if the sum of private-zone widths exceeds the usable width,
        # scale ALL rooms down so they can fit side-by-side in the private zone.
        is_portrait = specs.terrain_height >= specs.terrain_width
        usable_w = max(1.0, specs.terrain_width  - specs.recuo_lateral * 2)
        usable_h = max(1.0, specs.terrain_height - specs.recuo_frontal - specs.recuo_fundo)
        width_axis = usable_w if is_portrait else usable_h

        private_rooms = [r for r in rooms
                         if self.rule_generator._get_zone(r.name) in {"bedroom", "bathroom"}]
        private_widths_sum = sum(r.width for r in private_rooms)
        if private_widths_sum > width_axis:
            scale = width_axis / private_widths_sum
            for r in rooms:
                r.width  *= scale
                r.height *= scale
            logger.info(f"AI rooms scaled by {scale:.3f} to fit private zone within {width_axis:.1f}m.")

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