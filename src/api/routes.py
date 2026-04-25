"""
API routes for house plan generation.
"""
import asyncio
import logging
import os
from typing import Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator

load_dotenv()

from core.models import HouseSpecs
from generators.house_plan_generator import HousePlanGenerator
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
    num_social_bathrooms: int = Field(1, description="Number of shared/social bathrooms", ge=0, le=20)
    num_suites: int = Field(0, description="Number of suite bedrooms", ge=0, le=20)
    has_dining_room: bool = Field(False, description="Whether to include dining room")
    has_garage: bool = Field(False, description="Whether to include garage")
    has_living_room: bool = Field(True, description="Whether to include living room")
    has_kitchen: bool = Field(True, description="Whether to include kitchen")
    style: str = Field("modern", description="House style (modern, traditional, compact)")
    # Plano Diretor — default: genérico permissivo
    taxa_ocupacao: float = Field(0.6, description="Taxa de Ocupação (0 a 1)", gt=0, le=1)
    coeficiente_aproveitamento: float = Field(2.0, description="Coeficiente de aproveitamento", gt=0, le=20)
    recuo_frontal: float = Field(3.0, description="Recuo frontal em metros", ge=0, le=20)
    recuo_lateral: float = Field(1.5, description="Recuo lateral em metros", ge=0, le=20)
    recuo_fundo: float = Field(1.5, description="Recuo de fundo em metros", ge=0, le=20)
    num_pavimentos: int = Field(2, description="Gabarito máximo (pavimentos)", ge=1, le=30)
    taxa_permeabilidade: float = Field(0.15, description="Taxa mínima de permeabilidade (0 a 1)", ge=0, lt=1)
    # Cômodos extras opcionais
    has_home_office: bool = False
    has_dependencia: bool = False
    has_varanda: bool = False
    has_lavabo: bool = False
    has_area_gourmet: bool = False
    has_area_servico: bool = False

    @model_validator(mode="after")
    def validate_suite_counts(self):
        if self.num_suites > self.num_bedrooms:
            raise ValueError("num_suites cannot exceed num_bedrooms")
        return self

class ImageGenerationRequest(BaseModel):
    """Request model for house image generation."""
    description_estetica: str = Field("", description="Preferências estéticas para fachada e visual")
    terrain_data: Dict = Field(..., description="Terrain analysis data")
    num_bedrooms: int = Field(1, ge=1, le=20)
    num_social_bathrooms: int = Field(1, ge=0, le=20)
    num_suites: int = Field(0, ge=0, le=20)
    has_garage: bool = False
    has_dining_room: bool = False
    has_living_room: bool = True
    has_kitchen: bool = True
    has_home_office: bool = False
    has_dependencia: bool = False
    has_varanda: bool = False
    has_lavabo: bool = False
    has_area_gourmet: bool = False
    has_area_servico: bool = False
    style: str = "modern"
    num_pavimentos: int = Field(1, ge=1, le=30)
    terrain_width: float = Field(10.0, gt=0, le=500)
    terrain_height: float = Field(10.0, gt=0, le=500)
    recuo_frontal: float = Field(3.0, ge=0, le=20)
    room_layout: List[Dict] = Field(default_factory=list, description="Room positions from generated plan")

    @model_validator(mode="after")
    def validate_suite_counts(self):
        if self.num_suites > self.num_bedrooms:
            raise ValueError("num_suites cannot exceed num_bedrooms")
        return self

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
            "num_social_bathrooms": request.num_social_bathrooms,
            "num_suites": request.num_suites,
            "num_bathrooms": request.num_social_bathrooms + request.num_suites,
            "has_garage": request.has_garage,
            "has_dining_room": request.has_dining_room,
            "has_living_room": request.has_living_room,
            "has_kitchen": request.has_kitchen,
            "has_home_office": request.has_home_office,
            "has_dependencia": request.has_dependencia,
            "has_varanda": request.has_varanda,
            "has_lavabo": request.has_lavabo,
            "has_area_gourmet": request.has_area_gourmet,
            "has_area_servico": request.has_area_servico,
            "style": request.style,
            "num_pavimentos": request.num_pavimentos,
            "terrain_width": request.terrain_width,
            "terrain_height": request.terrain_height,
            "recuo_frontal": request.recuo_frontal,
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
    Returns JSON with terrain info and room layout (positions + doors).
    """
    try:
        specs = HouseSpecs(
            terrain_width=request.terrain_width,
            terrain_height=request.terrain_height,
            num_bedrooms=request.num_bedrooms,
            num_social_bathrooms=request.num_social_bathrooms,
            num_suites=request.num_suites,
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
            has_home_office=request.has_home_office,
            has_dependencia=request.has_dependencia,
            has_varanda=request.has_varanda,
            has_lavabo=request.has_lavabo,
            has_area_gourmet=request.has_area_gourmet,
            has_area_servico=request.has_area_servico,
        )

        generator = HousePlanGenerator()
        rooms = generator.generate_room_layout(specs)

        layout = [
            {
                "name": r.name,
                "x": r.x,
                "y": r.y,
                "width": r.width,
                "height": r.height,
                "doors": [
                    {
                        "x": d.x,
                        "y": d.y,
                        "width": d.width,
                        "height": d.height,
                        "is_horizontal": d.is_horizontal,
                    }
                    for d in r.doors
                ],
            }
            for r in rooms
        ]

        return {
            "terrain": {
                "width": specs.terrain_width,
                "height": specs.terrain_height,
                "recuo_frontal": specs.recuo_frontal,
                "recuo_lateral": specs.recuo_lateral,
                "recuo_fundo": specs.recuo_fundo,
            },
            "layout": layout,
        }

    except Exception as e:
        logger.error(f"Error generating house plan: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao gerar planta.")