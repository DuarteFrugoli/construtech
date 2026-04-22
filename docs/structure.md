# Análise de Estrutura do Projeto — Construtech

Data: 22/04/2026

---

## O que está bom

- Separação clara entre frontend e backend
- Backend com subpastas por responsabilidade (`ai/`, `api/`, `core/`, `generators/`, `utils/`)
- `core/models.py` centraliza todos os data models
- Frontend com componentes separados por arquivo

---

## Problemas na Raiz do Projeto

| Arquivo | Problema |
|---------|----------|
| `Test.py` | **Crítico:** contém chaves de API hardcoded. Deve ser deletado ou movido para `tests/` sem as chaves |
| `foo_house.svg` | Arquivo de teste solto na raiz. Deve ir para `src/outputs/` ou ser deletado |
| `repomix-output.xml` | Artefato de ferramenta externa — não pertence ao repositório. Adicionar ao `.gitignore` |
| `src/main.py` | Script legado standalone — confunde com o ponto de entrada real da API (`api/server.py`) |

---

## Problemas na estrutura do `src/`

A pasta `src/` mistura módulos soltos com subpastas organizadas:

```
src/                               ← estado atual
├── ai_response_converter.py       ← deveria estar em generators/
├── image_generator.py             ← deveria estar em services/
├── rule_based_layout.py           ← deveria estar em generators/
├── svg_constants.py               ← deveria estar em utils/
├── svg_generator.py               ← deveria estar em generators/
├── terrain_analyzer.py            ← deveria estar em services/
├── main.py                        ← script legado, remover ou isolar
├── ai/
├── api/
├── core/
├── generators/    ← só tem house_plan_generator.py, mas a lógica real está fora
├── utils/
└── outputs/       ← pasta de dados misturada com código
```

### Estrutura ideal

```
src/                               ← estrutura proposta
├── api/
│   ├── server.py
│   └── routes.py
├── core/
│   └── models.py
├── ai/
│   ├── model_config.py
│   └── prompt_generator.py
├── generators/
│   ├── house_plan_generator.py
│   ├── rule_based_layout.py       ← mover de src/
│   ├── ai_response_converter.py   ← mover de src/
│   └── svg_generator.py           ← mover de src/
├── services/
│   ├── terrain_analyzer.py        ← mover de src/
│   └── image_generator.py         ← mover de src/
└── utils/
    ├── file_manager.py
    └── svg_constants.py           ← mover de src/
```

---

## Nomes de Arquivos

| Arquivo atual | Sugestão | Motivo |
|---|---|---|
| `Test.py` | `tests/test_api.py` | PEP8: minúsculo; mover para pasta `tests/` |
| `rule_based_layout.py` | `rule_based_generator.py` | Consistência com `house_plan_generator.py` |
| `ai_response_converter.py` | `ai_layout_converter.py` | Mais descritivo — deixa claro que converte layout, não resposta genérica |
| `svg_constants.py` | `constants.py` (dentro de `utils/`) | Prefixo `svg_` redundante se estiver dentro de `utils/` |
| `model_config.py` | `gemini_client.py` | Mais claro sobre o que inicializa |
| `server.py` | `main.py` (dentro de `api/`) | Convenção padrão FastAPI/Uvicorn |
| `file_manager.py` | `output_manager.py` | Mais descritivo sobre o que gerencia |

---

## `outputs/` dentro de `src/`

Pasta de saída de dados não deve estar dentro do pacote Python. Mistura código com artefatos gerados, complica `.gitignore` e importações. O ideal é mover para a raiz:

```
construtech/
├── src/
├── frontend/
├── outputs/    ← raiz do projeto
└── docs/
```

---

## Resumo

| Categoria | Status |
|---|---|
| Separação frontend/backend | Boa |
| Subpastas por responsabilidade | Incompleta — vários módulos soltos em `src/` |
| Nomenclatura de arquivos | Inconsistente em alguns casos |
| Arquivos desnecessários na raiz | `Test.py`, `foo_house.svg`, `repomix-output.xml` |
| `Test.py` com chaves de API hardcoded | Crítico |
| `outputs/` dentro do pacote Python | Deve ficar na raiz |
