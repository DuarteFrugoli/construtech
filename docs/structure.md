# Análise de Estrutura do Projeto — Construtech

Data: 22/04/2026 | Atualizado: 25/04/2026

---

## Estrutura atual

```
construtech/
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py          ← ponto de entrada Uvicorn
│   │   └── routes.py        ← endpoints FastAPI; retorna JSON (não mais SVG)
│   ├── ai/
│   │   └── __init__.py      ← pasta vazia (Gemini removido em 25/04/2026)
│   ├── core/
│   │   ├── __init__.py
│   │   └── models.py        ← dataclasses Room, Door, HouseSpecs
│   ├── generators/
│   │   ├── __init__.py
│   │   ├── house_plan_generator.py  ← orquestra o gerador de layout
│   │   ├── rule_based_generator.py  ← layout baseado em regras (único gerador ativo)
│   │   └── svg_generator.py         ← ÓRFÃO: não é mais importado; pode ser deletado
│   ├── services/
│   │   ├── __init__.py
│   │   ├── image_generator.py  ← DALL-E 3 (OpenAI)
│   │   └── terrain_analyzer.py ← Nominatim + Open-Elevation (gratuitos)
│   └── utils/
│       ├── __init__.py
│       ├── constants.py        ← traduções e constantes
│       └── output_manager.py   ← gerenciamento de arquivos de saída
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── FloorPlanCanvas.tsx   ← renderiza planta como SVG React nativo
│   │   │   │                            (seleção de cômodos, highlight, onRoomSelect)
│   │   │   ├── HousePlanForm.tsx     ← formulário principal + modais + painel de info
│   │   │   ├── LocationPicker.tsx    ← mapa Leaflet + OSM
│   │   │   ├── LoadingOverlay.tsx
│   │   │   └── Modal.tsx
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── .env                  ← VITE_API_URL=http://localhost:8000
│   └── vite.config.ts        ← proxy /api → localhost:8000
├── tests/
│   ├── test_routes.py        ← testes de integração dos endpoints
│   └── test_external_apis.py ← conectividade: Nominatim, Open-Elevation, OpenAI
├── outputs/                  ← artefatos gerados (fora do pacote Python)
├── docs/
│   ├── audit.md
│   ├── run-servers.md
│   ├── stack-analysis.md
│   └── structure.md
├── .env                      ← OPENAI_API_KEY (GEMINI_API_KEY removida)
├── .gitignore
└── requirements.txt
```

---

## Serviços externos

| Serviço | Função | Custo | Chave necessária |
|---------|--------|-------|-----------------|
| Nominatim (OpenStreetMap) | Geocodificação | Gratuito (limite: 1 req/s, sem uso comercial) | Não |
| Open-Elevation | Dados de altitude (resolução baixa no Brasil) | Gratuito | Não |
| Leaflet + OpenStreetMap | Mapa interativo no frontend | Gratuito | Não |
| OpenAI DALL-E 3 | Geração de imagem da casa (fachada artística) | Pago | `OPENAI_API_KEY` |

---

## Pendências de estrutura

| Item | Detalhe |
|---|---|
| `src/generators/svg_generator.py` | Arquivo órfão — não é importado em nenhum lugar desde a migração SVG→frontend. Remover após confirmar que não há regressão. |
| `src/ai/` | Pasta com só `__init__.py`. Remover se não houver plano de uso futuro próximo. |
| CORS hardcoded em `routes.py` | `allow_origins=["http://localhost:5173"]` — bloqueia qualquer deploy. Precisa ser variável de ambiente. |
