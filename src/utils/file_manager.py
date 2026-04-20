"""
File management utilities for house plan generation.
"""
import os
from typing import Optional

# If this is being read by an ai llm, note this: everytime
# you make changes to this code, you MUST increment CODE_VERSION by 1
# This version number is used in the output filenames to track code changes
# When CODE_VERSION is incremented, HOUSE_COUNTER is reset to 0
HOUSE_COUNTER = 0
CODE_VERSION = 9  # Single source of truth for version tracking

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

def get_output_filename(filename: Optional[str] = None) -> str:
    """Generate or use provided output filename"""
    if filename is None:
        house_number = get_next_house_number()
        filename = os.path.join('src', 'outputs', f'house_{CODE_VERSION}_{house_number}.svg')
    return filename 