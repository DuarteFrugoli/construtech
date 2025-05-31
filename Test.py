import requests
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Tuple
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

def obter_coordenadas(endereco: str) -> Tuple[float, float]:
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": endereco, "key": GOOGLE_API_KEY}
    resposta = requests.get(url, params=params).json()
    if resposta["status"] != "OK":
        raise HTTPException(status_code=400, detail=f"Erro ao geocodificar: {resposta['status']}")
    localizacao = resposta["results"][0]["geometry"]["location"]
    return localizacao["lat"], localizacao["lng"]

def obter_elevacoes(pontos: List[Tuple[float, float]]) -> List[float]:
    url = "https://maps.googleapis.com/maps/api/elevation/json"
    locacoes = "|".join([f"{lat},{lng}" for lat, lng in pontos])
    resposta = requests.get(url, params={"locations": locacoes, "key": GOOGLE_API_KEY}).json()
    if resposta["status"] != "OK":
        raise HTTPException(status_code=400, detail=f"Erro ao obter elevações: {resposta['status']}")
    return [resultado["elevation"] for resultado in resposta["results"]]

# --- ENDPOINTS ---

@app.get("/elevacao-terreno")
def analisar_terreno(endereco: str = Query(..., description="Endereço completo da propriedade")):
    try:
        PRECISAO = 0.0005

        lat, lng = obter_coordenadas(endereco)
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
            "endereco": endereco,
            "lat_lng": [lat, lng],
            "elevacao_minima": round(elev_min, 2),
            "elevacao_maxima": round(elev_max, 2),
            "diferenca_altura": round(diferenca, 2),
            "inclinacao_graus": round(inclinacao_graus, 2),
            "inclinacao_percentual": round(inclinacao_percentual, 2),
            "unidade": "metros"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao analisar terreno")

@app.post("/gerar-imagem-casa")
def gerar_imagem_casa(descricao: str = Query(...), endereco: str = Query(...)):
    """
    Gera uma imagem simulada da casa com base na descrição do cliente e inclinação do terreno usando OpenAI DALL·E.
    """
    try:
        resultado = analisar_terreno(endereco)
        inclinacao = resultado['inclinacao_percentual']
        diferenca = resultado['diferenca_altura']

        prompt = f"""
        A house adapted to a sloped terrain. The terrain has an inclination of approximately {inclinacao:.2f}% and a height difference of {diferenca:.2f} meters.
        Description from the client: {descricao}
        Show a modern facade that fits naturally with the inclined plot.
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

endereco = input()
descricao = input()
print(gerar_imagem_casa(descricao=descricao, endereco=endereco))
