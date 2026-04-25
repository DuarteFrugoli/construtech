"""
Testes de conectividade com APIs externas.
Verifica se os serviços gratuitos estão respondendo e se as chaves pagas estão válidas.

Serviços gratuitos (sem chave):
  - Nominatim (OpenStreetMap) — geocodificação
  - Open-Elevation — dados de altitude

Serviços pagos (requerem chave no .env):
  - OpenAI DALL-E 3 — geração de imagens
  - Google Gemini — geração de layouts com IA

Rodar com:
    ..\\venv\\Scripts\\pytest tests\\test_external_apis.py -v
"""
import os
import sys
import pytest
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

NOMINATIM_HEADERS = {"User-Agent": "Construtech/1.0 (testes automatizados)"}


# ---------------------------------------------------------------------------
# Nominatim (OpenStreetMap) — Geocodificação gratuita
# ---------------------------------------------------------------------------

class TestNominatim:
    def test_retorna_200(self):
        """Verifica se o Nominatim responde com status 200"""
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": "São Paulo, Brasil", "format": "json", "limit": 1},
            headers=NOMINATIM_HEADERS,
            timeout=10,
        )
        assert response.status_code == 200, f"Status inesperado: {response.status_code}"

    def test_retorna_coordenadas(self):
        """Verifica se o Nominatim retorna coordenadas para um endereço válido"""
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": "Avenida Paulista, São Paulo", "format": "json", "limit": 1},
            headers=NOMINATIM_HEADERS,
            timeout=10,
        )
        data = response.json()
        assert len(data) > 0, "Nenhum resultado retornado pelo Nominatim"
        lat = float(data[0]["lat"])
        lng = float(data[0]["lon"])
        # Coordenadas devem estar na região de São Paulo
        assert -24.0 < lat < -23.0, f"Latitude fora da região esperada: {lat}"
        assert -47.0 < lng < -46.0, f"Longitude fora da região esperada: {lng}"

    def test_endereco_invalido_retorna_lista_vazia(self):
        """Verifica que endereço inexistente retorna lista vazia (não erro)"""
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": "xyzxyzxyz lugar inexistente 99999", "format": "json", "limit": 1},
            headers=NOMINATIM_HEADERS,
            timeout=10,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), "Resposta deve ser uma lista"
        assert len(data) == 0, "Endereço inválido não deve retornar resultados"

    def test_campos_necessarios_presentes(self):
        """Verifica se os campos lat/lon estão presentes na resposta"""
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": "Rio de Janeiro, Brasil", "format": "json", "limit": 1},
            headers=NOMINATIM_HEADERS,
            timeout=10,
        )
        data = response.json()
        assert len(data) > 0
        assert "lat" in data[0], "Campo 'lat' ausente na resposta"
        assert "lon" in data[0], "Campo 'lon' ausente na resposta"


# ---------------------------------------------------------------------------
# Open-Elevation — Dados de altitude gratuitos
# ---------------------------------------------------------------------------

class TestOpenElevation:
    def test_retorna_200(self):
        """Verifica se o Open-Elevation responde com status 200"""
        response = requests.post(
            "https://api.open-elevation.com/api/v1/lookup",
            json={"locations": [{"latitude": -23.5505, "longitude": -46.6333}]},
            timeout=20,
        )
        assert response.status_code == 200, f"Status inesperado: {response.status_code}"

    def test_retorna_elevacao_numerica(self):
        """Verifica se retorna um valor numérico de elevação"""
        response = requests.post(
            "https://api.open-elevation.com/api/v1/lookup",
            json={"locations": [{"latitude": -23.5505, "longitude": -46.6333}]},
            timeout=20,
        )
        data = response.json()
        results = data.get("results", [])
        assert len(results) > 0, "Nenhum resultado retornado"
        elevation = results[0].get("elevation")
        assert isinstance(elevation, (int, float)), f"Elevação inválida: {elevation}"
        assert elevation > 0, "Elevação de São Paulo deve ser positiva"

    def test_multiplos_pontos(self):
        """Verifica consulta com múltiplos pontos (usado pela grade 5x5 do terrain_analyzer)"""
        locations = [
            {"latitude": -23.5505 + i * 0.0001, "longitude": -46.6333 + j * 0.0001}
            for i in range(-2, 3)
            for j in range(-2, 3)
        ]
        response = requests.post(
            "https://api.open-elevation.com/api/v1/lookup",
            json={"locations": locations},
            timeout=20,
        )
        assert response.status_code == 200
        data = response.json()
        results = data.get("results", [])
        assert len(results) == 25, f"Esperado 25 resultados, obtido {len(results)}"

    def test_estrutura_resposta(self):
        """Verifica se os campos latitude/longitude/elevation estão presentes"""
        response = requests.post(
            "https://api.open-elevation.com/api/v1/lookup",
            json={"locations": [{"latitude": -23.5505, "longitude": -46.6333}]},
            timeout=20,
        )
        data = response.json()
        result = data["results"][0]
        assert "latitude" in result
        assert "longitude" in result
        assert "elevation" in result


# ---------------------------------------------------------------------------
# OpenAI — API de Imagens (DALL-E 3)
# ---------------------------------------------------------------------------

class TestOpenAI:
    def test_chave_presente(self):
        """Verifica se a chave da OpenAI está no .env"""
        assert OPENAI_API_KEY, "OPENAI_API_KEY não encontrada no .env"
        assert OPENAI_API_KEY.startswith("sk-"), "OPENAI_API_KEY não tem o formato esperado (deve começar com 'sk-')"

    def test_autenticacao_valida(self):
        """Verifica se a chave é aceita pela OpenAI"""
        response = requests.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            timeout=10,
        )
        assert response.status_code != 401, "Chave da OpenAI inválida ou expirada (401 Unauthorized)"
        assert response.status_code != 403, "Chave da OpenAI sem permissão (403 Forbidden)"
        assert response.status_code == 200, f"Status inesperado: {response.status_code}"

    def test_dalle_model_disponivel(self):
        """Verifica se o modelo dall-e-3 está disponível na conta"""
        response = requests.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            timeout=10,
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
            timeout=10,
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
            timeout=10,
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
            timeout=15,
        )
        assert response.status_code == 200, (
            f"Gemini retornou erro {response.status_code}: {response.text[:300]}"
        )
        data = response.json()
        candidates = data.get("candidates", [])
        assert len(candidates) > 0, "Nenhum candidato retornado pelo Gemini"
        text = candidates[0]["content"]["parts"][0]["text"]
        assert isinstance(text, str) and len(text) > 0, "Resposta vazia do Gemini"
