# Audit Report — Construtech

Data: 22/04/2026 | Atualizado: 23/04/2026

---

## 1. Bugs / Erros de Lógica

### Backend

#### ~~B1 — `gemini_api_key` enviada pelo browser~~ ✅ CORRIGIDO
Campo removido de `HousePlanRequest`. O modelo Gemini é inicializado via variável de ambiente no servidor.

#### ~~B2 — `initialize_model()` executada a cada requisição~~ ✅ CORRIGIDO
`src/ai/gemini_client.py` implementa singleton com `get_model()`. Inicialização ocorre uma única vez.

#### ~~B3 — I/O bloqueante em handlers `async`~~ ✅ CORRIGIDO
Chamadas a `terrain_analyzer` e `image_generator` agora usam `asyncio.run_in_executor` em `routes.py`.

#### ~~B4 — `KeyError` em resposta malformada da IA~~ ✅ CORRIGIDO
`src/generators/ai_layout_converter.py` usa `.get()` com valores padrão para todos os campos.

#### ~~B5 — `max()` em lista vazia~~ ✅ CORRIGIDO
Guard adicionado: se a lista de cômodos estiver vazia, retorna o layout baseado em regras.

#### ~~B6 — URL injection no Google Maps~~ ✅ CORRIGIDO (+ substituído)
Google Maps foi substituído por Nominatim (gratuito). O Nominatim usa `params=` no `requests.get()`.

#### ~~B7 — `print` debug antes da docstring~~ ✅ CORRIGIDO
`print()` removido de `src/services/image_generator.py`.

#### ~~B8 — Cômodos sem posição retornam com `x=0, y=0`~~ ✅ CORRIGIDO
`src/generators/rule_based_generator.py` filtra cômodos não posicionados antes de retornar.

#### ~~B9 — `HTTPException` no serviço, não na rota~~ ✅ CORRIGIDO
`terrain_analyzer.py` e `image_generator.py` agora lançam `RuntimeError`. A tradução para HTTP ocorre em `routes.py`.

#### ~~B10 — `get_dimensions()` fora de lugar (código morto)~~ ✅ CORRIGIDO
Classmethod removido de `src/core/models.py`.

#### ~~B11 — `save_dynamic_house_plan` aceita `None` silenciosamente~~ ✅ CORRIGIDO (arquivo removido)
`src/main.py` (script legado) foi removido. O ponto de entrada é `src/api/main.py`.

#### ~~B12 — Race condition no contador de arquivos~~ ✅ CORRIGIDO
`src/utils/output_manager.py` usa `threading.Lock()` ao redor da leitura e escrita do contador.

---

### Frontend

#### ~~F1 — XSS via `dangerouslySetInnerHTML`~~ ✅ CORRIGIDO
`DOMPurify.sanitize()` aplicado em `HousePlanForm.tsx` e `HousePlanPreview.tsx`.

#### ~~F2 — Estado stale no `handleMoreInfo`~~ ✅ CORRIGIDO
`newTerrainData` usado diretamente em vez de depender do estado React atualizado assincronamente.

#### ~~F3 — Closure stale não remove marcadores antigos~~ ✅ CORRIGIDO
`LocationPicker.tsx` reescrito com Leaflet + `useRef` para o marcador.

#### ~~F4 — Script do Google Maps carregado múltiplas vezes~~ ✅ CORRIGIDO (+ substituído)
Google Maps removido. Leaflet é importado como módulo npm, sem `<script>` dinâmico.

#### ~~F5 — Inputs numéricos produzem strings~~ ✅ CORRIGIDO
`handleInputChange` converte com `Number(value)` quando `type === 'number'`.

#### ~~F6 — URL da API hardcoded~~ ✅ CORRIGIDO
`http://localhost:8000` substituído por `import.meta.env.VITE_API_URL` (definido em `frontend/.env`).

#### ~~F7 — `localStorage` sem try/catch~~ ✅ CORRIGIDO
`JSON.parse` do localStorage envolto em `try/catch` que retorna `null` em caso de JSON inválido.

#### ~~F8 — Sem feedback de erro no geocoder~~ ✅ CORRIGIDO (+ substituído)
Google Geocoder removido. Nominatim é chamado no backend; erros são exibidos no frontend via `setError`.

---

## 2. Qualidade de Código

| # | Arquivo | Problema | Status |
|---|---------|----------|--------|
| ~~Q1~~ | `src/main.py` | ~15 imports não utilizados | ✅ Arquivo removido |
| ~~Q2~~ | `src/main.py` | `create_dynamic_house_plan()` duplicado | ✅ Arquivo removido |
| ~~Q3~~ | Todos os .py | `print()` de debug em todos os módulos | ✅ Substituído por `logging` |
| ~~Q4~~ | `frontend/src/components/HousePlanPreview.tsx` | Componente nunca importado nem usado | ✅ Deletado; botão Download SVG adicionado ao modal em `HousePlanForm.tsx` |
| ~~Q5~~ | `src/core/models.py` | `HouseSpecs.get_dimensions()` código morto | ✅ Removido |
| ~~Q6~~ | `src/generators/svg_generator.py` | Título hardcoded em `x='400'` | ✅ Usa `svg_width / 2` |
| ~~Q7~~ | `src/utils/constants.py` | Quartos 4+ sem tradução | ✅ `_TranslationsProxy` com matching dinâmico |
| ~~Q8~~ | `src/ai/gemini_client.py` | Imprime modelos disponíveis a cada requisição | ✅ Removido |
| ~~Q9~~ | `frontend/vite.config.ts` | Sem proxy Vite configurado | ✅ Proxy `/api` configurado |
| ~~Q10~~ | `src/api/main.py` | `reload=True` hardcoded | ✅ `reload=os.getenv("ENV") == "development"` |
| ~~Q11~~ | `src/ai/prompt_generator.py` | Dimensões de exemplo irreais no prompt | ✅ Corrigido para `4.5 x 5.0` |

---

## 3. Segurança

| # | Severidade | Arquivo | Problema | Status |
|---|-----------|---------|----------|--------|
| ~~S1~~ | Alta | `HousePlanForm.tsx`, `HousePlanPreview.tsx` | XSS via SVG sem sanitização | ✅ DOMPurify aplicado |
| ~~S2~~ | Alta | `routes.py` | `gemini_api_key` no payload do browser | ✅ Campo removido |
| ~~S3~~ | Média | `terrain_analyzer.py` | Endereço interpolado na URL sem encoding | ✅ Substituído por Nominatim com `params=` |
| ~~S4~~ | Média | `routes.py` | `detail=str(e)` expõe erros internos | ✅ Mensagens genéricas |
| ~~S5~~ | Média | `prompt_generator.py`, `image_generator.py` | Prompt injection via campos do usuário | ✅ Marcadores `[USER INPUT START]...[USER INPUT END]` adicionados; instrução de sistema adicionada ao prompt |
| ~~S6~~ | Baixa | `routes.py` | CORS `allow_methods=["*"]` excessivo | ✅ Restrito a `GET`, `POST` e `Content-Type` |
| ~~S7~~ | Baixa | `src/api/main.py` | `host="0.0.0.0"` em todas as interfaces | ✅ Host configurável via `HOST` env var (padrão `0.0.0.0` dev; usar `HOST=127.0.0.1` em prod) |

---

## 4. Validações Ausentes

| # | Arquivo | Problema | Status |
|---|---------|----------|--------|
| ~~V1~~ | `routes.py` | `address` sem limite de tamanho | ✅ `max_length=200` |
| ~~V2~~ | `routes.py` | Sem limite superior para dimensões | ✅ `le=500` em `terrain_width`/`terrain_height` |
| ~~V3~~ | `ai_layout_converter.py` | Sem `.get()` para campos da IA | ✅ Corrigido |
| ~~V4~~ | `ai_layout_converter.py` | Sem guard para lista vazia antes do `max()` | ✅ Corrigido |
| ~~V5~~ | `HousePlanForm.tsx` | Sem verificação de `description` não-vazia | ✅ Validação antes de chamar a API |
| ~~V6~~ | `HousePlanForm.tsx` | Sem guard para `terrain_data` vazio | ✅ Validação antes de enviar para `/generate-house-image` |
| ~~V7~~ | `output_manager.py` | `int()` sem try/catch em nome de arquivo | ✅ `try/except ValueError` adicionado |
| ~~V8~~ | `image_generator.py` | Erros da OpenAI descartados sem log | ✅ Log do corpo da resposta HTTP da OpenAI (`status_code` + `response.text`) quando disponível |

---

## 5. Sugestões de Features

| # | Feature |
|---|---------|
| FA | **Múltiplos andares** — configurar planta térrea + sobrado |
| FB | **Regenerar variação** — botão "Gerar nova variação" sem recarregar a página |
| FC | **Escala real na planta** — adicionar régua/escala no SVG (ex: `── 10m ──`) |
| FD | **Exportar como PDF** além do SVG |
| FE | **Preview do terreno no mapa** — exibir polígono do lote baseado nas dimensões informadas |
| FF | **Salvar/carregar projetos** — persistir planos no backend com ID único e URL compartilhável |
| FG | **Relatório de materiais** — estimar m² de parede, área de piso por cômodo |

---

## Resumo de Pendências

| Categoria | Total | Resolvido | Pendente |
|---|---|---|---|
| Bugs de backend (B1–B12) | 12 | 12 | 0 |
| Bugs de frontend (F1–F8) | 8 | 8 | 0 |
| Qualidade de código (Q1–Q11) | 11 | 11 | 0 |
| Segurança (S1–S7) | 7 | 7 | 0 |
| Validações ausentes (V1–V8) | 8 | 8 | 0 |
| Migração `google-generativeai` → `google-genai` | 1 | 0 | 1 |
| Chaves de API expiradas/inativas (ação manual) | — | — | verificar |
