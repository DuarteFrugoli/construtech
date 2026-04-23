import math
import logging
from typing import List
from core.models import Room, HouseSpecs, Door

logger = logging.getLogger(__name__)

class RuleBasedLayoutGenerator:
    def __init__(self):
        pass

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
        print(f"\nDEBUG: Total room area before scaling: {total_room_area:.0f} m²")
        
        # Scale rooms to match the desired building percentage
        target_area = specs.built_area
        if total_room_area > 0:
            scale_factor = math.sqrt(target_area / total_room_area)
            print(f"DEBUG: Scale factor: {scale_factor:.2f}")
            for room in rooms:
                room.width *= scale_factor
                room.height *= scale_factor
                print(f"DEBUG: Scaled {room.name}: {room.width:.0f} x {room.height:.0f} = {room.area:.0f} m²")
        
        final_area = sum(room.area for room in rooms)
        print(f"\nDEBUG: Final total area: {final_area:.0f} m²")
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