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
    has_kitchen: bool = False  # Changed to False by default
    has_living_room: bool = False  # Changed to False by default
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
            - Building percentage: {specs.building_percentage}% (target area: {specs.built_area:.0f} sq ft)
            - Bedrooms: {specs.num_bedrooms}
            - Bathrooms: {specs.num_bathrooms}
            - Style: {specs.style}
            
            CRITICAL REQUIREMENTS (in order of priority):
            1. NO ROOM OVERLAPPING - This is an absolute requirement. Rooms must be placed adjacent to each other without any overlap.
            2. Rooms must fit within the terrain dimensions ({specs.terrain_width}ft × {specs.terrain_height}ft)
            3. Total area should be between {specs.built_area * 0.85:.0f} and {specs.built_area * 1.05:.0f} sq ft (85% to 105% of target)
            4. Rooms can have ANY shape and size that makes sense for their function - they don't need to be rectangular
            5. Rooms should be placed in a way that maximizes space usage while maintaining functionality
            
            Additional guidelines:
            - You can create any type of room that makes sense for the house
            - Consider typical room size standards and functionality
            - Ensure the layout is practical and aesthetically pleasing
            - Rooms should be placed directly adjacent to each other (no spacing)
            - Feel free to create rooms with non-rectangular shapes if it makes sense for the layout
            - Try to create interesting room shapes that fit together like puzzle pieces
            
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
                "temperature": 1.0,  # Maximum temperature for maximum creativity
                "top_p": 1.0,  # Maximum top_p for maximum diversity
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
                return self._generate_rule_based_layout(specs)
                
        except Exception as e:
            print(f"AI generation failed: {e}, using rule-based generation")
            return self._generate_rule_based_layout(specs)
    
    def _convert_ai_response_to_rooms(self, layout_data: Dict, specs: HouseSpecs) -> List[Room]:
        """Convert AI response to Room objects"""
        print("\nDEBUG: Converting AI response to rooms")
        print(f"DEBUG: Target built area: {specs.built_area:.0f} sq ft")
        
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
            print(f"DEBUG: Initial {room.name}: {room.width:.0f} x {room.height:.0f} = {room.area:.0f} sq ft")
        
        print(f"DEBUG: Total AI area before scaling: {total_ai_area:.0f} sq ft")
        
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
                if test_percentage < specs.building_percentage - 7:
                    # Try to find a scale that gets us closer to target
                    scale_factor = math.sqrt((specs.built_area * 0.97) / total_ai_area)  # Target 97% of desired area
                    # But still don't exceed terrain constraints
                    scale_factor = min(scale_factor, terrain_scale)
            
            print(f"DEBUG: Scale factor (constrained by terrain): {scale_factor:.2f}")
            
            # Scale all rooms
            for room in rooms:
                room.width *= scale_factor
                room.height *= scale_factor
                print(f"DEBUG: Scaled {room.name}: {room.width:.0f} x {room.height:.0f} = {room.area:.0f} sq ft")
        
        final_area = sum(room.area for room in rooms)
        print(f"DEBUG: Final total area: {final_area:.0f} sq ft")
        print(f"DEBUG: Target percentage: {specs.building_percentage}%")
        print(f"DEBUG: Actual percentage: {(final_area/specs.total_area)*100:.1f}%")
        
        # Position rooms using simple algorithm
        return self._position_rooms(rooms, specs)
    
    def _generate_rule_based_layout(self, specs: HouseSpecs) -> List[Room]:
        """Fallback rule-based room generation"""
        print("\nDEBUG: Starting rule-based layout generation")
        print(f"DEBUG: Target built area: {specs.built_area:.0f} sq ft")
        
        rooms = []
        
        # Calculate house dimensions based on terrain and building percentage
        # Make the house more balanced while respecting terrain proportions
        terrain_ratio = specs.terrain_width / specs.terrain_height
        print(f"DEBUG: Terrain ratio: {terrain_ratio:.2f}")
        
        if terrain_ratio > 1.5:  # If terrain is too wide
            house_width = specs.terrain_width * 0.8
            house_height = specs.built_area / house_width
        elif terrain_ratio < 0.67:  # If terrain is too narrow
            house_height = specs.terrain_height * 0.8
            house_width = specs.built_area / house_height
        else:  # If terrain is roughly square
            house_width = math.sqrt(specs.built_area) * 0.9
            house_height = specs.built_area / house_width
        
        print(f"DEBUG: Initial house dimensions: {house_width:.0f} x {house_height:.0f}")
        
        # Define room templates with flexible proportions
        if specs.built_area < 800:  # Small house
            room_sizes = {
                "Living Room": (20, 25),
                "Kitchen": (15, 20),
                "Bedroom": (15, 18),
                "Bathroom": (8, 10)
            }
        elif specs.built_area < 1500:  # Medium house
            room_sizes = {
                "Living Room": (25, 30),
                "Kitchen": (20, 25),
                "Bedroom": (18, 20),
                "Master Bedroom": (20, 25),
                "Bathroom": (10, 12)
            }
        else:  # Large house
            room_sizes = {
                "Living Room": (30, 35),
                "Kitchen": (25, 30),
                "Bedroom": (20, 25),
                "Master Bedroom": (25, 30),
                "Bathroom": (12, 15)
            }
        
        print("\nDEBUG: Room sizes before scaling:")
        # Add required rooms
        if specs.has_living_room:
            rooms.append(Room("Living Room", *room_sizes["Living Room"], 0, 0))
            print(f"DEBUG: Living Room: {room_sizes['Living Room'][0]} x {room_sizes['Living Room'][1]}")
        
        if specs.has_kitchen:
            rooms.append(Room("Kitchen", *room_sizes["Kitchen"], 0, 0))
            print(f"DEBUG: Kitchen: {room_sizes['Kitchen'][0]} x {room_sizes['Kitchen'][1]}")
        
        # Add bedrooms
        for i in range(specs.num_bedrooms):
            if i == 0 and specs.num_bedrooms > 1:
                name = "Master Bedroom"
                size = room_sizes.get("Master Bedroom", room_sizes["Bedroom"])
            else:
                name = f"Bedroom {i+1}" if specs.num_bedrooms > 1 else "Bedroom"
                size = room_sizes["Bedroom"]
            rooms.append(Room(name, *size, 0, 0))
            print(f"DEBUG: {name}: {size[0]} x {size[1]}")
        
        # Add bathrooms
        for i in range(specs.num_bathrooms):
            name = f"Bathroom {i+1}" if specs.num_bathrooms > 1 else "Bathroom"
            rooms.append(Room(name, *room_sizes["Bathroom"], 0, 0))
            print(f"DEBUG: {name}: {room_sizes['Bathroom'][0]} x {room_sizes['Bathroom'][1]}")
        
        if specs.has_dining_room:
            rooms.append(Room("Dining Room", 20, 25, 0, 0))
            print("DEBUG: Dining Room: 20 x 25")
        
        if specs.has_garage:
            rooms.append(Room("Garage", 25, 30, 0, 0))
            print("DEBUG: Garage: 25 x 30")
        
        # Calculate current total area
        total_room_area = sum(room.area for room in rooms)
        print(f"\nDEBUG: Total room area before scaling: {total_room_area:.0f} sq ft")
        
        # Scale rooms to match the desired building percentage
        target_area = specs.built_area
        if total_room_area > 0:
            scale_factor = math.sqrt(target_area / total_room_area)
            print(f"DEBUG: Scale factor: {scale_factor:.2f}")
            for room in rooms:
                room.width *= scale_factor
                room.height *= scale_factor
                print(f"DEBUG: Scaled {room.name}: {room.width:.0f} x {room.height:.0f} = {room.area:.0f} sq ft")
        
        final_area = sum(room.area for room in rooms)
        print(f"\nDEBUG: Final total area: {final_area:.0f} sq ft")
        print(f"DEBUG: Target percentage: {specs.building_percentage}%")
        print(f"DEBUG: Actual percentage: {(final_area/specs.total_area)*100:.1f}%")
        
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
        
        def find_best_position(room):
            """Find the best position for a room that maximizes space usage"""
            width = room.width
            height = room.height
            best_position = None
            best_score = float('-inf')
            
            # Try different positions around existing rooms
            for rect in placed_rectangles:
                # Try positions around the rectangle
                positions = [
                    (rect['x'] + rect['width'], rect['y']),  # Right
                    (rect['x'] - width, rect['y']),  # Left
                    (rect['x'], rect['y'] + rect['height']),  # Below
                    (rect['x'], rect['y'] - height),  # Above
                ]
                
                for x, y in positions:
                    if is_valid_placement(x, y, width, height):
                        # Calculate a score based on how well the room fits
                        # Prefer positions that create a more compact layout
                        score = 0
                        
                        # Prefer positions that are adjacent to multiple rooms
                        for other_rect in placed_rectangles:
                            if (x + width == other_rect['x'] or x == other_rect['x'] + other_rect['width'] or
                                y + height == other_rect['y'] or y == other_rect['y'] + other_rect['height']):
                                score += 1
                        
                        # Prefer positions that are closer to the center of the terrain
                        center_x = specs.terrain_width / 2
                        center_y = specs.terrain_height / 2
                        distance_to_center = abs((x + width/2) - center_x) + abs((y + height/2) - center_y)
                        score -= distance_to_center / 100  # Normalize the distance impact
                        
                        if score > best_score:
                            best_score = score
                            best_position = (x, y)
            
            return best_position
        
        # Place remaining rooms
        for i in range(1, len(rooms)):
            room = rooms[i]
            position = find_best_position(room)
            
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
                # If no position found, try to rotate the room
                room.width, room.height = room.height, room.width
                position = find_best_position(room)
                
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
                    # If still no position found, try to adjust the room size
                    scale_factor = 0.9
                    while scale_factor > 0.5:
                        room.width *= scale_factor
                        room.height *= scale_factor
                        position = find_best_position(room)
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
                            break
                        scale_factor -= 0.1
        
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
            .terrain { fill: none; stroke: #000; stroke-width: 2; stroke-dasharray: 10,5; }
        """
        
        # Draw terrain outline
        terrain_x = 50
        terrain_y = 50
        terrain_width = specs.terrain_width * scale
        terrain_height = specs.terrain_height * scale
        
        ET.SubElement(svg, 'rect', {
            'x': str(terrain_x),
            'y': str(terrain_y),
            'width': str(terrain_width),
            'height': str(terrain_height),
            'class': 'terrain'
        })
        
        # Draw rooms
        total_constructed_area = 0
        room_areas = []
        
        for room in rooms:
            x = 50 + room.x * scale
            y = 50 + room.y * scale
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
        
        # Print area statistics
        print("\nArea Statistics:")
        print(f"Total Terrain Area: {specs.total_area:.0f} sq ft")
        print(f"Total Constructed Area: {total_constructed_area:.0f} sq ft")
        print(f"Percentage of Terrain Used: {(total_constructed_area/specs.total_area)*100:.1f}%")
        print("\nRoom Areas:")
        for room_name, area in room_areas:
            print(f"{room_name}: {area:.0f} sq ft ({(area/total_constructed_area)*100:.1f}% of constructed area)")
        
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
        terrain_width=10,  # 100 feet wide
        terrain_height=20,  # 100 feet deep
        building_percentage=85,  # 90% of terrain will be built
        num_bedrooms=2,
        num_bathrooms=1,
        has_dining_room=False,
        has_garage=False,
        style="traditional"
    )
    
    print("All house plans generated successfully!")
    print("\nTo use with Google Gemini API for better layouts:")
    print("1. Get a Google API key from https://makersuite.google.com/app/apikey")
    print("2. Set environment variable: export GOOGLE_API_KEY='your-key-here'")
    print("3. Or pass it directly to the function")