# Análise de Stack — Construtech

Data: 25/04/2026

---

## O que o produto precisa fazer

1. Usuário escolhe um **ponto no mapa** (localização real)
2. Passa as **definições da casa** (cômodos, estilo, plano diretor local)
3. Sistema gera a **planta baixa** daquele terreno
4. Sistema gera uma **visualização artística** da casa construída (fachada)
5. *(Futuro)* Estima o **custo de construção**
6. Resultado exibido em **web ou app mobile**

---

## Stack atual

| Camada | Tecnologia | Versão |
|---|---|---|
| Backend | FastAPI + Uvicorn | Python 3.12 |
| Validação | Pydantic v2 | 2.4+ |
| Frontend | React + Vite + TypeScript | React 19 |
| Estilo | Tailwind CSS | 3.x |
| Mapa | Leaflet + OpenStreetMap | 1.9.x |
| Geocoding | Nominatim (OSM) | REST |
| Elevação | Open-Elevation API | REST |
| Planta baixa | SVG gerado em Python puro | — |
| Imagem artística | DALL-E 3 (OpenAI) | REST |
| Gerador de layout | Rule-based determinístico | Python puro |
| Deploy | Nenhum (local) | — |
| Banco de dados | Nenhum | — |
| Autenticação | Nenhuma | — |

---

## Problemas de projeto (não de código)

### 1. SVG gerado em Python puro — errado desde o início

**O que está acontecendo:** O backend gera um SVG a partir de coordenadas numéricas em Python. O frontend recebe esse SVG como string e renderiza com `dangerouslySetInnerHTML`.

**Por que é um problema:**
- SVG estático não tem interatividade (zoom, clique em cômodo, arrastar parede)
- Para adicionar qualquer interação, você precisa parsear o SVG no frontend de qualquer jeito
- A geração de SVG no backend é complexa (ver `svg_generator.py`) e não escalável
- Qualquer mudança visual obriga deploy do backend

**Solução correta:** O backend devolve apenas **JSON com as coordenadas dos cômodos**. O frontend renderiza com **Canvas 2D** (via Konva.js ou Fabric.js) ou **SVG React nativo**. Interatividade, zoom e edição ficam todos no frontend — onde pertencem.

---

### 2. Nominatim para geocoding — instável em produção

**O que está acontecendo:** O `TerrainAnalyzer` usa Nominatim (OSM) para converter endereço em coordenadas.

**Por que é um problema:**
- Nominatim proíbe uso em produção com volume (Terms of Service: máximo de 1 req/s, sem uso comercial)
- Rate limit agressivo — em produção com múltiplos usuários simultâneos, vai falhar
- Qualidade de geocoding para endereços brasileiros é inferior ao Google/Mapbox

**Solução correta para produção:**
- **Geocoding:** [Geocoding API do Google](https://developers.google.com/maps/documentation/geocoding) (~$5 por 1000 req) ou **Mapbox Geocoding** (5k req grátis/mês)
- **Para MVP/desenvolvimento:** Nominatim está OK, mas documentar a limitação

---

### 3. Open-Elevation para altimetria — dados ruins no Brasil

**O que está acontecendo:** A análise de terreno usa Open-Elevation para obter dados de elevação e calcular a inclinação.

**Por que é um problema:**
- Open-Elevation usa dados SRTM de 2000 com resolução de 30m — impreciso para lotes urbanos
- Muitos pontos no Brasil retornam dados ausentes ou interpolados incorretamente
- A lógica de "inclinação do terreno" atual é uma estimativa grosseira, não um dado real do lote

**Solução correta:**
- **[Mapbox Terrain API](https://docs.mapbox.com/data/tilesets/reference/mapbox-terrain-dem-v1/)**: DEM de alta resolução, funciona bem no Brasil
- **Curto prazo:** Deixar o usuário informar manualmente a inclinação (mais honesto que um dado impreciso)

---

### 4. Plano Diretor genérico — o diferencial do produto está aqui

**O que está acontecendo:** O sistema recebe `recuo_frontal`, `taxa_ocupacao` e `coeficiente_aproveitamento` como parâmetros manuais com valores default genéricos.

**Por que é um problema:**
- O usuário médio não sabe esses valores — precisa consultar a prefeitura
- O diferencial real do produto é **saber as regras do terreno automaticamente** a partir do endereço
- Sem isso, o gerador não garante que a planta é legal

**Solução correta (ambiciosa mas viável):**
- Banco de dados de planos diretores por município (dados públicos — muitos estão em portais de prefeitura)
- Com a coordenada do terreno, identificar o zoneamento e buscar os parâmetros automaticamente
- Isso transforma o produto de "gerador de plantas" para "assistente legal de projeto"

---

### 5. Sem banco de dados — não há memória de projetos

**O que está acontecendo:** Cada geração é stateless. Não há como salvar, recuperar ou compartilhar um projeto.

**Por que é um problema:**
- Usuário perde o trabalho se fechar o browser
- Não há histórico, não há compartilhamento, não há versões
- Impossível construir features de usuário (login, favoritos, download PDF)

**Solução:**
- **PostgreSQL + SQLAlchemy** (já familiar ao ecossistema FastAPI): para projetos, usuários, histórico
- **Ou Supabase** (PostgreSQL gerenciado + Auth + Storage embutidos): ideal para MVP rápido

---

### 6. CORS fixo em localhost — indeployável

**O que está acontecendo:**
```python
allow_origins=["http://localhost:5173"]
```

**Por que é um problema:** Em produção, o frontend vai ter outro domínio. Isso bloqueia tudo.

**Solução:** Ler a lista de origins de variável de ambiente.

---

### 7. Sem deploy — o produto não existe fora da sua máquina

**O que está acontecendo:** Não há Dockerfile, nenhum serviço de hospedagem, nenhuma pipeline de CI/CD.

**Solução recomendada para MVP:**
| Camada | Serviço | Custo |
|---|---|---|
| Backend | [Railway](https://railway.app) ou [Render](https://render.com) | Grátis até 500h/mês |
| Frontend | [Vercel](https://vercel.com) | Grátis para projetos pessoais |
| Banco | Supabase ou Railway PostgreSQL | Grátis até 500MB |

---

## Comparação completa: atual vs ideal

| Aspecto | Atual | Recomendado | Motivo |
|---|---|---|---|
| **Renderização da planta** | SVG gerado no backend | JSON → Canvas/SVG no frontend (Konva.js) | Interatividade, edição, zoom |
| **Geocoding** | Nominatim (proibido em prod) | Google Geocoding / Mapbox | Confiabilidade, Brasil, ToS |
| **Elevação** | Open-Elevation (dados ruins) | Mapbox Terrain ou input manual | Precisão real |
| **Plano Diretor** | Parâmetros manuais | DB de planos diretores por município | Diferencial do produto |
| **Persistência** | Nenhuma | PostgreSQL (Supabase) | Salvar projetos, usuários |
| **Auth** | Nenhuma | Supabase Auth | Login social (Google) |
| **CORS** | Hardcoded localhost | Env var | Deploy |
| **Deploy** | Local only | Railway + Vercel | Produto real |
| **Gerador de layout** | Rule-based sequencial | Rule-based + candidatos com score | Melhor qualidade (TODO já documentado) |
| **Estimativa de custo** | Ausente | CUB/m² por estado (SINDUSCON) | Feature de valor |

---

## O que está certo e deve ser mantido

- **FastAPI + Pydantic v2**: escolha excelente. Rápido, tipado, documentação automática.
- **React + TypeScript + Vite**: stack moderna e correta para o frontend.
- **Tailwind CSS**: produtivo e consistente.
- **Leaflet**: leve, gratuito, funciona bem para seleção de ponto no mapa.
- **DALL-E 3**: a melhor opção disponível via API para visualização artística arquitetônica.
- **Rule-based generator**: mais confiável que LLM para layout. Manter e melhorar (scoring).
- **Pydantic para validação dos parâmetros do plano diretor**: correto desde o design.

---

## Roadmap sugerido (por prioridade)

### Fase 1 — Produto funcional (2–4 semanas)
1. Mover renderização da planta para o frontend (Konva.js ou SVG React)
2. Corrigir CORS para usar variável de ambiente
3. Dockerfile básico para o backend
4. Deploy: Railway (backend) + Vercel (frontend)

### Fase 2 — Produto usável (1–2 meses)
5. Supabase: banco de dados + auth (login com Google)
6. Salvar/carregar projetos
7. Substituir Nominatim por Mapbox Geocoding (ou Google)
8. Implementar scoring de candidatos no gerador de layout (TODO existente)
9. Estimativa de custo com CUB/m² do SINDUSCON

### Fase 3 — Diferencial de mercado (2–4 meses)
10. Base de planos diretores por município
11. Detecção automática de zoneamento por coordenada
12. App mobile (React Native reutilizando a lógica de frontend)
13. Exportação de planta em PDF/DWG

---

## Conclusão

O projeto tem uma **base de código sólida** — FastAPI, React/TypeScript e a lógica do gerador de layout estão bem estruturados. Os erros são de **produto**, não de código:

1. A planta deveria ser interativa (responsabilidade do frontend, não do backend)
2. O Nominatim não serve para produção
3. Sem deploy, sem banco, sem auth — o produto não chega ao usuário

O caminho mais curto para um MVP utilizável por terceiros é: **Konva.js no frontend + Supabase + deploy Railway/Vercel**. Isso pode ser feito sem reescrever o backend.
