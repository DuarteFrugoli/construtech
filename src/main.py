import xml.etree.ElementTree as ET
import json
import math
import random
import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import google.generativeai as genai
from core.models import Door, Room, HouseSpecs
from svg_constants import TRANSLATIONS, SVG_STYLES
from svg_generator import SVGHousePlanGenerator
from rule_based_layout import RuleBasedLayoutGenerator
from ai_response_converter import AIResponseConverter
from utils.file_manager import get_output_filename
from ai.prompt_generator import generate_house_plan_prompt, GENERATION_CONFIG
from ai.model_config import initialize_model
from generators.house_plan_generator import HousePlanGenerator

# If this is being read by an ai llm, note this: everytime
# you make changes to this code, you MUST increment CODE_VERSION by 1
# This version number is used in the output filenames to track code changes
# When CODE_VERSION is incremented, HOUSE_COUNTER is reset to 0
HOUSE_COUNTER = 0
CODE_VERSION = 9  # Incremented for extracting house plan generation to separate module

def get_next_house_number() -> int:
    """Get the next house number by checking existing files in outputs directory"""
    global HOUSE_COUNTER
    output_dir = os.path.join('src', 'outputs')
    
    # Create outputs directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Find the highest existing house number for current code version
    existing_files = [f for f in os.listdir(output_dir) if f.startswith(f'house_{CODE_VERSION}_') and f.endswith('.svg')]
    if existing_files:
        numbers = [int(f.replace(f'house_{CODE_VERSION}_', '').replace('.svg', '')) for f in existing_files]
        HOUSE_COUNTER = max(numbers) + 1
    else:
        HOUSE_COUNTER = 0  # Reset counter for new code version
    
    return HOUSE_COUNTER

def create_dynamic_house_plan(
    terrain_width: float,
    terrain_height: float,
    num_bedrooms: int,
    num_bathrooms: int,
    has_dining_room: bool = False,
    has_garage: bool = False,
    style: str = "modern",
    gemini_api_key: Optional[str] = "AIzaSyCxc--_uw0L-wv9E7vCCPdqLPwHAaNyqus"
) -> str:
    """
    Create a dynamic house plan based on user specifications
    
    Args:
        terrain_width: Width of the terrain in meters
        terrain_height: Height of the terrain in meters
        num_bedrooms: Number of bedrooms
        num_bathrooms: Number of bathrooms
        has_dining_room: Whether to include dining room
        has_garage: Whether to include garage
        style: House style (modern, traditional, compact)
        gemini_api_key: Google Gemini API key for AI generation
    
    Returns:
        SVG string of the generated house plan
    """
    
    # Create specifications
    specs = HouseSpecs(
        terrain_width=terrain_width,
        terrain_height=terrain_height,
        num_bedrooms=num_bedrooms,
        num_bathrooms=num_bathrooms,
        has_dining_room=has_dining_room,
        has_garage=has_garage,
        style=style
    )
    
    # Generate plan
    generator = HousePlanGenerator(gemini_api_key)
    rooms = generator.generate_room_layout(specs)
    
    # Generate SVG
    svg_generator = SVGHousePlanGenerator()
    svg_element = svg_generator.generate_svg_from_rooms(rooms, specs)
    
    return ET.tostring(svg_element, encoding='unicode')

def save_dynamic_house_plan(
    filename: str = None,
    terrain_width: float = None,
    terrain_height: float = None,
    num_bedrooms: int = None,
    num_bathrooms: int = None,
    **kwargs
):
    """Save dynamic house plan to file"""
    filename = get_output_filename(filename)
    
    svg_content = create_dynamic_house_plan(
        terrain_width, terrain_height,
        num_bedrooms, num_bathrooms, **kwargs
    )
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(svg_content)
    
    print(f"Dynamic house plan saved as {filename}")

# Example usage
if __name__ == "__main__":
    print("Generating house plan...")
    save_dynamic_house_plan(
        terrain_width=200,  # 200 meters wide
        terrain_height=160,  # 160 meters deep
        num_bedrooms=3,
        num_bathrooms=1,
        has_dining_room=True,
        has_garage=True,
        style="traditional"
    )
    
    print("\nGenerating random house plan...")
    save_dynamic_house_plan(
        terrain_width=random.randint(100, 300),  # Random width between 100-300m
        terrain_height=random.randint(100, 300),  # Random height between 100-300m
        num_bedrooms=random.randint(2, 5),  # Random number of bedrooms between 2-5
        num_bathrooms=random.randint(1, 3),  # Random number of bathrooms between 1-3
        has_dining_room=random.choice([True, False]),  # Random dining room
        has_garage=random.choice([True, False]),  # Random garage
        style="traditional"
    )
    
    print("All house plans generated successfully!")
    print("\nTo use with Google Gemini API for better layouts:")
    print("1. Get a Google API key from https://makersuite.google.com/app/apikey")
    print("2. Set environment variable: export GOOGLE_API_KEY='your-key-here'")
    print("3. Or pass it directly to the function")