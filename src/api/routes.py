"""
API routes for house plan generation.
"""
import asyncio
import logging
import os
import xml.etree.ElementTree as ET
from typing import Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

from core.models import HouseSpecs
from generators.house_plan_generator import HousePlanGenerator
from generators.svg_generator import SVGHousePlanGenerator
from services.terrain_analyzer import TerrainAnalyzer
from services.image_generator import HouseImageGenerator

logger = logging.getLogger(__name__)

app = FastAPI(
    title="House Plan Generator API",
    description="API for generating house plans based on specifications",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# Initialize services
terrain_analyzer = TerrainAnalyzer()
image_generator = HouseImageGenerator(os.getenv("OPENAI_API_KEY", ""))

class HousePlanRequest(BaseModel):
    """Request model for house plan generation."""
    terrain_width: float = Field(..., description="Width of the terrain in meters", gt=0, le=500)
    terrain_height: float = Field(..., description="Height of the terrain in meters", gt=0, le=500)
    num_bedrooms: int = Field(..., description="Number of bedrooms", ge=1, le=20)
    num_bathrooms: int = Field(..., description="Number of bathrooms", ge=1, le=20)
    has_dining_room: bool = Field(False, description="Whether to include dining room")
    has_garage: bool = Field(False, description="Whether to include garage")
    style: str = Field("modern", description="House style (modern, traditional, compact)")

class ImageGenerationRequest(BaseModel):
    """Request model for house image generation."""
    description: str = Field(..., description="Description of the house")
    terrain_data: Dict = Field(..., description="Terrain analysis data")

@app.get("/analyze-terrain")
async def analyze_terrain(address: str = Query(..., description="Address to analyze", max_length=200)):
    """
    Analyze terrain characteristics for a given address.
    Returns elevation data, slope information, and other relevant metrics.
    """
    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: terrain_analyzer.analyze_terrain(address))
    except RuntimeError as e:
        logger.error(f"Terrain analysis error: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in analyze_terrain: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao analisar terreno.")

@app.post("/generate-house-image")
async def generate_house_image(request: ImageGenerationRequest):
    """
    Generate a realistic house image using DALL-E based on the description and terrain data.
    """
    try:
        loop = asyncio.get_event_loop()
        image_url = await loop.run_in_executor(
            None, lambda: image_generator.generate_house_image(request.description, request.terrain_data)
        )
        return {"image_url": image_url}
    except RuntimeError as e:
        logger.error(f"Image generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in generate_house_image: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao gerar imagem.")

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
        generator = HousePlanGenerator()
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
        logger.error(f"Error generating house plan: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao gerar planta.")