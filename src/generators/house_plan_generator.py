"""
House plan generation logic.
"""
import json
import logging
from typing import Optional, List
from core.models import Room, HouseSpecs
from ai.gemini_client import get_model
from ai.prompt_generator import generate_house_plan_prompt, GENERATION_CONFIG
from generators.rule_based_generator import RuleBasedLayoutGenerator
from generators.ai_layout_converter import AIResponseConverter

logger = logging.getLogger(__name__)


class HousePlanGenerator:
    def __init__(self):
        self.use_ai, self.model = get_model()

    def generate_room_layout(self, specs: HouseSpecs) -> List[Room]:
        """Generate room layout using AI or rule-based approach"""
        if not self.use_ai:
            return RuleBasedLayoutGenerator().generate_layout(specs)

        try:
            prompt = generate_house_plan_prompt(specs)
            response = self.model.generate_content(prompt, generation_config=GENERATION_CONFIG)

            if not response or not response.text:
                raise RuntimeError("Empty response from Gemini API")

            ai_response = response.text.strip()
            if ai_response.startswith('```'):
                ai_response = ai_response.split('\n', 1)[1].rsplit('\n', 1)[0].strip()

            try:
                layout_data = json.loads(ai_response)
                converter = AIResponseConverter()
                layout_data = converter.filter_valid_rooms(layout_data, specs)
                return converter.convert_response_to_rooms(layout_data, specs)
            except json.JSONDecodeError as e:
                logger.warning(f"AI response parsing failed: {e}. Falling back to rule-based.")
                return RuleBasedLayoutGenerator().generate_layout(specs)

        except Exception as e:
            logger.warning(f"AI generation failed: {e}. Falling back to rule-based.")
            return RuleBasedLayoutGenerator().generate_layout(specs)
 