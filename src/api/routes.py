"""
API routes for house plan generation.
"""
from fastapi import FastAPI, HTTPException, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict
import xml.etree.ElementTree as ET
import os

from core.models import HouseSpecs
from generators.house_plan_generator import HousePlanGenerator
from svg_generator import SVGHousePlanGenerator
from terrain_analyzer import TerrainAnalyzer
from image_generator import HouseImageGenerator

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

# Initialize services with API keys
terrain_analyzer = TerrainAnalyzer("AIzaSyAB_RNeA3SUG_mUivMEZrKECowFebeHChw")
image_generator = HouseImageGenerator("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")

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

class ImageGenerationRequest(BaseModel):
    """Request model for house image generation."""
    description: str = Field(..., description="Description of the house")
    terrain_data: Dict = Field(..., description="Terrain analysis data")

@app.get("/analyze-terrain")
async def analyze_terrain(address: str = Query(..., description="Address to analyze")):
    """
    Analyze terrain characteristics for a given address.
    Returns elevation data, slope information, and other relevant metrics.
    """
    try:
        return terrain_analyzer.analyze_terrain(address)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-house-image")
async def generate_house_image(request: ImageGenerationRequest):
    """
    Generate a realistic house image using DALL-E based on the description and terrain data.
    """
    try:
        image_url = image_generator.generate_house_image(request.description, request.terrain_data)
        return {"image_url": image_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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