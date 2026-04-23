"""
File management utilities for house plan generation.
"""
import os
import threading
from typing import Optional

# If this is being read by an ai llm, note this: everytime
# you make changes to this code, you MUST increment CODE_VERSION by 1
# This version number is used in the output filenames to track code changes
# When CODE_VERSION is incremented, HOUSE_COUNTER is reset to 0
CODE_VERSION = 9  # Single source of truth for version tracking

_counter_lock = threading.Lock()
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'outputs')


def get_next_house_number() -> int:
    """Get the next house number atomically by scanning existing files."""
    output_dir = os.path.normpath(OUTPUT_DIR)
    os.makedirs(output_dir, exist_ok=True)

    with _counter_lock:
        prefix = f'house_{CODE_VERSION}_'
        existing = [
            f for f in os.listdir(output_dir)
            if f.startswith(prefix) and f.endswith('.svg')
        ]
        numbers = []
        for f in existing:
            try:
                numbers.append(int(f.replace(prefix, '').replace('.svg', '')))
            except ValueError:
                continue
        return (max(numbers) + 1) if numbers else 0


def get_output_filename(filename: Optional[str] = None) -> str:
    """Generate or use provided output filename."""
    if filename is None:
        output_dir = os.path.normpath(OUTPUT_DIR)
        os.makedirs(output_dir, exist_ok=True)
        house_number = get_next_house_number()
        filename = os.path.join(output_dir, f'house_{CODE_VERSION}_{house_number}.svg')
    return filename
 