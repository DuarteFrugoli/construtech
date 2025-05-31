"""
API routes for house plan generation.
"""
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import xml.etree.ElementTree as ET

from core.models import HouseSpecs
from generators.house_plan_generator import HousePlanGenerator
from svg_generator import SVGHousePlanGenerator

app = FastAPI(
    title="House Plan Generator API",
    description="API for generating house plans based on specifications",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

class HousePlanRequest(BaseModel):
    """Request model for house plan generation."""
    terrain_width: float = Field(..., description="Width of the terrain in meters", gt=0)
    terrain_height: float = Field(..., description="Height of the terrain in meters", gt=0)
    num_bedrooms: int = Field(..., description="Number of bedrooms", ge=1)
    num_bathrooms: int = Field(..., description="Number of bathrooms", ge=1)
    has_dining_room: bool = Field(False, description="Whether to include dining room")
    has_garage: bool = Field(False, description="Whether to include garage")
    style: str = Field("modern", description="House style (modern, traditional, compact)")
    gemini_api_key: Optional[str] = Field(None, description="Google Gemini API key for AI generation")

@app.post("/generate-house-plan")
async def generate_house_plan(request: HousePlanRequest) -> Response:
    """
    Generate a house plan based on the provided specifications.
    
    Args:
        request: House plan generation request parameters
        
    Returns:
        SVG content of the generated house plan
        
    Raises:
        HTTPException: If there's an error generating the house plan
    """
    try:
        # Create specifications
        specs = HouseSpecs(
            terrain_width=request.terrain_width,
            terrain_height=request.terrain_height,
            num_bedrooms=request.num_bedrooms,
            num_bathrooms=request.num_bathrooms,
            has_dining_room=request.has_dining_room,
            has_garage=request.has_garage,
            style=request.style
        )
        
        # Generate plan
        generator = HousePlanGenerator(request.gemini_api_key)
        rooms = generator.generate_room_layout(specs)
        
        # Generate SVG
        svg_generator = SVGHousePlanGenerator()
        svg_element = svg_generator.generate_svg_from_rooms(rooms, specs)
        
        # Convert to string
        svg_content = ET.tostring(svg_element, encoding='unicode')
        
        # Return raw SVG content
        return Response(
            content=svg_content,
            media_type="image/svg+xml"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 