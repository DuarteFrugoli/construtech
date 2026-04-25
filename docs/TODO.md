# TODO — Refatoração de Longo Prazo do Gerador de Layout

## Problema Central

O `RuleBasedLayoutGenerator` atual usa um algoritmo **sequencial determinístico**: posiciona cômodos em ordem fixa (pack_rows da esquerda para direita), sem nenhuma avaliação de qualidade do resultado. Isso impede arranjos melhores mesmo quando o espaço disponível permitiria.

Exemplo concreto: num terreno 10×18 com 1 quarto + 1 suíte + 1 banheiro social, o banheiro social poderia ficar no canto da zona social (embaixo da cozinha, acima do corredor), deixando a casa mais quadrada e aproveitando o espaço — mas o algoritmo atual não avalia essa possibilidade.

---

## Solução Recomendada: Layout por Candidatos com Pontuação

### Ideia

Em vez de um único resultado, gerar **N configurações candidatas** e manter a com maior pontuação.

```
para cada candidato:
    1. Sortear uma permutação da ordem dos cômodos
    2. Sortear orientações (portrait/landscape) por cômodo
    3. Executar o pack (lógica atual, simplificada)
    4. Pontuar o resultado
retornar o melhor candidato
```

### Função de Pontuação

Critérios a ponderar:

| Critério | Peso sugerido |
|---|---|
| % do terreno utilizado | alto |
| Nenhum cômodo sem porta | obrigatório (score = 0 se falhar) |
| Proporção dos cômodos (ratio w/h ≤ 2.5) | médio |
| Banheiro de suíte adjacente ao quarto | alto |
| Banheiro social adjacente ao corredor | alto |
| Cozinha não no caminho entre sala e quartos | médio |
| Casa mais "quadrada" (bounding box compacto) | baixo |

### Escopo de Mudanças

- `rule_based_generator.py`: adicionar loop de candidatos + `_score_layout(rooms) -> float`
- Manter as regras atuais de porta (`should_add_door`) — funcionam bem
- Manter a separação de zonas (social / corredor / privada / serviço) — é uma boa estrutura
- O `pack_rows` / `pack_cols` atual pode ser reutilizado dentro de cada candidato

### O que NÃO fazer

- Não usar backtracking completo (explode em complexidade)
- Não usar algoritmo genético (overkill para o tamanho do problema)
- 50–200 candidatos já dão resultados bons com custo mínimo (< 100ms)

---

## Problema Secundário: Dimensionamento por Zona

Os tamanhos atuais dos cômodos (`_ROOM_AREA_RANGES` + `_size_bias`) são independentes do terreno. Numa refatoração maior, o correto seria:

- Calcular **quanto espaço a zona social tem disponível** (altura para portrait, largura para landscape)
- Dimensionar sala e cozinha para **preencher essa zona proporcionalmente**, não por área absoluta
- Idem para zona privada

Isso resolve de vez o problema de "casa pequena em terreno grande" sem gambiarras de scale_factor.

---

## Status

- [x] Lógica de portas funcional
- [x] Banheiro de suíte ao lado do quarto (portrait e landscape)
- [x] Banheiro social com corredor
- [x] Sala + cozinha lado a lado (portrait)
- [x] Nomenclatura de suítes correta
- [ ] **Geração por candidatos com pontuação** ← próximo grande passo
- [ ] Dimensionamento por zona em vez de área global
