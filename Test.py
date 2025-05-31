from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Tuple
import requests
import logging
import math
from geopy.distance import geodesic

# --- CONFIGURAÇÕES ---
GOOGLE_API_KEY = "AIzaSyAB_RNeA3SUG_mUivMEZrKECowFebeHChw"
OPENAI_API_KEY = "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"

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# App FastAPI
app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- FUNÇÕES AUXILIARES ---

def obter_elevacoes(pontos: List[Tuple[float, float]]) -> List[float]:
    url = "https://maps.googleapis.com/maps/api/elevation/json"
    locacoes = "|".join([f"{lat},{lng}" for lat, lng in pontos])
    resposta = requests.get(url, params={"locations": locacoes, "key": GOOGLE_API_KEY}).json()
    if resposta["status"] != "OK":
        raise HTTPException(status_code=400, detail=f"Erro ao obter elevações: {resposta['status']}")
    return [resultado["elevation"] for resultado in resposta["results"]]

# --- ENDPOINTS ---

@app.get("/elevacao-terreno")
def analisar_terreno_por_coordenadas(
        latitude: float = Query(..., description="Latitude da propriedade"),
        longitude: float = Query(..., description="Longitude da propriedade")
):
    try:
        PRECISAO = 0.0005
        lat, lng = latitude, longitude

        pontos = [
            (lat, lng), (lat + PRECISAO, lng), (lat - PRECISAO, lng),
            (lat, lng + PRECISAO), (lat, lng - PRECISAO)
        ]
        elevacoes = obter_elevacoes(pontos)

        elev_min = min(elevacoes)
        elev_max = max(elevacoes)
        diferenca = elev_max - elev_min

        idx_min = elevacoes.index(elev_min)
        idx_max = elevacoes.index(elev_max)
        distancia_real = geodesic(pontos[idx_min], pontos[idx_max]).meters

        inclinacao_rad = math.atan(diferenca / distancia_real)
        inclinacao_graus = math.degrees(inclinacao_rad)
        inclinacao_percentual = (diferenca / distancia_real) * 100

        return {
            "diferenca_altura": round(diferenca, 2),
            "inclinacao_graus": round(inclinacao_graus, 2),
            "inclinacao_percentual": round(inclinacao_percentual, 2),
        }

    except Exception as e:
        logger.error(f"Erro: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao analisar terreno")


@app.post("/gerar-imagem-casa")
def gerar_imagem_casa(
        descricao: str = Query(...),
        lat: float = Query(...),
        lng: float = Query(...)
):
    """
    Gera uma imagem simulada da casa com base na descrição do cliente e inclinação do terreno usando OpenAI DALL·E.
    """
    try:
        resultado = analisar_terreno_por_coordenadas(lat, lng)
        inclinacao = resultado['inclinacao_percentual']
        graus = resultado['inclinacao_graus']
        diferenca = resultado['diferenca_altura']

        prompt = f"""
        A house adapted to a sloped terrain. The terrain has an inclination of approximately {inclinacao:.2f}%, graus of inclination {graus:.2f} and a height difference of {diferenca:.2f} meters.
        Description from the client: {descricao} 
        Using the address data, the house is optimized for natural lighting
        Rendering: Realistic 3D with natural lighting
        Focus: Show how natural light penetrates interior spaces
        Architectural elements that should be present:
        - Large, strategically positioned windows
        - Skylights for overhead light
        - Use of translucent materials where appropriate
        - Side openings for cross ventilation
        - Adjustable sunshades
        No visible text or labels
        """

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }

        data = {
            "model": "dall-e-3",
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024"
        }

        response = requests.post("https://api.openai.com/v1/images/generations", headers=headers, json=data)
        response.raise_for_status()
        imagem_url = response.json()["data"][0]["url"]

        return {"imagem_url": imagem_url}

    except Exception as e:
        logger.error(f"Erro ao gerar imagem com DALL·E: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao gerar imagem com OpenAI")

