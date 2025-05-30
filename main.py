import xml.etree.ElementTree as ET
import json
import math
import random
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import google.generativeai as genai
import os

@dataclass
class Room:
    name: str
    width: float
    height: float
    x: float
    y: float
    required: bool = True
    min_area: float = 0
    doors: List[Dict] = None
    windows: List[Dict] = None
    
    def __post_init__(self):
        if self.doors is None:
            self.doors = []
        if self.windows is None:
            self.windows = []
    
    @property
    def area(self):
        return self.width * self.height

@dataclass
class HouseSpecs:
    terrain_width: float  # Terrain width in feet
    terrain_height: float  # Terrain height in feet
    building_percentage: float  # Percentage of terrain to be built (0-100)
    num_bedrooms: int
    num_bathrooms: int
    has_kitchen: bool = True
    has_living_room: bool = True
    has_dining_room: bool = False
    has_garage: bool = False
    style: str = "modern"  # modern, traditional, compact
    
    @property
    def total_area(self) -> float:
        """Calculate total terrain area in sq ft"""
        return self.terrain_width * self.terrain_height
    
    @property
    def built_area(self) -> float:
        """Calculate built area based on percentage"""
        return self.total_area * (self.building_percentage / 100)

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
            return self._generate_rule_based_layout(specs)
            
        try:
            prompt = f"""
            Design an optimal floor plan layout for a house with these specifications:
            - Terrain dimensions: {specs.terrain_width}ft × {specs.terrain_height}ft
            - Building percentage: {specs.building_percentage}%
            - Built area: {specs.built_area:.0f} sq ft
            - Bedrooms: {specs.num_bedrooms}
            - Bathrooms: {specs.num_bathrooms}
            - Kitchen: {'Yes' if specs.has_kitchen else 'No'}
            - Living room: {'Yes' if specs.has_living_room else 'No'}
            - Dining room: {'Yes' if specs.has_dining_room else 'No'}
            - Garage: {'Yes' if specs.has_garage else 'No'}
            - Style: {specs.style}
            
            Important guidelines:
            1. Only include the rooms specified above - do not add extra rooms like hallways
            2. Rooms can have any proportions that make sense for their function
            3. Consider typical room size standards and functionality
            4. Ensure the layout is practical and aesthetically pleasing
            5. Rooms should be placed directly adjacent to each other (no spacing)
            6. No rooms should overlap
            
            Return ONLY a JSON object with this exact structure (no markdown formatting, no code blocks):
            {{
                "rooms": [
                    {{
                        "name": "Living Room",
                        "width": 16.0,
                        "height": 20.0,
                        "priority": 1
                    }},
                    {{
                        "name": "Kitchen",
                        "width": 12.0,
                        "height": 15.0,
                        "priority": 2
                    }}
                ],
                "layout_efficiency": 0.85,
                "circulation_percentage": 0.15
            }}
            """
            
            # Configure generation parameters
            generation_config = {
                "temperature": 0.7,
                "top_p": 0.8,
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
                    if "kitchen" in name and not specs.has_kitchen:
                        continue
                    if "living" in name and not specs.has_living_room:
                        continue
                    if "dining" in name and not specs.has_dining_room:
                        continue
                    if "garage" in name and not specs.has_garage:
                        continue
                    valid_rooms.append(room)
                layout_data["rooms"] = valid_rooms
                return self._convert_ai_response_to_rooms(layout_data, specs)
            except json.JSONDecodeError as e:
                print(f"AI response parsing failed: {e}")
                print("Response was:", ai_response)
                return self._generate_rule_based_layout(specs)
                
        except Exception as e:
            print(f"AI generation failed: {e}, using rule-based generation")
            return self._generate_rule_based_layout(specs)
    
    def _convert_ai_response_to_rooms(self, layout_data: Dict, specs: HouseSpecs) -> List[Room]:
        """Convert AI response to Room objects"""
        rooms = []
        for room_data in layout_data.get("rooms", []):
            room = Room(
                name=room_data["name"],
                width=room_data["width"],
                height=room_data["height"],
                x=0,  # Will be positioned later
                y=0
            )
            rooms.append(room)
        
        # Position rooms using simple algorithm
        return self._position_rooms(rooms, specs)
    
    def _generate_rule_based_layout(self, specs: HouseSpecs) -> List[Room]:
        """Fallback rule-based room generation"""
        rooms = []
        
        # Calculate house dimensions based on terrain and building percentage
        # Make the house more balanced while respecting terrain proportions
        terrain_ratio = specs.terrain_width / specs.terrain_height
        if terrain_ratio > 1.5:  # If terrain is too wide
            house_width = specs.terrain_width * 0.8
            house_height = specs.built_area / house_width
        elif terrain_ratio < 0.67:  # If terrain is too narrow
            house_height = specs.terrain_height * 0.8
            house_width = specs.built_area / house_height
        else:  # If terrain is roughly square
            house_width = math.sqrt(specs.built_area) * 0.9
            house_height = specs.built_area / house_width
        
        # Define room templates with flexible proportions
        if specs.built_area < 800:  # Small house
            room_sizes = {
                "Living Room": (14, 16),
                "Kitchen": (10, 12),
                "Bedroom": (12, 14),
                "Bathroom": (6, 8)
            }
        elif specs.built_area < 1500:  # Medium house
            room_sizes = {
                "Living Room": (16, 20),
                "Kitchen": (12, 14),
                "Bedroom": (12, 14),
                "Master Bedroom": (14, 16),
                "Bathroom": (6, 8)
            }
        else:  # Large house
            room_sizes = {
                "Living Room": (20, 24),
                "Kitchen": (14, 16),
                "Bedroom": (12, 14),
                "Master Bedroom": (16, 18),
                "Bathroom": (8, 10)
            }
        
        # Add required rooms
        if specs.has_living_room:
            rooms.append(Room("Living Room", *room_sizes["Living Room"], 0, 0))
        
        if specs.has_kitchen:
            rooms.append(Room("Kitchen", *room_sizes["Kitchen"], 0, 0))
        
        # Add bedrooms
        for i in range(specs.num_bedrooms):
            if i == 0 and specs.num_bedrooms > 1:
                name = "Master Bedroom"
                size = room_sizes.get("Master Bedroom", room_sizes["Bedroom"])
            else:
                name = f"Bedroom {i+1}" if specs.num_bedrooms > 1 else "Bedroom"
                size = room_sizes["Bedroom"]
            rooms.append(Room(name, *size, 0, 0))
        
        # Add bathrooms
        for i in range(specs.num_bathrooms):
            name = f"Bathroom {i+1}" if specs.num_bathrooms > 1 else "Bathroom"
            rooms.append(Room(name, *room_sizes["Bathroom"], 0, 0))
        
        if specs.has_dining_room:
            rooms.append(Room("Dining Room", 12, 14, 0, 0))
        
        if specs.has_garage:
            rooms.append(Room("Garage", 20, 20, 0, 0))
        
        # Adjust room sizes to fit built area while maintaining proportions
        total_room_area = sum(room.area for room in rooms)
        if total_room_area > specs.built_area * 0.85:  # Leave 15% for circulation
            scale_factor = math.sqrt((specs.built_area * 0.85) / total_room_area)
            for room in rooms:
                room.width *= scale_factor
                room.height *= scale_factor
        
        return self._position_rooms(rooms, specs)
    
    def _position_rooms(self, rooms: List[Room], specs: HouseSpecs) -> List[Room]:
        """Position rooms in the house layout ensuring no gaps or overlaps and maintaining a rectangular shape"""
        if not rooms:
            return rooms
        
        # Sort rooms by area (largest first)
        rooms.sort(key=lambda r: r.area, reverse=True)
        
        # Initialize the first room at origin
        if rooms:
            rooms[0].x = 0
            rooms[0].y = 0
        
        # Keep track of placed rectangles
        placed_rectangles = []
        if rooms:
            placed_rectangles.append({
                'x': rooms[0].x,
                'y': rooms[0].y,
                'width': rooms[0].width,
                'height': rooms[0].height
            })
        
        def get_bounds():
            """Get the current bounds of all placed rooms"""
            if not placed_rectangles:
                return 0, 0, 0, 0
            min_x = min(r['x'] for r in placed_rectangles)
            min_y = min(r['y'] for r in placed_rectangles)
            max_x = max(r['x'] + r['width'] for r in placed_rectangles)
            max_y = max(r['y'] + r['height'] for r in placed_rectangles)
            return min_x, min_y, max_x, max_y
        
        def calculate_shape_score(x, y, width, height):
            """Calculate how well this placement maintains a rectangular shape"""
            # Get current bounds
            min_x, min_y, max_x, max_y = get_bounds()
            
            # Calculate new bounds if this room is placed
            new_min_x = min(min_x, x)
            new_min_y = min(min_y, y)
            new_max_x = max(max_x, x + width)
            new_max_y = max(max_y, y + height)
            
            # Calculate the area of the bounding rectangle
            bounding_area = (new_max_x - new_min_x) * (new_max_y - new_min_y)
            
            # Calculate the total area of all rooms including the new one
            total_room_area = sum(r['width'] * r['height'] for r in placed_rectangles) + (width * height)
            
            # The closer the bounding area is to the total room area, the more rectangular the shape
            # We want to minimize the difference between bounding area and total room area
            return bounding_area - total_room_area
        
        def is_valid_placement(x, y, width, height):
            """Check if a room can be placed at the given position without overlapping"""
            # Check if room fits within terrain bounds
            if x < 0 or y < 0 or x + width > specs.terrain_width or y + height > specs.terrain_height:
                return False
            
            # Check for overlaps with existing rooms
            for rect in placed_rectangles:
                # If there's any overlap, return False
                if not (x + width <= rect['x'] or  # New room is completely to the left
                       x >= rect['x'] + rect['width'] or  # New room is completely to the right
                       y + height <= rect['y'] or  # New room is completely below
                       y >= rect['y'] + rect['height']):  # New room is completely above
                    return False
            return True
        
        def find_best_adjacent_position(room):
            """Find the best position where the room is adjacent to at least one existing room"""
            width = room.width
            height = room.height
            best_score = float('inf')
            best_position = None
            
            # Try each placed rectangle
            for rect in placed_rectangles:
                # Try placing to the right
                x = rect['x'] + rect['width']
                y = rect['y']
                if is_valid_placement(x, y, width, height):
                    score = calculate_shape_score(x, y, width, height)
                    if score < best_score:
                        best_score = score
                        best_position = (x, y)
                
                # Try placing to the left
                x = rect['x'] - width
                y = rect['y']
                if is_valid_placement(x, y, width, height):
                    score = calculate_shape_score(x, y, width, height)
                    if score < best_score:
                        best_score = score
                        best_position = (x, y)
                
                # Try placing above
                x = rect['x']
                y = rect['y'] - height
                if is_valid_placement(x, y, width, height):
                    score = calculate_shape_score(x, y, width, height)
                    if score < best_score:
                        best_score = score
                        best_position = (x, y)
                
                # Try placing below
                x = rect['x']
                y = rect['y'] + rect['height']
                if is_valid_placement(x, y, width, height):
                    score = calculate_shape_score(x, y, width, height)
                    if score < best_score:
                        best_score = score
                        best_position = (x, y)
            
            return best_position
        
        # Place remaining rooms
        for i in range(1, len(rooms)):
            room = rooms[i]
            position = find_best_adjacent_position(room)
            
            if position:
                x, y = position
                room.x = x
                room.y = y
                placed_rectangles.append({
                    'x': x,
                    'y': y,
                    'width': room.width,
                    'height': room.height
                })
            else:
                # If no adjacent position found, try to place it at the first available position
                # This should rarely happen if the total area is sufficient
                best_score = float('inf')
                best_position = None
                
                for y in range(0, int(specs.terrain_height), int(room.height)):
                    for x in range(0, int(specs.terrain_width), int(room.width)):
                        if is_valid_placement(x, y, room.width, room.height):
                            score = calculate_shape_score(x, y, room.width, room.height)
                            if score < best_score:
                                best_score = score
                                best_position = (x, y)
                
                if best_position:
                    x, y = best_position
                    room.x = x
                    room.y = y
                    placed_rectangles.append({
                        'x': x,
                        'y': y,
                        'width': room.width,
                        'height': room.height
                    })
        
        return rooms
    
    def generate_svg_from_rooms(self, rooms: List[Room], specs: HouseSpecs) -> ET.Element:
        """Generate SVG from positioned rooms"""
        # Calculate bounds
        max_x = max(room.x + room.width for room in rooms) if rooms else 100
        max_y = max(room.y + room.height for room in rooms) if rooms else 100
        
        # Scale to fit in 800x600 canvas with margins
        scale_x = 700 / max_x if max_x > 0 else 1
        scale_y = 500 / max_y if max_y > 0 else 1
        scale = min(scale_x, scale_y)
        
        # Create SVG
        svg = ET.Element('svg', {
            'width': '800',
            'height': '600',
            'viewBox': '0 0 800 600',
            'xmlns': 'http://www.w3.org/2000/svg'
        })
        
        # Add styles
        style = ET.SubElement(svg, 'style')
        style.text = """
            .wall { fill: none; stroke: #333; stroke-width: 2; }
            .room-fill { fill: #f0f0f0; stroke: #333; stroke-width: 1; }
            .door { fill: none; stroke: #8B4513; stroke-width: 2; }
            .window { fill: #87CEEB; stroke: #333; stroke-width: 1; }
            .room-label { font-family: Arial; font-size: 12px; text-anchor: middle; fill: #333; }
            .specs { font-family: Arial; font-size: 10px; fill: #666; }
        """
        
        # Draw rooms
        for room in rooms:
            x = 50 + room.x * scale
            y = 50 + room.y * scale
            width = room.width * scale
            height = room.height * scale
            
            # Room rectangle
            ET.SubElement(svg, 'rect', {
                'x': str(x),
                'y': str(y),
                'width': str(width),
                'height': str(height),
                'class': 'room-fill'
            })
            
            # Room label
            label_x = x + width / 2
            label_y = y + height / 2
            ET.SubElement(svg, 'text', {
                'x': str(label_x),
                'y': str(label_y),
                'class': 'room-label'
            }).text = room.name
            
            # Room dimensions (small text)
            dim_text = f"{room.width:.0f}' × {room.height:.0f}'"
            ET.SubElement(svg, 'text', {
                'x': str(label_x),
                'y': str(label_y + 15),
                'class': 'specs'
            }).text = dim_text
        
        # Add house specifications
        specs_y = 20
        specs_text = [
            f"Built Area: {specs.built_area:.0f} sq ft",
            f"Total Area: {specs.total_area:.0f} sq ft",
            f"Bedrooms: {specs.num_bedrooms}",
            f"Bathrooms: {specs.num_bathrooms}",
            f"Style: {specs.style.title()}"
        ]
        
        for i, text in enumerate(specs_text):
            ET.SubElement(svg, 'text', {
                'x': '10',
                'y': str(specs_y + i * 12),
                'class': 'specs'
            }).text = text
        
        # Title
        title = ET.SubElement(svg, 'text', {
            'x': '400',
            'y': '25',
            'style': 'font-family: Arial; font-size: 16px; font-weight: bold; text-anchor: middle; fill: #333;'
        })
        title.text = f"AI-Generated House Plan"
        
        return svg

def create_dynamic_house_plan(
    terrain_width: float,
    terrain_height: float,
    building_percentage: float,
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
        terrain_width: Width of the terrain in feet
        terrain_height: Height of the terrain in feet
        building_percentage: Percentage of terrain to be built (0-100)
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
        building_percentage=building_percentage,
        num_bedrooms=num_bedrooms,
        num_bathrooms=num_bathrooms,
        has_dining_room=has_dining_room,
        has_garage=has_garage,
        style=style
    )
    
    # Generate plan
    generator = AIHousePlanGenerator(gemini_api_key)
    rooms = generator.generate_room_layout_with_ai(specs)
    svg_element = generator.generate_svg_from_rooms(rooms, specs)
    
    return ET.tostring(svg_element, encoding='unicode')

def save_dynamic_house_plan(
    filename: str,
    terrain_width: float,
    terrain_height: float,
    building_percentage: float,
    num_bedrooms: int,
    num_bathrooms: int,
    **kwargs
):
    """Save dynamic house plan to file"""
    svg_content = create_dynamic_house_plan(
        terrain_width, terrain_height, building_percentage,
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
        filename="foo_house.svg",
        terrain_width=200,  # 100 feet wide
        terrain_height=100,  # 100 feet deep
        building_percentage=50,  # 90% of terrain will be built
        num_bedrooms=4,
        num_bathrooms=2,
        has_dining_room=False,
        has_garage=False,
        style="traditional"
    )
    
    print("All house plans generated successfully!")
    print("\nTo use with Google Gemini API for better layouts:")
    print("1. Get a Google API key from https://makersuite.google.com/app/apikey")
    print("2. Set environment variable: export GOOGLE_API_KEY='your-key-here'")
    print("3. Or pass it directly to the function")