"""
House plan generation logic.
"""
from typing import List
from core.models import Room, HouseSpecs
from generators.rule_based_generator import RuleBasedLayoutGenerator


class HousePlanGenerator:
    def generate_room_layout(self, specs: HouseSpecs) -> List[Room]:
        """Generate room layout using the rule-based approach."""
        return RuleBasedLayoutGenerator().generate_layout(specs)
 