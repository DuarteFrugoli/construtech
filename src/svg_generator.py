import xml.etree.ElementTree as ET
from typing import List, Dict, Tuple
from core.models import Room, HouseSpecs
from svg_constants import TRANSLATIONS, SVG_STYLES

class SVGHousePlanGenerator:
    def __init__(self):
        pass

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
            
            # Draw back line (opposite to front)
            back_x1 = terrain_x + terrain_width_scaled
            back_y1 = terrain_y
            back_x2 = terrain_x + terrain_width_scaled
            back_y2 = terrain_y + terrain_height_scaled
        else:
            # If height is longer, draw horizontal line
            front_x1 = terrain_x
            front_y1 = terrain_y
            front_x2 = terrain_x + terrain_width_scaled
            front_y2 = terrain_y
            
            # Draw back line (opposite to front)
            back_x1 = terrain_x
            back_y1 = terrain_y + terrain_height_scaled
            back_x2 = terrain_x + terrain_width_scaled
            back_y2 = terrain_y + terrain_height_scaled
        
        # Draw back line with thicker green line (draw first so it's below other elements)
        ET.SubElement(svg, 'line', {
            'x1': str(back_x1),
            'y1': str(back_y1),
            'x2': str(back_x2),
            'y2': str(back_y2),
            'style': 'stroke: #00cc00; stroke-width: 4;'
        })
        
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
            }).text = f"Recuo: {specs.RECUO_FRONTAL:.1f}m"
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
            }).text = f"Recuo: {specs.RECUO_FRONTAL:.1f}m"
        
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
            dim_text = f"{room.width:.0f}m × {room.height:.0f}m"
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
        legend_y = specs_y + len(specs_text) * 20 + 10

        # Add Plano Diretor checklist
        pd_text = [
            f"Plano Diretor:",
            f"• Taxa de Ocupação: {specs.TAXA_OCUPACAO*100}%",
            f"• Recuo Frontal: {specs.RECUO_FRONTAL:.1f}m"
        ]
        
        for i, text in enumerate(pd_text):
            ET.SubElement(svg, 'text', {
                'x': str(legend_x),
                'y': str(legend_y + i * 20),
                'style': 'font-family: Arial; font-size: 12px; fill: #333;'
            }).text = text

        # Update legend_y for front line
        legend_y += len(pd_text) * 20 + 10

        # Add back line legend
        ET.SubElement(svg, 'line', {
            'x1': str(legend_x),
            'y1': str(legend_y),
            'x2': str(legend_x + 30),
            'y2': str(legend_y),
            'style': 'stroke: #00cc00; stroke-width: 4;'
        })
        ET.SubElement(svg, 'text', {
            'x': str(legend_x + 35),
            'y': str(legend_y + 4),
            'style': 'font-family: Arial; font-size: 12px; fill: #333;'  # Match specs style
        }).text = TRANSLATIONS['Back of House']

        # Update legend_y for front line
        legend_y += 20

        # Add front line legend
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