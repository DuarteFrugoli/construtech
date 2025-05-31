"""
House plan generation logic.
"""
import json
from typing import Optional, List
from core.models import Room, HouseSpecs
from ai.model_config import initialize_model
from ai.prompt_generator import generate_house_plan_prompt, GENERATION_CONFIG
from rule_based_layout import RuleBasedLayoutGenerator
from ai_response_converter import AIResponseConverter

class HousePlanGenerator:
    def __init__(self, gemini_api_key: Optional[str] = None):
        """
        Initialize the House Plan Generator
        
        Args:
            gemini_api_key: Google Gemini API key. If None, will try to get from environment
        """
        self.use_ai, self.model = initialize_model(gemini_api_key)
    
    def generate_room_layout(self, specs: HouseSpecs) -> List[Room]:
        """Generate room layout using AI or rule-based approach"""
        if not self.use_ai:
            rule_generator = RuleBasedLayoutGenerator()
            return rule_generator.generate_layout(specs)
            
        try:
            prompt = generate_house_plan_prompt(specs)
            
            response = self.model.generate_content(
                prompt,
                generation_config=GENERATION_CONFIG
            )
            
            if not response or not response.text:
                raise Exception("Empty response from Gemini API")
                
            ai_response = response.text.strip()
            
            # Clean up the response - remove markdown formatting if present
            if ai_response.startswith('```'):
                # Remove markdown code block markers and language specifier
                ai_response = ai_response.split('\n', 1)[1]  # Remove first line
                ai_response = ai_response.rsplit('\n', 1)[0]  # Remove last line
                ai_response = ai_response.strip()
            
            # Parse AI response
            try:
                layout_data = json.loads(ai_response)
                # Filter and convert response to rooms
                converter = AIResponseConverter()
                layout_data = converter.filter_valid_rooms(layout_data, specs)
                return converter.convert_response_to_rooms(layout_data, specs)
            except json.JSONDecodeError as e:
                print(f"AI response parsing failed: {e}")
                print("Response was:", ai_response)
                rule_generator = RuleBasedLayoutGenerator()
                return rule_generator.generate_layout(specs)
                
        except Exception as e:
            print(f"AI generation failed: {e}, using rule-based generation")
            rule_generator = RuleBasedLayoutGenerator()
            return rule_generator.generate_layout(specs) 