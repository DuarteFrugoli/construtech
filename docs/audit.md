# Audit Report — Construtech

Data: 22/04/2026

---

## 1. Bugs / Erros de Lógica

### Backend

#### B1 — `gemini_api_key` enviada pelo browser
**Arquivo:** `src/api/routes.py`  
`HousePlanRequest` inclui um campo `gemini_api_key` que trafega do browser → servidor. Chaves de API nunca devem vir do cliente.

#### B2 — `initialize_model()` executada a cada requisição
**Arquivo:** `src/ai/model_config.py`  
A cada chamada ao `/generate-house-plan`, o código enumera todos os modelos Gemini (`genai.list_models()`) e faz uma chamada de teste (`"Hello"`). Desperdiça cota e adiciona ~2s de latência por requisição. O modelo deve ser inicializado uma vez na startup (singleton).

#### B3 — I/O bloqueante em handlers `async`
**Arquivo:** `src/api/routes.py`  
`terrain_analyzer` e `image_generator` usam `requests` (síncrono) dentro de handlers `async def`. Isso bloqueia o event loop inteiro do FastAPI. Fix: usar `httpx` com `await` ou `asyncio.run_in_executor`.

#### B4 — `KeyError` em resposta malformada da IA
**Arquivo:** `src/ai_response_converter.py`  
Acessa `room_data["name"]`, `room_data["width"]`, `room_data["height"]` sem `.get()` ou verificação de existência. Se a IA omitir qualquer campo, o servidor crasha com `KeyError`.

#### B5 — `max()` em lista vazia
**Arquivo:** `src/ai_response_converter.py`  
```python
max_room_width = max(room.width for room in rooms)
```
Se a lista de cômodos filtrados estiver vazia, `max()` lança `ValueError: max() arg is an empty sequence`. Adicionar guard: `if not rooms: return rule_generator.generate_layout(specs)`.

#### B6 — URL injection no Google Maps
**Arquivo:** `src/terrain_analyzer.py`  
`address` é interpolado diretamente na URL sem encoding:
```python
url = f"...?address={address}&key={self.google_api_key}"
```
Um endereço contendo `&`, `=` ou `#` corrompe a query string. Fix: usar `params={"address": address, "key": ...}` no `requests.get()`.

#### B7 — `print` debug antes da docstring
**Arquivo:** `src/image_generator.py`  
```python
def generate_house_image(self, description, terrain_data):
    print(terrain_data, description)
    """..."""
```
O `print()` executa antes da docstring — a string literal vira expressão morta. Além disso, dados da requisição vazam para stdout em produção.

#### B8 — Cômodos sem posição retornam com `x=0, y=0`
**Arquivo:** `src/rule_based_layout.py`  
Se `_position_rooms` não encontra posição válida para um cômodo, ele permanece na lista de retorno com coordenadas `(0, 0)`, sobrepondo o primeiro cômodo no SVG gerado. Não há aviso nem remoção.

#### B9 — `HTTPException` no serviço, não na rota
**Arquivos:** `src/terrain_analyzer.py`, `src/image_generator.py`  
Classes de serviço importam e lançam `HTTPException` do FastAPI diretamente. Erros de domínio nunca devem depender do framework web. Devem lançar exceções próprias e a tradução para HTTP deve ocorrer nas rotas.

#### B10 — `get_dimensions()` fora de lugar (código morto)
**Arquivo:** `src/core/models.py`  
Classmethod em `HouseSpecs` com docstring dizendo "door dimensions". Pertence à classe `Door`, nunca é chamado em nenhum lugar do código.

#### B11 — `save_dynamic_house_plan` aceita `None` silenciosamente
**Arquivo:** `src/main.py`  
Parâmetros com default `None` são passados sem validação ao `HouseSpecs`, que crasha na primeira operação aritmética (`.built_area = None * float`).

#### B12 — Race condition no contador de arquivos
**Arquivo:** `src/utils/file_manager.py`  
`get_next_house_number()` lê o filesystem e retorna um número; o caller cria o arquivo depois. Duas requisições simultâneas podem receber o mesmo número, e uma sobrescreve a outra.

---

### Frontend

#### F1 — XSS via `dangerouslySetInnerHTML`
**Arquivos:** `frontend/src/components/HousePlanForm.tsx`, `HousePlanPreview.tsx`  
O SVG recebido do backend é injetado como HTML bruto. SVG suporta `<script>` e event handlers inline (`onload`, `onclick`). Um backend comprometido ou ataque MITM pode injetar JavaScript arbitrário. Fix: sanitizar com [DOMPurify](https://github.com/cure53/DOMPurify).

#### F2 — Estado stale no `handleMoreInfo`
**Arquivo:** `frontend/src/components/HousePlanForm.tsx`  
```typescript
const newTerrainData = await terrainResponse.json();
setTerrainData(newTerrainData); // atualização assíncrona de estado
// terrainData ainda é null na próxima linha!
body: JSON.stringify({ terrain_data: terrainData || JSON.parse(...) })
```
Fix: usar `newTerrainData` diretamente em vez de depender do estado atualizado.

#### F3 — Closure stale não remove marcadores antigos
**Arquivo:** `frontend/src/components/LocationPicker.tsx`  
O `if (marker)` dentro do click handler captura `marker = null` do momento do `useEffect`. `setMarker` atualiza o estado React mas a closure nunca enxerga a atualização. Cada clique no mapa adiciona um novo marcador sem remover o anterior. Fix: usar `useRef` para o marcador.

#### F4 — Script do Google Maps carregado múltiplas vezes
**Arquivo:** `frontend/src/components/LocationPicker.tsx`  
O `<script>` é adicionado ao `<head>` em cada montagem do componente. Remontagens causam múltiplas inicializações simultâneas do Maps API.

#### F5 — Inputs numéricos produzem strings
**Arquivo:** `frontend/src/components/HousePlanForm.tsx`  
`e.target.value` para `type="number"` é sempre `string`. O estado inicia como `number` mas vira `string` após a primeira edição, violando a tipagem do `HousePlanFormData`. Fix: converter com `Number()` ou `parseFloat()` no handler.

#### F6 — URL da API hardcoded
**Arquivo:** `frontend/src/components/HousePlanForm.tsx`  
`http://localhost:8000` aparece três vezes no código. Deve usar `import.meta.env.VITE_API_URL`.

#### F7 — `localStorage` sem try/catch
**Arquivo:** `frontend/src/components/HousePlanForm.tsx`  
```typescript
JSON.parse(localStorage.getItem('terrainData') || '{}')
```
Se o valor armazenado for JSON malformado, `JSON.parse` lança `SyntaxError` não capturado.

#### F8 — Sem feedback de erro no geocoder
**Arquivo:** `frontend/src/components/LocationPicker.tsx`  
```typescript
geocoder.geocode(..., (results, status) => {
  if (status === 'OK' && results[0]) {
    onLocationSelect(results[0].formatted_address);
  }
  // else: falha silenciosa, sem feedback ao usuário
});
```

---

## 2. Qualidade de Código

| # | Arquivo | Problema |
|---|---------|----------|
| Q1 | `src/main.py` | ~15 imports não utilizados (`json`, `math`, `time`, `logging`, `datetime`, `genai`, `SVGHousePlanGenerator`, `RuleBasedLayoutGenerator`, etc.) |
| Q2 | `src/main.py` | `create_dynamic_house_plan()` duplica exatamente o que `routes.py` já faz. Código morto em produção |
| Q3 | Todos os .py | Extensos `print()` de debug em todos os módulos. Devem ser substituídos por `logging` com níveis configuráveis |
| Q4 | `frontend/src/components/HousePlanPreview.tsx` | Componente nunca importado nem usado em nenhum lugar. Código morto |
| Q5 | `src/core/models.py` | `HouseSpecs.get_dimensions()` nunca é chamado. Código morto com descrição errada |
| Q6 | `src/svg_generator.py` | Título hardcoded em `x='400'` independente da largura real do SVG. Fica fora do centro em terrenos estreitos |
| Q7 | `src/svg_constants.py` | `TRANSLATIONS` mapeia `"Bedroom 2"` e `"Bedroom 3"` explicitamente, mas quartos são nomeados dinamicamente. Quartos 4+ ficam sem tradução |
| Q8 | `src/ai/model_config.py` | Imprime todos os modelos Gemini disponíveis a cada requisição. Ruidoso e desnecessário |
| Q9 | `frontend/vite.config.ts` | Sem proxy Vite configurado para o backend. URLs ficam hardcoded nos componentes |
| Q10 | `src/api/server.py` | `reload=True` hardcoded. Deve ser `reload=os.getenv("ENV") == "development"` |
| Q11 | `src/ai/prompt_generator.py` | O JSON de exemplo no prompt mostra `"width": 40.0, "height": 50.0`, contradizendo a guideline "3.5 a 6 metros" acima. Confunde o modelo |

---

## 3. Segurança

| # | Severidade | Arquivo | Problema |
|---|-----------|---------|----------|
| S1 | **Alta** | `HousePlanForm.tsx`, `HousePlanPreview.tsx` | SVG renderizado com `dangerouslySetInnerHTML` sem sanitização. Risco de XSS |
| S2 | **Alta** | `routes.py` | Campo `gemini_api_key` em `HousePlanRequest` expõe chave via DevTools do browser |
| S3 | **Média** | `terrain_analyzer.py` | Parâmetro `address` interpolado na URL sem encoding. Risco de corrupção de query string |
| S4 | **Média** | `routes.py` | `raise HTTPException(detail=str(e))` expõe mensagens de erro internas (paths, detalhes de API) para o cliente |
| S5 | **Média** | `prompt_generator.py`, `image_generator.py` | Valores controlados pelo usuário (`style`, `description`, `address`) interpolados diretamente nos prompts de IA. Risco de prompt injection |
| S6 | **Baixa** | `routes.py` | `allow_methods=["*"]` e `allow_headers=["*"]` no CORS são excessivamente permissivos |
| S7 | **Baixa** | `server.py` | `host="0.0.0.0"` expõe em todas as interfaces. Deve ficar atrás de um reverse proxy em produção |

---

## 4. Validações Ausentes

| # | Arquivo | Problema |
|---|---------|----------|
| V1 | `routes.py` | Parâmetro `address` sem limite de tamanho nem validação de formato |
| V2 | `routes.py` | Sem limite superior para `terrain_width`/`terrain_height`. Terrenos enormes travam o algoritmo de posicionamento |
| V3 | `ai_response_converter.py` | Sem `.get()` para `"name"`, `"width"`, `"height"` — resposta incompleta da IA crasha o servidor |
| V4 | `ai_response_converter.py` | Sem guard para lista de cômodos vazia antes do `max()` |
| V5 | `HousePlanForm.tsx` | Sem verificação de `description` não-vazia antes de chamar a geração de imagem |
| V6 | `HousePlanForm.tsx` | Sem guard para `terrain_data` vazio ao enviar para `/generate-house-image`. Backend recebe `{}` e crasha em `terrain_data["slope"]` |
| V7 | `file_manager.py` | `int(f.replace(...))` pode lançar `ValueError` se um arquivo no diretório `outputs/` tiver sufixo não-inteiro |
| V8 | `image_generator.py` | Detalhes de erro da OpenAI (rate limit, etc.) são descartados em favor de mensagem genérica — invisível para operadores |

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

## 6. Status das Correções Aplicadas

| Problema | Status |
|---------|--------|
| Chaves de API hardcoded (`routes.py`, `model_config.py`, `LocationPicker.tsx`) | Corrigido |
| `has_kitchen` definido duas vezes em `models.py` | Corrigido |
| `CODE_VERSION` duplicado entre `main.py` e `file_manager.py` | Corrigido |
| `.env` adicionado ao `.gitignore` | Corrigido |
| `python-dotenv` adicionado ao `requirements.txt` | Corrigido |
| Demais bugs listados acima | Pendente |
