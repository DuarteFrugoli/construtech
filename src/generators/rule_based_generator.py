import math
import logging
from typing import List
from core.models import Room, HouseSpecs, Door

logger = logging.getLogger(__name__)

class RuleBasedLayoutGenerator:
    def __init__(self):
        pass

    # ── Zone classification ───────────────────────────────────────────────────
    _SOCIAL_KEYWORDS  = {"living", "kitchen", "dining", "gourmet", "varanda", "lavabo"}
    _PRIVATE_KEYWORDS = {"bedroom", "bathroom", "home office", "dependência", "dependencia"}
    _SERVICE_KEYWORDS = {"garage", "garagem", "serviço", "servico"}

    # Positive = compatible, negative = incompatible
    _ZONE_COMPATIBILITY = {
        ("social",      "social"):      3,
        ("private",     "private"):     3,
        ("service",     "service"):     2,
        ("circulation", "social"):      2,
        ("circulation", "private"):     2,
        ("circulation", "service"):     1,
        ("social",      "circulation"): 2,
        ("private",     "circulation"): 2,
        ("service",     "circulation"): 1,
        ("social",      "private"):    -8,
        ("private",     "social"):     -8,
        ("social",      "service"):    -4,
        ("service",     "social"):     -4,
        ("private",     "service"):    -3,
        ("service",     "private"):    -3,
    }
    _ZONE_ORDER = {"social": 0, "circulation": 1, "private": 2, "service": 3}

    def _get_zone(self, room_name: str) -> str:
        """Classify a room into a functional zone."""
        name = room_name.lower()
        if any(k in name for k in ("corredor", "hall", "corridor")):
            return "circulation"
        if any(k in name for k in self._SOCIAL_KEYWORDS):
            return "social"
        if any(k in name for k in self._PRIVATE_KEYWORDS):
            return "private"
        if any(k in name for k in self._SERVICE_KEYWORDS):
            return "service"
        return "social"

    def generate_layout(self, specs: HouseSpecs) -> List[Room]:
        """Generate a rule-based room layout"""
        rooms = []

        terrain_ratio = specs.terrain_width / specs.terrain_height
        
        if terrain_ratio > 1.5:
            house_width = specs.terrain_width * 0.8
            house_height = specs.built_area / house_width
        elif terrain_ratio < 0.67:
            house_height = specs.terrain_height * 0.8
            house_width = specs.built_area / house_height
        else:
            house_width = math.sqrt(specs.built_area) * 0.9
            house_height = specs.built_area / house_width

        logger.debug(f"Initial house dimensions: {house_width:.0f} x {house_height:.0f}")

        if specs.built_area < 800:
            room_sizes = {
                "Living Room": (20, 25),
                "Kitchen": (15, 20),
                "Bedroom": (15, 18),
                "Bathroom": (8, 10)
            }
        elif specs.built_area < 1500:
            room_sizes = {
                "Living Room": (25, 30),
                "Kitchen": (20, 25),
                "Bedroom": (18, 20),
                "Master Bedroom": (20, 25),
                "Bathroom": (10, 12)
            }
        else:
            room_sizes = {
                "Living Room": (30, 35),
                "Kitchen": (25, 30),
                "Bedroom": (20, 25),
                "Master Bedroom": (25, 30),
                "Bathroom": (12, 15)
            }

        if specs.has_living_room:
            rooms.append(Room("Living Room", *room_sizes["Living Room"], 0, 0))

        if specs.has_kitchen:
            rooms.append(Room("Kitchen", *room_sizes["Kitchen"], 0, 0))

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
            rooms.append(Room("Dining Room", 20, 25, 0, 0))
        
        if specs.has_garage:
            rooms.append(Room("Garage", 25, 30, 0, 0))

        if specs.has_home_office:
            rooms.append(Room("Home Office", 12, 15, 0, 0))

        if specs.has_dependencia:
            rooms.append(Room("Dependência", 15, 18, 0, 0))

        if specs.has_varanda:
            rooms.append(Room("Varanda", 12, 15, 0, 0))

        if specs.has_lavabo:
            rooms.append(Room("Lavabo", 4, 5, 0, 0))

        if specs.has_area_gourmet:
            rooms.append(Room("Área Gourmet", 20, 25, 0, 0))

        if specs.has_area_servico:
            rooms.append(Room("Área de Serviço", 8, 12, 0, 0))
        
        # Scale rooms to match the desired building percentage
        total_room_area = sum(room.area for room in rooms)
        if total_room_area > 0:
            scale_factor = math.sqrt(specs.built_area / total_room_area)
            for room in rooms:
                room.width *= scale_factor
                room.height *= scale_factor

        logger.debug(
            f"Final area: {sum(r.area for r in rooms):.0f} m² "
            f"({(sum(r.area for r in rooms)/specs.total_area)*100:.1f}% of terrain)"
        )

        # Add corridor after scaling with realistic proportions (≥2 bedrooms)
        if specs.num_bedrooms >= 2:
            bedroom_rooms = [r for r in rooms if "Bedroom" in r.name]
            corridor_width = 1.5  # standard corridor width in metres
            corridor_length = max(3.0, sum(r.width for r in bedroom_rooms))
            rooms.append(Room("Corredor", corridor_width, corridor_length, 0, 0))

        return self._position_rooms(rooms, specs)

    def _position_rooms(self, rooms: List[Room], specs: HouseSpecs) -> List[Room]:
        """Position rooms in the house layout ensuring no gaps or overlaps and maintaining a rectangular shape"""
        if not rooms:
            return rooms
        
        # Sort rooms by functional zone (social → corridor → private → service), then by area
        rooms.sort(key=lambda r: (self._ZONE_ORDER.get(self._get_zone(r.name), 99), -r.area))
        
        # Initialize the first room at origin, respecting front and lateral setbacks
        if rooms:
            if specs.terrain_width > specs.terrain_height:
                # Front is on the left (x-axis)
                rooms[0].x = specs.recuo_frontal
                rooms[0].y = specs.recuo_lateral
            else:
                # Front is on the top (y-axis)
                rooms[0].x = specs.recuo_lateral
                rooms[0].y = specs.recuo_frontal
        
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

            if specs.terrain_width > specs.terrain_height:
                # Front = left (x), Back = right, Laterals = top/bottom (y)
                if x < specs.recuo_frontal:
                    return False
                if x + width > specs.terrain_width - specs.recuo_fundo:
                    return False
                if y < specs.recuo_lateral:
                    return False
                if y + height > specs.terrain_height - specs.recuo_lateral:
                    return False
            else:
                # Front = top (y), Back = bottom, Laterals = left/right (x)
                if y < specs.recuo_frontal:
                    return False
                if y + height > specs.terrain_height - specs.recuo_fundo:
                    return False
                if x < specs.recuo_lateral:
                    return False
                if x + width > specs.terrain_width - specs.recuo_lateral:
                    return False

            # Check for overlaps with existing rooms
            for rect in placed_rectangles:
                if not (x + width <= rect['x'] or
                       x >= rect['x'] + rect['width'] or
                       y + height <= rect['y'] or
                       y >= rect['y'] + rect['height']):
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
                return 10.0
            return sum(wall_lengths) / len(wall_lengths)
        
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
                        # Zone-aware adjacency score
                        score = 0
                        room_zone = self._get_zone(room.name)

                        for other_rect in placed_rectangles:
                            is_adjacent = (
                                x + width == other_rect['x'] or
                                x == other_rect['x'] + other_rect['width'] or
                                y + height == other_rect['y'] or
                                y == other_rect['y'] + other_rect['height']
                            )
                            if is_adjacent:
                                other_zone = self._get_zone(other_rect['room'].name)
                                score += self._ZONE_COMPATIBILITY.get((room_zone, other_zone), 0)

                        # Slight preference for positions closer to terrain centre
                        center_x = specs.terrain_width / 2
                        center_y = specs.terrain_height / 2
                        distance_to_center = abs((x + width/2) - center_x) + abs((y + height/2) - center_y)
                        score -= distance_to_center / 100
                        
                        if score > best_score:
                            best_score = score
                            best_position = (x, y)
                            best_adjacent_room = rect['room']
                            best_is_horizontal = is_horizontal
            
            return best_position, best_adjacent_room, best_is_horizontal
        
        door_size = calculate_mean_wall_length() * 0.2
        
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
                    else:
                        # Room couldn't be placed at any size — remove it to avoid (0,0) overlap
                        logger.warning(f"Could not place room '{room.name}' — skipping.")
                        rooms[i] = None

        # Remove rooms that were never positioned
        positioned = [r for r in rooms if r is not None]
        return positioned 