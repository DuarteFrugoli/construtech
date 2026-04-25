# Audit Report — Construtech

Data: 22/04/2026 | Atualizado: 25/04/2026

> Todos os bugs (B1–B12, F1–F8), itens de qualidade (Q1–Q11), segurança (S1–S7) e validações (V1–V8) foram resolvidos. Este documento mantém apenas pendências ativas.

---

## Mudanças arquiteturais recentes

| # | Mudança | Motivo |
|---|---------|--------|
| A1 | **Gemini removido** — `gemini_client.py`, `prompt_generator.py`, `ai_layout_converter.py` deletados | Dependência desnecessária; gerador baseado em regras é suficiente para o MVP |
| A2 | **SVG migrado para o frontend** — backend retorna JSON `{terrain, layout[]}`; `svg_generator.py` órfão | SVG no backend impedia interatividade; React SVG nativo permite clique, drag, animações |
| A3 | **`DOMPurify` removido** — SVG construído pelo React, sem string externa | Elimina risco de XSS por design, não por sanitização |
| A4 | **Seleção de cômodos** — `FloorPlanCanvas` com `onRoomSelect`, highlight e painel de info | Base para features de edição (drag, resize) |

---

## Features pendentes

### Edição da planta

| # | Feature | Prioridade |
|---|---------|-----------|
| FE1 | **Drag para mover cômodos** — arrastar qualquer cômodo para reposicioná-lo | Alta |
| FE2 | **Redimensionar cômodos** — handles nos cantos para alterar largura/altura | Alta |
| FE3 | **Mover porta** — arrastar a porta para outra parede do mesmo cômodo | Média |
| FE4 | **Escala real na planta** — régua/escala visual (ex: `── 5m ──`) | Média |
| FE5 | **Regenerar variação** — botão "Gerar nova variação" sem recarregar a página | Baixa |

### Persistência e usuário

| # | Feature | Prioridade |
|---|---------|-----------|
| FP1 | **Salvar/carregar projetos** — PostgreSQL (Supabase) com ID único e URL compartilhável | Alta |
| FP2 | **Autenticação** — login social (Google) via Supabase Auth | Média |
| FP3 | **Exportar como PDF** além do SVG | Baixa |

### Dados externos

| # | Feature | Prioridade |
|---|---------|-----------|
| FD1 | **Plano diretor automático** — detectar zoneamento e recuos a partir da coordenada do terreno | Alta |
| FD2 | **Estimativa de custo** — CUB/m² por estado (SINDUSCON) × área construída | Alta |
| FD3 | **Preview do terreno no mapa** — exibir polígono do lote nas dimensões informadas | Média |
| FD4 | **Relatório de materiais** — estimar m² de parede, área de piso por cômodo | Baixa |

### Produto / Deploy

| # | Feature | Prioridade |
|---|---------|-----------|
| FP4 | **CORS dinâmico** — ler origins de variável de ambiente (pré-requisito para deploy) | Alta |
| FP5 | **Deploy (Railway + Vercel)** — backend no Railway, frontend na Vercel, banco no Supabase | Alta |
| FP6 | **Múltiplos andares** — configurar planta térrea + sobrado | Baixa |

