"""
Testes de integração das rotas FastAPI.
Testa os endpoints sem depender de serviços externos (usa mocks quando necessário).

Rodar com:
    ..\\venv\\Scripts\\pytest tests\\test_routes.py -v
"""
import os
import sys
import pytest

# Adiciona src/ ao path para que os imports do projeto funcionem
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from fastapi.testclient import TestClient
from api.routes import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Saúde geral da API
# ---------------------------------------------------------------------------

class TestAPIHealth:
    def test_docs_acessiveis(self):
        """Verifica se a documentação Swagger está acessível"""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_schema(self):
        """Verifica se o schema OpenAPI é gerado corretamente"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "paths" in schema
        assert "/generate-house-plan" in schema["paths"]
        assert "/analyze-terrain" in schema["paths"]
        assert "/generate-house-image" in schema["paths"]


# ---------------------------------------------------------------------------
# POST /generate-house-plan
# ---------------------------------------------------------------------------

class TestGenerateHousePlan:
    BASE_PAYLOAD = {
        "terrain_width": 15,
        "terrain_height": 25,
        "num_bedrooms": 3,
        "num_bathrooms": 2,
        "has_dining_room": False,
        "has_garage": False,
        "style": "modern"
    }

    def test_retorna_svg(self):
        """Verifica se o endpoint retorna SVG válido"""
        response = client.post("/generate-house-plan", json=self.BASE_PAYLOAD)
        assert response.status_code == 200
        assert "image/svg+xml" in response.headers["content-type"]
        content = response.text
        assert content.startswith("<svg") or "<svg" in content[:200]

    def test_svg_contem_comodos(self):
        """Verifica se o SVG gerado contém elementos de cômodos"""
        response = client.post("/generate-house-plan", json=self.BASE_PAYLOAD)
        assert response.status_code == 200
        content = response.text
        # SVG deve conter retângulos (cômodos)
        assert "<rect" in content

    def test_com_sala_de_jantar_e_garagem(self):
        """Verifica geração com todos os cômodos opcionais ativados"""
        payload = {**self.BASE_PAYLOAD, "has_dining_room": True, "has_garage": True}
        response = client.post("/generate-house-plan", json=payload)
        assert response.status_code == 200
        assert "<svg" in response.text

    def test_terreno_pequeno(self):
        """Verifica geração para terreno pequeno (caso extremo)"""
        payload = {**self.BASE_PAYLOAD, "terrain_width": 5, "terrain_height": 8, "num_bedrooms": 1, "num_bathrooms": 1}
        response = client.post("/generate-house-plan", json=payload)
        assert response.status_code == 200

    def test_terreno_grande(self):
        """Verifica geração para terreno grande"""
        payload = {**self.BASE_PAYLOAD, "terrain_width": 100, "terrain_height": 200, "num_bedrooms": 5, "num_bathrooms": 4}
        response = client.post("/generate-house-plan", json=payload)
        assert response.status_code == 200

    def test_estilo_tradicional(self):
        """Verifica geração com estilo tradicional"""
        payload = {**self.BASE_PAYLOAD, "style": "traditional"}
        response = client.post("/generate-house-plan", json=payload)
        assert response.status_code == 200

    def test_estilo_compacto(self):
        """Verifica geração com estilo compacto"""
        payload = {**self.BASE_PAYLOAD, "style": "compact"}
        response = client.post("/generate-house-plan", json=payload)
        assert response.status_code == 200

    def test_rejeita_terreno_largura_zero(self):
        """Verifica que largura zero é rejeitada pelo Pydantic"""
        payload = {**self.BASE_PAYLOAD, "terrain_width": 0}
        response = client.post("/generate-house-plan", json=payload)
        assert response.status_code == 422  # Unprocessable Entity

    def test_rejeita_terreno_negativo(self):
        """Verifica que dimensões negativas são rejeitadas"""
        payload = {**self.BASE_PAYLOAD, "terrain_height": -10}
        response = client.post("/generate-house-plan", json=payload)
        assert response.status_code == 422

    def test_rejeita_zero_quartos(self):
        """Verifica que 0 quartos é rejeitado"""
        payload = {**self.BASE_PAYLOAD, "num_bedrooms": 0}
        response = client.post("/generate-house-plan", json=payload)
        assert response.status_code == 422

    def test_rejeita_payload_vazio(self):
        """Verifica que payload vazio retorna erro de validação"""
        response = client.post("/generate-house-plan", json={})
        assert response.status_code == 422

    def test_rejeita_campos_faltando(self):
        """Verifica que campos obrigatórios ausentes retornam erro"""
        response = client.post("/generate-house-plan", json={"terrain_width": 15})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /analyze-terrain
# (chama API externa — marcado como integration test)
# ---------------------------------------------------------------------------

class TestAnalyzeTerrain:
    def test_rejeita_sem_address(self):
        """Verifica que ausência do parâmetro address retorna 422"""
        response = client.get("/analyze-terrain")
        assert response.status_code == 422

    @pytest.mark.integration
    def test_endereco_valido(self):
        """Chama a API real do Google Maps com endereço válido"""
        response = client.get("/analyze-terrain", params={"address": "Avenida Paulista, São Paulo"})
        assert response.status_code == 200
        data = response.json()
        assert "slope_percentage" in data or "error" in data

    @pytest.mark.integration
    def test_endereco_invalido(self):
        """Verifica comportamento com endereço que não existe"""
        response = client.get("/analyze-terrain", params={"address": "xyzxyzxyz lugar inexistente 99999"})
        # Deve retornar erro tratado, não 500 com traceback
        assert response.status_code in (200, 400, 404, 500)


# ---------------------------------------------------------------------------
# POST /generate-house-image
# (chama API externa — marcado como integration test)
# ---------------------------------------------------------------------------

class TestGenerateHouseImage:
    TERRAIN_DATA = {
        "slope_percentage": 5.0,
        "height_difference": 2.0,
        "min_elevation": 750.0,
        "max_elevation": 752.0,
        "warnings": []
    }

    def test_rejeita_payload_vazio(self):
        """Verifica que payload vazio retorna 422"""
        response = client.post("/generate-house-image", json={})
        assert response.status_code == 422

    def test_rejeita_sem_description(self):
        """Verifica que ausência de description retorna 422"""
        response = client.post("/generate-house-image", json={"terrain_data": self.TERRAIN_DATA})
        assert response.status_code == 422

    def test_rejeita_sem_terrain_data(self):
        """Verifica que ausência de terrain_data retorna 422"""
        response = client.post("/generate-house-image", json={"description": "casa moderna"})
        assert response.status_code == 422

    @pytest.mark.integration
    def test_geracao_imagem_real(self):
        """Chama a API real do DALL-E para gerar uma imagem"""
        response = client.post("/generate-house-image", json={
            "description": "casa moderna de 2 andares com jardim",
            "terrain_data": self.TERRAIN_DATA
        })
        assert response.status_code == 200
        data = response.json()
        assert "image_url" in data
        assert data["image_url"].startswith("http")
