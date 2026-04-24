# Como Rodar e Parar os Servidores

Data: 23/04/2026

---

## Objetivo

Este guia serve para subir e parar o backend e o frontend localmente sem precisar pedir ajuda para tarefas operacionais simples.

---

## Resumo rápido

- Backend: FastAPI em `http://localhost:8000`
- Frontend: Vite em `http://localhost:5173`
- Para parar qualquer servidor iniciado no terminal: `Ctrl + C`

---

## Ambiente Python recomendado

O ambiente virtual padrão do projeto é:

- `venv/`

Use esse ambiente como padrão para evitar erro de dependência faltando, como `ModuleNotFoundError: No module named 'uvicorn'`.

---

## Subir o backend

Abra um terminal PowerShell na raiz do projeto:

```powershell
cd "C:\Users\Pedro Frugoli\Desktop\pessoal\vscode\Construtech"
& ".\venv\Scripts\python.exe" src/api/main.py
```

Quando der certo, a saída deve ficar parecida com esta:

```text
INFO:     Started server process [...]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Backend disponível em:

- `http://localhost:8000`

---

## Parar o backend

No mesmo terminal onde ele foi iniciado, pressione:

```text
Ctrl + C
```

Se o terminal estiver preso ou perdido no VS Code:

- abra a aba de terminal correspondente
- clique no ícone de lixeira para encerrar a sessão

---

## Subir o frontend

Abra outro terminal PowerShell e rode:

```powershell
cd "C:\Users\Pedro Frugoli\Desktop\pessoal\vscode\Construtech\frontend"
npm run dev
```

Quando der certo, a saída deve incluir algo assim:

```text
VITE v6.x.x ready
Local: http://localhost:5173/
```

Frontend disponível em:

- `http://localhost:5173`

---

## Parar o frontend

No terminal do Vite, pressione:

```text
Ctrl + C
```

Se necessário, também pode encerrar o terminal pela interface do VS Code.

---

## Fluxo recomendado para testar o sistema

1. Abra um terminal na raiz e suba o backend.
2. Abra um segundo terminal em `frontend/` e suba o frontend.
3. Acesse `http://localhost:5173` no navegador.
4. Faça os testes.
5. Quando terminar, volte em cada terminal e pressione `Ctrl + C`.

---

## Problemas comuns

### 1. `uvicorn` ou outra dependência não foi encontrada

Você provavelmente usou o ambiente errado.

Use o Python do `venv`:

```powershell
& ".\venv\Scripts\python.exe" src/api/main.py
```

### 2. O frontend sobe, mas não consegue falar com a API

Verifique se o backend está ativo em `http://localhost:8000`.

### 3. A porta já está em uso

Isso normalmente significa que já existe outro servidor rodando.

Faça um destes:

- volte no terminal antigo e use `Ctrl + C`
- feche o terminal antigo no VS Code
- identifique e encerre o processo que está ocupando a porta

---

## Comandos mínimos

Backend:

```powershell
cd "C:\Users\Pedro Frugoli\Desktop\pessoal\vscode\Construtech"
& ".\venv\Scripts\python.exe" src/api/main.py
```

Frontend:

```powershell
cd "C:\Users\Pedro Frugoli\Desktop\pessoal\vscode\Construtech\frontend"
npm run dev
```

Parar ambos:

```text
Ctrl + C
```