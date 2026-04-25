# Análise de Estrutura do Projeto — Construtech

Data: 22/04/2026 | Atualizado: 23/04/2026

---

## Estrutura atual (após reorganização)

```
construtech/
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py          ← ponto de entrada Uvicorn
│   │   └── routes.py        ← endpoints FastAPI
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── gemini_client.py ← singleton do modelo Gemini
│   │   └── prompt_generator.py
│   ├── core/
│   │   ├── __init__.py
│   │   └── models.py        ← dataclasses Room, Door, HouseSpecs
│   ├── generators/
│   │   ├── __init__.py
│   │   ├── ai_layout_converter.py   ← converte resposta da IA em cômodos
│   │   ├── house_plan_generator.py  ← orquestra IA + regras
│   │   ├── rule_based_generator.py  ← layout baseado em regras
│   │   └── svg_generator.py         ← gera SVG a partir dos cômodos
│   ├── services/
│   │   ├── __init__.py
│   │   ├── image_generator.py  ← DALL-E 3 (OpenAI)
│   │   └── terrain_analyzer.py ← Nominatim + Open-Elevation (gratuitos)
│   └── utils/
│       ├── __init__.py
│       ├── constants.py        ← traduções e constantes SVG
│       └── output_manager.py   ← gerenciamento de arquivos de saída
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── HousePlanForm.tsx     ← formulário principal
│   │   │   ├── HousePlanPreview.tsx  ← preview standalone (não usado)
│   │   │   ├── LocationPicker.tsx    ← mapa Leaflet + OSM
│   │   │   ├── LoadingOverlay.tsx
│   │   │   └── Modal.tsx
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── .env                  ← VITE_API_URL=http://localhost:8000
│   └── vite.config.ts        ← proxy /api → localhost:8000
├── tests/
│   ├── test_routes.py        ← testes de integração dos endpoints
│   └── test_external_apis.py ← conectividade: Nominatim, Open-Elevation, OpenAI, Gemini
├── outputs/                  ← artefatos gerados (fora do pacote Python)
├── docs/
│   ├── audit.md
│   └── structure.md
├── .env                      ← GEMINI_API_KEY, OPENAI_API_KEY
├── .gitignore
└── requirements.txt
```

---

## Serviços externos

| Serviço | Função | Custo | Chave necessária |
|---------|--------|-------|-----------------|
| Nominatim (OpenStreetMap) | Geocodificação | Gratuito | Não |
| Open-Elevation | Dados de altitude | Gratuito | Não |
| Leaflet + OpenStreetMap | Mapa interativo no frontend | Gratuito | Não |
| Google Gemini 1.5 Flash | Geração de layouts com IA | Pago (cota gratuita disponível) | `GEMINI_API_KEY` |
| OpenAI DALL-E 3 | Geração de imagem da casa | Pago | `OPENAI_API_KEY` |

---

## Pendências de estrutura

| Item | Detalhe |
|---|---|
| `HousePlanPreview.tsx` | Componente nunca importado em nenhum lugar. Remover ou integrar ao `App.tsx` (Q4) |
| Migração `google-generativeai` → `google-genai` | Biblioteca depreciada; migrar quando `google-genai` estabilizar |

---

## Resolvido

| Item | Solução |
|---|---|
| Módulos soltos em `src/` | Movidos com `git mv` para subpastas corretas |
| `src/main.py` legado | Removido (`git rm`) |
| `outputs/` dentro do pacote | Movido para raiz do projeto; `.gitignore` atualizado |
| Renomeação de 6 arquivos | `rule_based_layout.py` → `rule_based_generator.py`, `ai_response_converter.py` → `ai_layout_converter.py`, `svg_constants.py` → `constants.py`, `model_config.py` → `gemini_client.py`, `server.py` → `main.py`, `file_manager.py` → `output_manager.py` |
