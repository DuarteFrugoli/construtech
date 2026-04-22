"""
Testes de conectividade com APIs externas.
Verifica se as chaves estão válidas e se os serviços estão respondendo.

Rodar com:
    ..\\venv\\Scripts\\pytest tests\\test_external_apis.py -v
"""
import os
import sys
import pytest
import requests
from dotenv import load_dotenv

# Carrega as variáveis do .env da raiz do projeto
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ---------------------------------------------------------------------------
# Google Maps — Geocoding API
# ---------------------------------------------------------------------------

class TestGoogleMapsGeocoding:
    def test_chave_presente(self):
        """Verifica se a chave do Google Maps está no .env"""
        assert GOOGLE_MAPS_API_KEY, "GOOGLE_MAPS_API_KEY não encontrada no .env"
        assert len(GOOGLE_MAPS_API_KEY) > 10, "GOOGLE_MAPS_API_KEY parece inválida (muito curta)"

    def test_geocoding_retorna_200(self):
        """Verifica se a API de Geocoding responde com status 200"""
        response = requests.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={"address": "São Paulo, Brasil", "key": GOOGLE_MAPS_API_KEY},
            timeout=10
        )
        assert response.status_code == 200, f"Status inesperado: {response.status_code}"

    def test_geocoding_chave_valida(self):
        """Verifica se a chave é aceita pela API (sem REQUEST_DENIED)"""
        response = requests.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={"address": "São Paulo, Brasil", "key": GOOGLE_MAPS_API_KEY},
            timeout=10
        )
        data = response.json()
        status = data.get("status")
        assert status != "REQUEST_DENIED", (
            f"Chave recusada pela API de Geocoding. Mensagem: {data.get('error_message', 'sem detalhes')}"
        )
        assert status in ("OK", "ZERO_RESULTS"), f"Status inesperado: {status}"

    def test_geocoding_retorna_coordenadas(self):
        """Verifica se a API retorna coordenadas para um endereço válido"""
        response = requests.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={"address": "Avenida Paulista, São Paulo", "key": GOOGLE_MAPS_API_KEY},
            timeout=10
        )
        data = response.json()
        assert data.get("status") == "OK", f"Status: {data.get('status')}"
        results = data.get("results", [])
        assert len(results) > 0, "Nenhum resultado retornado"
        location = results[0]["geometry"]["location"]
        assert "lat" in location and "lng" in location
        # Coordenadas devem estar na região de São Paulo
        assert -24.0 < location["lat"] < -23.0
        assert -47.0 < location["lng"] < -46.0


# ---------------------------------------------------------------------------
# Google Maps — Elevation API
# ---------------------------------------------------------------------------

class TestGoogleMapsElevation:
    def test_elevation_chave_valida(self):
        """Verifica se a chave é aceita pela API de Elevation"""
        response = requests.get(
            "https://maps.googleapis.com/maps/api/elevation/json",
            params={"locations": "-23.5505,-46.6333", "key": GOOGLE_MAPS_API_KEY},
            timeout=10
        )
        data = response.json()
        status = data.get("status")
        assert status != "REQUEST_DENIED", (
            f"Chave recusada pela API de Elevation. Mensagem: {data.get('error_message', 'sem detalhes')}"
        )

    def test_elevation_retorna_valor(self):
        """Verifica se a API retorna um valor de elevação numérico"""
        response = requests.get(
            "https://maps.googleapis.com/maps/api/elevation/json",
            params={"locations": "-23.5505,-46.6333", "key": GOOGLE_MAPS_API_KEY},
            timeout=10
        )
        data = response.json()
        assert data.get("status") == "OK", f"Status: {data.get('status')}"
        results = data.get("results", [])
        assert len(results) > 0
        elevation = results[0].get("elevation")
        assert isinstance(elevation, (int, float)), f"Elevação inválida: {elevation}"
        assert elevation > 0, "Elevação de São Paulo deve ser positiva"


# ---------------------------------------------------------------------------
# OpenAI — API de Imagens (DALL-E)
# ---------------------------------------------------------------------------

class TestOpenAI:
    def test_chave_presente(self):
        """Verifica se a chave da OpenAI está no .env"""
        assert OPENAI_API_KEY, "OPENAI_API_KEY não encontrada no .env"
        assert OPENAI_API_KEY.startswith("sk-"), "OPENAI_API_KEY não tem o formato esperado (deve começar com 'sk-')"

    def test_autenticacao_valida(self):
        """Verifica se a chave é aceita pela OpenAI (chama /models que é barato)"""
        response = requests.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            timeout=10
        )
        assert response.status_code != 401, "Chave da OpenAI inválida ou expirada (401 Unauthorized)"
        assert response.status_code != 403, "Chave da OpenAI sem permissão (403 Forbidden)"
        assert response.status_code == 200, f"Status inesperado: {response.status_code}"

    def test_dalle_model_disponivel(self):
        """Verifica se o modelo dall-e-3 está disponível na conta"""
        response = requests.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            timeout=10
        )
        assert response.status_code == 200
        models = [m["id"] for m in response.json().get("data", [])]
        assert "dall-e-3" in models, (
            f"dall-e-3 não encontrado nos modelos disponíveis. Modelos: {models[:10]}..."
        )


# ---------------------------------------------------------------------------
# Google Gemini API
# ---------------------------------------------------------------------------

class TestGeminiAPI:
    def test_chave_presente(self):
        """Verifica se a chave do Gemini está no .env"""
        assert GEMINI_API_KEY, "GEMINI_API_KEY não encontrada no .env"
        assert len(GEMINI_API_KEY) > 10, "GEMINI_API_KEY parece inválida (muito curta)"

    def test_listar_modelos(self):
        """Verifica se a chave permite listar os modelos disponíveis"""
        response = requests.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            params={"key": GEMINI_API_KEY},
            timeout=10
        )
        assert response.status_code != 400, "Chave do Gemini inválida (400)"
        assert response.status_code != 403, (
            f"Chave do Gemini recusada (403). Detalhes: {response.text[:200]}"
        )
        assert response.status_code == 200, f"Status inesperado: {response.status_code} — {response.text[:200]}"

    def test_gemini_flash_disponivel(self):
        """Verifica se o modelo gemini-1.5-flash está disponível"""
        response = requests.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            params={"key": GEMINI_API_KEY},
            timeout=10
        )
        assert response.status_code == 200
        models = [m["name"] for m in response.json().get("models", [])]
        flash_available = any("gemini-1.5-flash" in m for m in models)
        assert flash_available, (
            f"gemini-1.5-flash não encontrado. Modelos disponíveis: {models[:5]}..."
        )

    def test_gemini_responde_prompt_simples(self):
        """Faz uma chamada real ao Gemini com um prompt mínimo para verificar funcionamento"""
        response = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
            params={"key": GEMINI_API_KEY},
            json={"contents": [{"parts": [{"text": "Responda apenas: ok"}]}]},
            timeout=15
        )
        assert response.status_code == 200, (
            f"Gemini retornou erro {response.status_code}: {response.text[:300]}"
        )
        data = response.json()
        candidates = data.get("candidates", [])
        assert len(candidates) > 0, "Nenhum candidato retornado pelo Gemini"
        text = candidates[0]["content"]["parts"][0]["text"]
        assert isinstance(text, str) and len(text) > 0, "Resposta vazia do Gemini"
