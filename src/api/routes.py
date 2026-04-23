"""
API routes for house plan generation.
"""
import asyncio
import logging
import os
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional

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
    # Plano Diretor — default: genérico permissivo
    taxa_ocupacao: float = Field(0.6, description="Taxa de Ocupação (0 a 1)", gt=0, le=1)
    coeficiente_aproveitamento: float = Field(2.0, description="Coeficiente de aproveitamento", gt=0, le=20)
    recuo_frontal: float = Field(3.0, description="Recuo frontal em metros", ge=0, le=20)
    recuo_lateral: float = Field(1.5, description="Recuo lateral em metros", ge=0, le=20)
    recuo_fundo: float = Field(1.5, description="Recuo de fundo em metros", ge=0, le=20)
    num_pavimentos: int = Field(2, description="Gabarito máximo (pavimentos)", ge=1, le=30)
    taxa_permeabilidade: float = Field(0.15, description="Taxa mínima de permeabilidade (0 a 1)", ge=0, lt=1)
    description_tecnica: str = Field("", description="Requisitos técnicos para a planta (ambientes, funcionalidades)")

class ImageGenerationRequest(BaseModel):
    """Request model for house image generation."""
    description_estetica: str = Field("", description="Preferências estéticas para fachada e visual")
    description_tecnica: str = Field("", description="Requisitos técnicos (contexto para a imagem)")
    terrain_data: Dict = Field(..., description="Terrain analysis data")
    num_bedrooms: int = Field(1, ge=1, le=20)
    num_bathrooms: int = Field(1, ge=1, le=20)
    has_garage: bool = False
    has_dining_room: bool = False
    style: str = "modern"
    num_pavimentos: int = Field(1, ge=1, le=30)
    terrain_width: float = Field(10.0, gt=0, le=500)
    terrain_height: float = Field(10.0, gt=0, le=500)
    recuo_frontal: float = Field(3.0, ge=0, le=20)
    room_layout: List[Dict] = Field(default_factory=list, description="Room positions from generated plan")

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
        plan_context = {
            "num_bedrooms": request.num_bedrooms,
            "num_bathrooms": request.num_bathrooms,
            "has_garage": request.has_garage,
            "has_dining_room": request.has_dining_room,
            "style": request.style,
            "num_pavimentos": request.num_pavimentos,
            "terrain_width": request.terrain_width,
            "terrain_height": request.terrain_height,
            "recuo_frontal": request.recuo_frontal,
            "description_tecnica": request.description_tecnica,
            "room_layout": request.room_layout,
        }
        loop = asyncio.get_event_loop()
        image_url = await loop.run_in_executor(
            None, lambda: image_generator.generate_house_image(request.description_estetica, request.terrain_data, plan_context)
        )
        return {"image_url": image_url}
    except RuntimeError as e:
        logger.error(f"Image generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in generate_house_image: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao gerar imagem.")

@app.post("/generate-house-plan")
async def generate_house_plan(request: HousePlanRequest):
    """
    Generate a house plan based on the provided specifications.
    Returns JSON with 'svg' (SVG string) and 'layout' (room positions list).
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
            style=request.style,
            taxa_ocupacao=request.taxa_ocupacao,
            coeficiente_aproveitamento=request.coeficiente_aproveitamento,
            recuo_frontal=request.recuo_frontal,
            recuo_lateral=request.recuo_lateral,
            recuo_fundo=request.recuo_fundo,
            num_pavimentos=request.num_pavimentos,
            taxa_permeabilidade=request.taxa_permeabilidade,
            description_tecnica=request.description_tecnica,
        )
        
        # Generate plan
        generator = HousePlanGenerator()
        rooms = generator.generate_room_layout(specs)
        
        # Generate SVG
        svg_generator = SVGHousePlanGenerator()
        svg_element = svg_generator.generate_svg_from_rooms(rooms, specs)
        
        # Convert to string
        svg_content = ET.tostring(svg_element, encoding='unicode')

        # Serialize room layout (only spatial fields needed for image generation)
        layout = [
            {
                "name": r.name,
                "x": r.x,
                "y": r.y,
                "width": r.width,
                "height": r.height,
            }
            for r in rooms
        ]

        return {"svg": svg_content, "layout": layout}
        
    except Exception as e:
        logger.error(f"Error generating house plan: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao gerar planta.")