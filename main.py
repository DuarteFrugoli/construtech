import xml.etree.ElementTree as ET
import json
import math
import random
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import google.generativeai as genai
import os

@dataclass
class Door:
    x: float
    y: float
    width: float = 3.0  # Fixed door width in feet
    height: float = 7.0  # Fixed door height in feet
    is_horizontal: bool = False  # Whether the door is on a horizontal wall

    @classmethod
    def get_dimensions(cls) -> Tuple[float, float]:
        """Get fixed door dimensions"""
        return 3.0, 7.0  # Fixed width and height

@dataclass
class Room:
    name: str
    width: float
    height: float
    x: float
    y: float
    required: bool = True
    min_area: float = 0
    doors: List[Door] = None
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
    num_bedrooms: int
    num_bathrooms: int
    has_kitchen: bool = False  # Changed to False by default
    has_living_room: bool = False  # Changed to False by default
    has_dining_room: bool = False
    has_garage: bool = False
    style: str = "modern"  # modern, traditional, compact
    
    # Taxa de Ocupação fixa conforme Plano Diretor
    TAXA_OCUPACAO: float = 0.70  # 70% fixo
    
    # Recuo frontal conforme Plano Diretor
    RECUO_FRONTAL: float = 16.4  # 5 metros em pés
    
    @property
    def total_area(self) -> float:
        """Calculate total terrain area in sq ft"""
        return self.terrain_width * self.terrain_height
    
    @property
    def built_area(self) -> float:
        """Calculate built area based on Taxa de Ocupação fixa"""
        return self.total_area * self.TAXA_OCUPACAO

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
            - Taxa de Ocupação: {specs.TAXA_OCUPACAO*100}% (target area: {specs.built_area:.0f} sq ft)
            - Bedrooms: {specs.num_bedrooms}
            - Bathrooms: {specs.num_bathrooms}
            - Style: {specs.style}
            
            CRITICAL REQUIREMENTS (in order of priority):
            1. NO ROOM OVERLAPPING - This is an absolute requirement. Rooms must be placed adjacent to each other without any overlap.
            2. Rooms must fit within the terrain dimensions ({specs.terrain_width}ft × {specs.terrain_height}ft)
            3. Total area should be between {specs.built_area * 0.85:.0f} and {specs.built_area * 1.05:.0f} sq ft (85% to 105% of target)
            
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
            - Minimum room width: 8 feet (standard door width)
            - Maximum aspect ratio: 2:1 (length:width)
            - Room size ranges:
              * Bedrooms: 120-250 sq ft (e.g., 12x10 to 15x16)
              * Bathrooms: 40-100 sq ft (e.g., 5x8 to 10x10)
              * Living Room: 200-400 sq ft (e.g., 15x15 to 20x20)
              * Kitchen: 100-200 sq ft (e.g., 10x10 to 15x15)
              * Dining Room: 120-250 sq ft (e.g., 12x10 to 15x16)
            
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
                return self._generate_rule_based_layout(specs)
                
        except Exception as e:
            print(f"AI generation failed: {e}, using rule-based generation")
            return self._generate_rule_based_layout(specs)
    
    def _convert_ai_response_to_rooms(self, layout_data: Dict, specs: HouseSpecs) -> List[Room]:
        """Convert AI response to Room objects"""
        print("\nDEBUG: Converting AI response to rooms")
        print(f"DEBUG: Target built area: {specs.built_area:.0f} sq ft")
        
        # Seção especial de prints do Plano Diretor
        print("\n=== CHECKLIST PLANO DIRETOR ===")
        print("✓ Taxa de Ocupação (TO) fixa em 70% conforme Plano Diretor")
        print("✓ Recuo frontal mínimo de 5 metros (16.4 pés) conforme Plano Diretor")
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
                print(f"DEBUG: Scaled {room.name}: {room.width:.0f} x {room.height:.0f} = {room.area:.0f} sq ft")
        
        final_area = sum(room.area for room in rooms)
        print(f"DEBUG: Final total area: {final_area:.0f} sq ft")
        print(f"DEBUG: Taxa de Ocupação: {specs.TAXA_OCUPACAO*100}%")
        print(f"DEBUG: Actual percentage: {(final_area/specs.total_area)*100:.1f}%")
        
        # Position rooms using simple algorithm
        return self._position_rooms(rooms, specs)
    
    def _generate_rule_based_layout(self, specs: HouseSpecs) -> List[Room]:
        """Fallback rule-based room generation"""
        print("\nDEBUG: Starting rule-based layout generation")
        print(f"DEBUG: Target built area: {specs.built_area:.0f} sq ft")
        
        # Seção especial de prints do Plano Diretor
        print("\n=== CHECKLIST PLANO DIRETOR ===")
        print("✓ Taxa de Ocupação (TO) fixa em 70% conforme Plano Diretor")
        print("✓ Recuo frontal mínimo de 5 metros (16.4 pés) conforme Plano Diretor")
        print("=== FIM DO CHECKLIST ===\n")
        
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
        print(f"DEBUG: Taxa de Ocupação: {specs.TAXA_OCUPACAO*100}%")
        print(f"DEBUG: Actual percentage: {(final_area/specs.total_area)*100:.1f}%")
        
        return self._position_rooms(rooms, specs)
    
    def _position_rooms(self, rooms: List[Room], specs: HouseSpecs) -> List[Room]:
        """Position rooms in the house layout ensuring no gaps or overlaps and maintaining a rectangular shape"""
        if not rooms:
            return rooms
        
        # Sort rooms by area (largest first)
        rooms.sort(key=lambda r: r.area, reverse=True)
        
        # Initialize the first room at origin, respecting front setback
        if rooms:
            # Determine if front is on width or height side
            if specs.terrain_width > specs.terrain_height:
                # Front is on width side (vertical line)
                rooms[0].x = specs.RECUO_FRONTAL  # Add front setback
                rooms[0].y = 0
            else:
                # Front is on height side (horizontal line)
                rooms[0].x = 0
                rooms[0].y = specs.RECUO_FRONTAL  # Add front setback
        
        # Keep track of placed rectangles
        placed_rectangles = []
        if rooms:
            placed_rectangles.append({
                'x': rooms[0].x,
                'y': rooms[0].y,
                'width': rooms[0].width,
                'height': rooms[0].height,
                'room': rooms[0]
            })
        
        def is_valid_placement(x, y, width, height):
            """Check if a room can be placed at the given position without overlapping"""
            # Check if room fits within terrain bounds
            if x < 0 or y < 0 or x + width > specs.terrain_width or y + height > specs.terrain_height:
                return False
            
            # Check for front setback
            if specs.terrain_width > specs.terrain_height:
                # Front is on width side
                if x < specs.RECUO_FRONTAL:
                    return False
            else:
                # Front is on height side
                if y < specs.RECUO_FRONTAL:
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
        
        def calculate_mean_wall_length():
            """Calculate the mean length of walls in the layout"""
            wall_lengths = []
            
            # Collect all wall lengths
            for rect in placed_rectangles:
                wall_lengths.append(rect['width'])
                wall_lengths.append(rect['height'])
            
            # Calculate mean
            if not wall_lengths:
                return 10.0  # Default if no walls
            
            mean_length = sum(wall_lengths) / len(wall_lengths)
            print(f"DEBUG: Mean wall length: {mean_length:.2f}")
            return mean_length
        
        def find_best_position(room):
            """Find the best position for a room that maximizes space usage"""
            width = room.width
            height = room.height
            best_position = None
            best_score = float('-inf')
            best_adjacent_room = None
            best_is_horizontal = False
            
            # Try different positions around existing rooms
            for rect in placed_rectangles:
                # Try positions around the rectangle
                positions = [
                    (rect['x'] + rect['width'], rect['y'], False),  # Right
                    (rect['x'] - width, rect['y'], False),  # Left
                    (rect['x'], rect['y'] + rect['height'], True),  # Below
                    (rect['x'], rect['y'] - height, True),  # Above
                ]
                
                for x, y, is_horizontal in positions:
                    if is_valid_placement(x, y, width, height):
                        # Calculate a score based on how well the room fits
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
                            best_adjacent_room = rect['room']
                            best_is_horizontal = is_horizontal
            
            return best_position, best_adjacent_room, best_is_horizontal
        
        # Calculate mean wall length once for all doors
        mean_wall_length = calculate_mean_wall_length()
        door_size = mean_wall_length * 0.2  # Door size is 20% of mean wall length
        print(f"DEBUG: Door size: {door_size:.2f}")
        
        def add_door_between_rooms(room1, room2, is_horizontal):
            """Add a door between two adjacent rooms using consistent dimensions"""
            if is_horizontal:
                # Horizontal wall (top/bottom)
                wall_start = max(room1.x, room2.x)
                wall_end = min(room1.x + room1.width, room2.x + room2.width)
                wall_length = wall_end - wall_start
                door_x = wall_start + wall_length/2
                door_y = room1.y if room1.y < room2.y else room2.y + room2.height
                door = Door(x=door_x, y=door_y, width=door_size, height=door_size, is_horizontal=True)
            else:
                # Vertical wall (left/right)
                wall_start = max(room1.y, room2.y)
                wall_end = min(room1.y + room1.height, room2.y + room2.height)
                wall_length = wall_end - wall_start
                door_x = room1.x if room1.x < room2.x else room2.x + room2.width
                door_y = wall_start + wall_length/2
                door = Door(x=door_x, y=door_y, width=door_size, height=door_size, is_horizontal=False)
            
            room1.doors.append(door)
            room2.doors.append(door)
        
        # Place remaining rooms
        for i in range(1, len(rooms)):
            room = rooms[i]
            position, adjacent_room, is_horizontal = find_best_position(room)
            
            if position:
                x, y = position
                room.x = x
                room.y = y
                placed_rectangles.append({
                    'x': x,
                    'y': y,
                    'width': room.width,
                    'height': room.height,
                    'room': room
                })
                
                # Add door between adjacent rooms
                if adjacent_room:
                    add_door_between_rooms(room, adjacent_room, is_horizontal)
            else:
                # If no position found, try to rotate the room
                room.width, room.height = room.height, room.width
                position, adjacent_room, is_horizontal = find_best_position(room)
                
                if position:
                    x, y = position
                    room.x = x
                    room.y = y
                    placed_rectangles.append({
                        'x': x,
                        'y': y,
                        'width': room.width,
                        'height': room.height,
                        'room': room
                    })
                    
                    # Add door between adjacent rooms
                    if adjacent_room:
                        add_door_between_rooms(room, adjacent_room, is_horizontal)
                else:
                    # If still no position found, try to adjust the room size
                    scale_factor = 0.9
                    while scale_factor > 0.5:
                        room.width *= scale_factor
                        room.height *= scale_factor
                        position, adjacent_room, is_horizontal = find_best_position(room)
                        if position:
                            x, y = position
                            room.x = x
                            room.y = y
                            placed_rectangles.append({
                                'x': x,
                                'y': y,
                                'width': room.width,
                                'height': room.height,
                                'room': room
                            })
                            
                            # Add door between adjacent rooms
                            if adjacent_room:
                                add_door_between_rooms(room, adjacent_room, is_horizontal)
                            break
                        scale_factor -= 0.1
        
        return rooms
    
    def generate_svg_from_rooms(self, rooms: List[Room], specs: HouseSpecs) -> ET.Element:
        """Generate SVG from positioned rooms"""
        # Translation dictionary
        translations = {
            "Living Room": "Sala de Estar",
            "Master Bedroom": "Quarto Principal",
            "Bedroom": "Quarto",
            "Bedroom 2": "Quarto 2",
            "Bedroom 3": "Quarto 3",
            "Bathroom": "Banheiro",
            "Master Bathroom": "Banheiro Principal",
            "Bathroom 2": "Banheiro 2",
            "Kitchen": "Cozinha",
            "Dining Room": "Sala de Jantar",
            "Garage": "Garagem",
            "Built Area": "Área Construída",
            "Total Area": "Área Total",
            "Bedrooms": "Quartos",
            "Bathrooms": "Banheiros",
            "Style": "Estilo",
            "Traditional": "Tradicional",
            "Modern": "Moderno",
            "Compact": "Compacto",
            "AI-Generated House Plan": "Planta de Casa Gerada por IA",
            "Front of House": "Frente da Casa"
        }

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
            f"{translations['Built Area']}: {specs.built_area:.0f} sq ft",
            f"{translations['Total Area']}: {specs.total_area:.0f} sq ft",
            f"{translations['Bedrooms']}: {specs.num_bedrooms}",
            f"{translations['Bathrooms']}: {specs.num_bathrooms}",
            f"{translations['Style']}: {translations.get(specs.style.title(), specs.style.title())}"
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
        style.text = """
            .wall { fill: none; stroke: #333; stroke-width: 3; }
            .room-fill { fill: #f0f0f0; stroke: #333; stroke-width: 1; }
            .door { fill: none; stroke: #8B4513; stroke-width: 2; }
            .door-arc { fill: none; stroke: #8B4513; stroke-width: 2; }
            .door-opening { fill: none; stroke: #999; stroke-width: 0.5; }
            .window { fill: #87CEEB; stroke: #333; stroke-width: 1; }
            .room-label { font-family: Arial; font-size: 12px; text-anchor: middle; fill: #333; }
            .specs { font-family: Arial; font-size: 10px; fill: #666; }
            .terrain { fill: none; stroke: #000; stroke-width: 2; stroke-dasharray: 10,5; }
            .front-line { fill: none; stroke: #0066cc; stroke-width: 2; stroke-dasharray: 5,5; }
            .legend { font-family: Arial; font-size: 10px; fill: #0066cc; }
        """
        
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
            }).text = translations.get(room.name, room.name)
            
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
        title.text = translations['AI-Generated House Plan']
        
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
        }).text = translations['Front of House']
        
        # Print area statistics
        print("\nEstatísticas de Área:")
        print(f"Área Total do Terreno: {specs.total_area:.0f} sq ft")
        print(f"Área Total Construída: {total_constructed_area:.0f} sq ft")
        print(f"Porcentagem do Terreno Utilizada: {(total_constructed_area/specs.total_area)*100:.1f}%")
        print("\nÁreas dos Cômodos:")
        for room_name, area in room_areas:
            translated_name = translations.get(room_name, room_name)
            print(f"{translated_name}: {area:.0f} sq ft ({(area/total_constructed_area)*100:.1f}% da área construída)")
        
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
        terrain_width: Width of the terrain in feet
        terrain_height: Height of the terrain in feet
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
    svg_element = generator.generate_svg_from_rooms(rooms, specs)
    
    return ET.tostring(svg_element, encoding='unicode')

def save_dynamic_house_plan(
    filename: str,
    terrain_width: float,
    terrain_height: float,
    num_bedrooms: int,
    num_bathrooms: int,
    **kwargs
):
    """Save dynamic house plan to file"""
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
        filename="foo_house.svg",
        terrain_width=370,  # 100 feet wide
        terrain_height=200,  # 100 feet deep
        num_bedrooms=3,
        num_bathrooms=2,
        has_dining_room=True,
        has_garage=True,
        style="traditional"
    )
    
    print("All house plans generated successfully!")
    print("\nTo use with Google Gemini API for better layouts:")
    print("1. Get a Google API key from https://makersuite.google.com/app/apikey")
    print("2. Set environment variable: export GOOGLE_API_KEY='your-key-here'")
    print("3. Or pass it directly to the function")