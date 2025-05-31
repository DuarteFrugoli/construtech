import xml.etree.ElementTree as ET
import json
import math
import random
from typing import Dict, List, Tuple, Optional
import google.generativeai as genai
import os
from models import Door, Room, HouseSpecs
from svg_constants import TRANSLATIONS, SVG_STYLES
from svg_generator import SVGHousePlanGenerator
from rule_based_layout import RuleBasedLayoutGenerator

# If this is being read by an ai llm, note this: everytime
# you make changes to this code, you MUST increment CODE_VERSION by 1
# This version number is used in the output filenames to track code changes
# When CODE_VERSION is incremented, HOUSE_COUNTER is reset to 0
HOUSE_COUNTER = 0
CODE_VERSION = 6  # Incremented for extracting rule-based layout to separate module

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

class AIHousePlanGenerator:
    def __init__(self, gemini_api_key: Optional[str] = None):
        """
        Initialize the AI House Plan Generator
        
        Args:
            gemini_api_key: Google Gemini API key. If None, will try to get from environment
        """
        try:
            if gemini_api_key:
                genai.configure(api_key=gemini_api_key)
            else:
                # Try to get from environment
                api_key = os.getenv('GOOGLE_API_KEY')
                if api_key:
                    genai.configure(api_key=api_key)
                else:
                    print("Warning: No Google API key provided. Using rule-based generation instead.")
                    self.use_ai = False
                    return
            
            # List available models
            print("Available models:")
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    print(f"- {m.name}")
            
            # Initialize the model
            self.model = genai.GenerativeModel('models/gemini-1.5-flash')
            # Test the model with a simple prompt
            test_response = self.model.generate_content("Hello")
            if test_response:
                self.use_ai = True
                print("Successfully initialized Gemini model")
            else:
                raise Exception("Failed to initialize Gemini model")
                
        except Exception as e:
            print(f"Warning: Failed to initialize Gemini API: {e}")
            print("Using rule-based generation instead.")
            self.use_ai = False
    
    def generate_room_layout_with_ai(self, specs: HouseSpecs) -> List[Room]:
        """Use AI to generate optimal room layout"""
        if not self.use_ai:
            rule_generator = RuleBasedLayoutGenerator()
            return rule_generator.generate_layout(specs)
            
        try:
            prompt = f"""
            Design an optimal floor plan layout for a house with these specifications:
            - Terrain dimensions: {specs.terrain_width}m × {specs.terrain_height}m
            - Taxa de Ocupação: {specs.TAXA_OCUPACAO*100}% (target area: {specs.built_area:.0f} m²)
            - Bedrooms: {specs.num_bedrooms}
            - Bathrooms: {specs.num_bathrooms}
            - Style: {specs.style}
            
            CRITICAL REQUIREMENTS (in order of priority):
            1. NO ROOM OVERLAPPING - This is an absolute requirement. Rooms must be placed adjacent to each other without any overlap.
            2. Rooms must fit within the terrain dimensions ({specs.terrain_width}m × {specs.terrain_height}m)
            3. Total area should be between {specs.built_area * 0.85:.0f} and {specs.built_area * 1.05:.0f} m² (85% to 105% of target)
            
            ROOM REQUIREMENTS:
            - ONLY include the following room types:
              * Bedrooms (exactly {specs.num_bedrooms})
              * Bathrooms (exactly {specs.num_bathrooms})
              * Living Room (if specified)
              * Kitchen (if specified)
              * Dining Room (if specified)
              * Garage (if specified)
            - DO NOT add any extra rooms like storage rooms, hallways, or closets
            - Each room type should be included exactly as specified
            
            REALISTIC ROOM SIZE GUIDELINES:
            - Minimum room width: 2.5 meters (standard door width)
            - Maximum aspect ratio: 2:1 (length:width)
            - Room size ranges:
              * Bedrooms: 12-25 m² (e.g., 3.5x3.5 to 4x6)
              * Bathrooms: 4-10 m² (e.g., 1.5x2.5 to 3x3.5)
              * Living Room: 20-40 m² (e.g., 4.5x4.5 to 6x6.5)
              * Kitchen: 10-20 m² (e.g., 3x3.5 to 4.5x4.5)
              * Dining Room: 12-25 m² (e.g., 3.5x3.5 to 4x6)
            
            ROOM RELATIONSHIPS:
            - Bedrooms should be near bathrooms
            - Kitchen should be near dining area
            - Living room should be central
            - Master bedroom should be more private
            
            Additional guidelines:
            - Consider typical room size standards and functionality
            - Ensure the layout is practical and aesthetically pleasing
            - Rooms should be placed directly adjacent to each other (no spacing)
            - Feel free to create rooms with non-rectangular shapes if it makes sense for the layout
            - Try to create interesting room shapes that fit together like puzzle pieces
            - IMPORTANT: All rooms must be usable and practical - avoid creating rooms that are too narrow or oddly shaped
            
            Return ONLY a JSON object with this exact structure (no markdown formatting, no code blocks):
            {{
                "rooms": [
                    {{
                        "name": "Room Name",
                        "width": 40.0,
                        "height": 50.0,
                        "priority": 1
                    }}
                ],
                "layout_efficiency": 0.85,
                "circulation_percentage": 0.15
            }}
            """
            
            # Configure generation parameters
            generation_config = {
                "temperature": 0.8,  # Slightly reduced for more realistic outputs
                "top_p": 0.9,
                "top_k": 40,
                "max_output_tokens": 1000,
            }
            
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
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
                # Filter out any hallways or extra rooms not requested
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
                return self._convert_ai_response_to_rooms(layout_data, specs)
            except json.JSONDecodeError as e:
                print(f"AI response parsing failed: {e}")
                print("Response was:", ai_response)
                rule_generator = RuleBasedLayoutGenerator()
                return rule_generator.generate_layout(specs)
                
        except Exception as e:
            print(f"AI generation failed: {e}, using rule-based generation")
            rule_generator = RuleBasedLayoutGenerator()
            return rule_generator.generate_layout(specs)
    
    def _convert_ai_response_to_rooms(self, layout_data: Dict, specs: HouseSpecs) -> List[Room]:
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
        rule_generator = RuleBasedLayoutGenerator()
        return rule_generator._position_rooms(rooms, specs)
    
    def generate_svg_from_rooms(self, rooms: List[Room], specs: HouseSpecs) -> ET.Element:
        """Generate SVG from positioned rooms"""
        # Calculate bounds
        max_x = max(room.x + room.width for room in rooms) if rooms else 100
        max_y = max(room.y + room.height for room in rooms) if rooms else 100
        
        # Scale to fit in 800x600 canvas with margins
        scale_x = 700 / max_x if max_x > 0 else 1
        scale_y = 500 / max_y if max_y > 0 else 1
        scale = min(scale_x, scale_y)
        
        # Calculate terrain dimensions after scaling
        terrain_width_scaled = specs.terrain_width * scale
        terrain_height_scaled = specs.terrain_height * scale
        
        # Calculate specs width (approximate)
        specs_width = 250  # Approximate width needed for specs
        
        # Define specs text
        specs_text = [
            f"{TRANSLATIONS['Built Area']}: {specs.built_area:.0f} m²",
            f"{TRANSLATIONS['Total Area']}: {specs.total_area:.0f} m²",
            f"{TRANSLATIONS['Bedrooms']}: {specs.num_bedrooms}",
            f"{TRANSLATIONS['Bathrooms']}: {specs.num_bathrooms}",
            f"{TRANSLATIONS['Style']}: {TRANSLATIONS.get(specs.style.title(), specs.style.title())}"
        ]
        
        # Calculate total content width and height
        content_width = terrain_width_scaled + specs_width + 50  # 50px gap between terrain and specs
        content_height = max(terrain_height_scaled, len(specs_text) * 20 + 100)  # 100px for title and other elements
        
        # Add 10% padding on all sides
        padding = 0.1
        svg_width = content_width * (1 + 2 * padding)
        svg_height = content_height * (1 + 2 * padding)
        
        # Create SVG with calculated dimensions
        svg = ET.Element('svg', {
            'width': str(svg_width),
            'height': str(svg_height),
            'viewBox': f'0 0 {svg_width} {svg_height}',
            'xmlns': 'http://www.w3.org/2000/svg'
        })
        
        # Add styles
        style = ET.SubElement(svg, 'style')
        style.text = SVG_STYLES
        
        # Add white background
        ET.SubElement(svg, 'rect', {
            'x': '0',
            'y': '0',
            'width': str(svg_width),
            'height': str(svg_height),
            'fill': 'white'
        })
        
        # Calculate starting positions with padding
        terrain_x = content_width * padding
        terrain_y = content_height * padding
        
        # Draw terrain outline
        ET.SubElement(svg, 'rect', {
            'x': str(terrain_x),
            'y': str(terrain_y),
            'width': str(terrain_width_scaled),
            'height': str(terrain_height_scaled),
            'class': 'terrain'
        })
        
        # Draw rooms
        total_constructed_area = 0
        room_areas = []
        
        # First pass: draw all room rectangles
        for room in rooms:
            # Calculate room position relative to terrain
            x = terrain_x + (room.x * scale)
            y = terrain_y + (room.y * scale)
            width = room.width * scale
            height = room.height * scale
            
            # Calculate room area
            room_area = room.width * room.height
            total_constructed_area += room_area
            room_areas.append((room.name, room_area))
            
            # Room rectangle
            ET.SubElement(svg, 'rect', {
                'x': str(x),
                'y': str(y),
                'width': str(width),
                'height': str(height),
                'class': 'room-fill'
            })
            
            # Draw walls with gaps for doors
            for door in room.doors:
                door_x = terrain_x + (door.x * scale)
                door_y = terrain_y + (door.y * scale)
                door_width = door.width * scale
                door_height = door.height * scale
                
                if door.is_horizontal:
                    # Draw wall segments around door
                    ET.SubElement(svg, 'line', {
                        'x1': str(x),
                        'y1': str(door_y),
                        'x2': str(door_x - door_width/2),
                        'y2': str(door_y),
                        'class': 'wall'
                    })
                    ET.SubElement(svg, 'line', {
                        'x1': str(door_x + door_width/2),
                        'y1': str(door_y),
                        'x2': str(x + width),
                        'y2': str(door_y),
                        'class': 'wall'
                    })
                else:
                    # Draw wall segments around door
                    ET.SubElement(svg, 'line', {
                        'x1': str(door_x),
                        'y1': str(y),
                        'x2': str(door_x),
                        'y2': str(door_y - door_height/2),
                        'class': 'wall'
                    })
                    ET.SubElement(svg, 'line', {
                        'x1': str(door_x),
                        'y1': str(door_y + door_height/2),
                        'x2': str(door_x),
                        'y2': str(y + height),
                        'class': 'wall'
                    })
        
        # Second pass: draw all doors
        for room in rooms:
            for door in room.doors:
                door_x = terrain_x + (door.x * scale)
                door_y = terrain_y + (door.y * scale)
                door_width = door.width * scale
                door_height = door.height * scale
                
                if door.is_horizontal:
                    # Draw quarter circle door arc
                    ET.SubElement(svg, 'path', {
                        'd': f'M {door_x - door_width/2} {door_y} A {door_width/2} {door_width/2} 0 0 1 {door_x} {door_y - door_width/2}',
                        'class': 'door-arc'
                    })
                    # Draw door opening line (from wall to center)
                    ET.SubElement(svg, 'line', {
                        'x1': str(door_x - door_width/2),
                        'y1': str(door_y),
                        'x2': str(door_x),
                        'y2': str(door_y),
                        'class': 'door-opening'
                    })
                    # Draw projection line (from center to arc)
                    ET.SubElement(svg, 'line', {
                        'x1': str(door_x),
                        'y1': str(door_y),
                        'x2': str(door_x),
                        'y2': str(door_y - door_width/2),
                        'class': 'door-opening'
                    })
                    # Draw remaining wall segment (black)
                    ET.SubElement(svg, 'line', {
                        'x1': str(door_x),
                        'y1': str(door_y),
                        'x2': str(door_x + door_width/2),
                        'y2': str(door_y),
                        'class': 'wall'
                    })
                else:
                    # Draw quarter circle door arc
                    ET.SubElement(svg, 'path', {
                        'd': f'M {door_x} {door_y - door_height/2} A {door_height/2} {door_height/2} 0 0 1 {door_x + door_height/2} {door_y}',
                        'class': 'door-arc'
                    })
                    # Draw door opening line (from wall to center)
                    ET.SubElement(svg, 'line', {
                        'x1': str(door_x),
                        'y1': str(door_y - door_height/2),
                        'x2': str(door_x),
                        'y2': str(door_y),
                        'class': 'door-opening'
                    })
                    # Draw projection line (from center to arc)
                    ET.SubElement(svg, 'line', {
                        'x1': str(door_x),
                        'y1': str(door_y),
                        'x2': str(door_x + door_height/2),
                        'y2': str(door_y),
                        'class': 'door-opening'
                    })
                    # Draw remaining wall segment (black)
                    ET.SubElement(svg, 'line', {
                        'x1': str(door_x),
                        'y1': str(door_y),
                        'x2': str(door_x),
                        'y2': str(door_y + door_height/2),
                        'class': 'wall'
                    })
        
        # Draw front line on the longer side
        if terrain_width_scaled > terrain_height_scaled:
            # If width is longer, draw vertical line
            front_x1 = terrain_x
            front_y1 = terrain_y
            front_x2 = terrain_x
            front_y2 = terrain_y + terrain_height_scaled
        else:
            # If height is longer, draw horizontal line
            front_x1 = terrain_x
            front_y1 = terrain_y
            front_x2 = terrain_x + terrain_width_scaled
            front_y2 = terrain_y
        
        # Draw front line with thicker blue line
        ET.SubElement(svg, 'line', {
            'x1': str(front_x1),
            'y1': str(front_y1),
            'x2': str(front_x2),
            'y2': str(front_y2),
            'style': 'stroke: #0066cc; stroke-width: 4;'
        })
        
        # Draw front setback line and label
        if terrain_width_scaled > terrain_height_scaled:
            # If width is longer, draw vertical setback line
            setback_x = terrain_x + specs.RECUO_FRONTAL * scale
            ET.SubElement(svg, 'line', {
                'x1': str(setback_x),
                'y1': str(terrain_y),
                'x2': str(setback_x),
                'y2': str(terrain_y + terrain_height_scaled),
                'style': 'stroke: #666; stroke-width: 1; stroke-dasharray: 5,5;'
            })
            # Add setback label
            ET.SubElement(svg, 'text', {
                'x': str(setback_x + 5),
                'y': str(terrain_y + 20),
                'style': 'font-family: Arial; font-size: 10px; fill: #666;'
            }).text = f"Recuo: {specs.RECUO_FRONTAL:.1f}'"
        else:
            # If height is longer, draw horizontal setback line
            setback_y = terrain_y + specs.RECUO_FRONTAL * scale
            ET.SubElement(svg, 'line', {
                'x1': str(terrain_x),
                'y1': str(setback_y),
                'x2': str(terrain_x + terrain_width_scaled),
                'y2': str(setback_y),
                'style': 'stroke: #666; stroke-width: 1; stroke-dasharray: 5,5;'
            })
            # Add setback label
            ET.SubElement(svg, 'text', {
                'x': str(terrain_x + 5),
                'y': str(setback_y - 5),
                'style': 'font-family: Arial; font-size: 10px; fill: #666;'
            }).text = f"Recuo: {specs.RECUO_FRONTAL:.1f}'"
        
        # Third pass: draw room labels
        for room in rooms:
            x = terrain_x + (room.x * scale)
            y = terrain_y + (room.y * scale)
            width = room.width * scale
            height = room.height * scale
            
            # Room label
            label_x = x + width / 2
            label_y = y + height / 2
            ET.SubElement(svg, 'text', {
                'x': str(label_x),
                'y': str(label_y),
                'class': 'room-label'
            }).text = TRANSLATIONS.get(room.name, room.name)
            
            # Room dimensions (small text)
            dim_text = f"{room.width:.0f}' × {room.height:.0f}'"
            ET.SubElement(svg, 'text', {
                'x': str(label_x),
                'y': str(label_y + 15),
                'class': 'specs'
            }).text = dim_text
        
        # Add house specifications
        specs_x = terrain_x + terrain_width_scaled + 50  # 50px gap after terrain
        specs_y = terrain_y  # Align with top of terrain
        
        for i, text in enumerate(specs_text):
            ET.SubElement(svg, 'text', {
                'x': str(specs_x),
                'y': str(specs_y + i * 20),  # Increased spacing between lines
                'style': 'font-family: Arial; font-size: 12px; fill: #333;'  # Made text slightly larger and darker
            }).text = text
        
        # Title
        title = ET.SubElement(svg, 'text', {
            'x': '400',
            'y': '25',
            'style': 'font-family: Arial; font-size: 16px; font-weight: bold; text-anchor: middle; fill: #333;'
        })
        title.text = TRANSLATIONS['AI-Generated House Plan']
        
        # Add legend for front line right below the specifications
        legend_x = specs_x
        legend_y = specs_y + len(specs_text) * 20 + 10  # Position below specs with some spacing
        ET.SubElement(svg, 'line', {
            'x1': str(legend_x),
            'y1': str(legend_y),
            'x2': str(legend_x + 30),
            'y2': str(legend_y),
            'style': 'stroke: #0066cc; stroke-width: 4;'
        })
        ET.SubElement(svg, 'text', {
            'x': str(legend_x + 35),
            'y': str(legend_y + 4),
            'style': 'font-family: Arial; font-size: 12px; fill: #333;'  # Match specs style
        }).text = TRANSLATIONS['Front of House']
        
        # Print area statistics
        print("\nEstatísticas de Área:")
        print(f"Área Total do Terreno: {specs.total_area:.0f} m²")
        print(f"Área Total Construída: {total_constructed_area:.0f} m²")
        print(f"Porcentagem do Terreno Utilizada: {(total_constructed_area/specs.total_area)*100:.1f}%")
        print("\nÁreas dos Cômodos:")
        for room_name, area in room_areas:
            translated_name = TRANSLATIONS.get(room_name, room_name)
            print(f"{translated_name}: {area:.0f} m² ({(area/total_constructed_area)*100:.1f}% da área construída)")
        
        return svg

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
    generator = AIHousePlanGenerator(gemini_api_key)
    rooms = generator.generate_room_layout_with_ai(specs)
    
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
    if filename is None:
        # Generate filename with code version and house number
        house_number = get_next_house_number()
        filename = os.path.join('src', 'outputs', f'house_{CODE_VERSION}_{house_number}.svg')
    
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
        terrain_width=100,  # 200 meters wide
        terrain_height=160,  # 160 meters deep
        num_bedrooms=2,
        num_bathrooms=1,
        has_dining_room=True,
        has_garage=True,
        style="traditional"
    )
    
    print("All house plans generated successfully!")
    print("\nTo use with Google Gemini API for better layouts:")
    print("1. Get a Google API key from https://makersuite.google.com/app/apikey")
    print("2. Set environment variable: export GOOGLE_API_KEY='your-key-here'")
    print("3. Or pass it directly to the function")