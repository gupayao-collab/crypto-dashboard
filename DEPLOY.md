# Deploy do Dashboard no iPhone

Guia passo a passo para colocar online, gratuito, com a mesma cara da versão PC.

---

## Arquitetura

```
PC (continua igual ao que ja era):
  iniciar_dashboard.bat -> coletores + servidor.py + crypto_dashboard.html
  HTML detecta localhost -> carrega dados.json/portfolio.json locais

iPhone (novo):
  GitHub Pages [crypto_dashboard.html] -> Render Backend Python -> Binance
  HTML detecta github.io -> chama backend remoto
```

**Codebase unica:** `binance_data.py` e o mesmo modulo usado pelos collectors locais e pelo backend Flask. Qualquer ajuste vale para os dois ambientes.

---

## Etapa 1 — Confirmar a API Key da Binance

1. Acesse https://www.binance.com/en/my/settings/api-management
2. Na key que voce vai usar, clique em **Edit restrictions**
3. Confirme:
   - ✅ **Enable Reading** marcado
   - ❌ **Enable Spot & Margin Trading** desmarcado
   - ❌ **Enable Withdrawals** desmarcado
4. Anote API Key + Secret num bloco de notas temporario

> ⚠️ Mesmo que vaze, uma key so de leitura nao consegue tirar dinheiro. Apague o bloco de notas no fim do deploy.

---

## Etapa 2 — Subir o codigo para um repo publico

A pasta `Dashboard/` inteira vai pro GitHub. O `.gitignore` ja exclui credenciais, `.env`, `dados.json` e `portfolio.json`.

```bash
cd "C:\Users\gusta\Desktop\CLAUDE\PROGRAMAS\Monitor Cripto Binance\Dashboard"

git init
git add .
git commit -m "Dashboard com suporte PC e iPhone (codebase unica)"

# Repo publico no GitHub
gh repo create crypto-dashboard --public --source=. --remote=origin --push
```

---

## Etapa 3 — Deploy do backend no Render.com

1. Acesse https://render.com → criar conta com GitHub
2. **New** → **Web Service** → conectar ao repo `crypto-dashboard`
3. Configure:
   - **Name:** `crypto-dash-gustavo`
   - **Region:** Oregon
   - **Branch:** `main`
   - **Root Directory:** *(deixe em branco)*
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r backend/requirements.txt`
   - **Start Command:** `gunicorn --chdir backend app:app --timeout 60`
   - **Instance Type:** **Free**

4. Em **Environment Variables**, adicione:

   | Key | Value |
   |---|---|
   | `BINANCE_API_KEY` | (sua API Key) |
   | `BINANCE_SECRET` | (sua Secret) |
   | `DEPOSITO_INICIAL` | `3000` |
   | `ALLOWED_ORIGIN` | `https://gupayao-collab.github.io` |

5. **Create Web Service** → espera build (~3 min)

6. Quando subir, copie a URL: `https://crypto-dash-gustavo.onrender.com`

7. Testar: `https://crypto-dash-gustavo.onrender.com/health` → deve retornar `{"status":"ok"}`

8. Testar dados: `https://crypto-dash-gustavo.onrender.com/dados.json` → JSON com precos
9. Testar portfolio: `https://crypto-dash-gustavo.onrender.com/portfolio.json` → JSON com saldo

---

## Etapa 4 — Ajustar URL do backend no HTML (se necessario)

Abrir [crypto_dashboard.html](crypto_dashboard.html), procurar:

```js
var BACKEND_URL = 'https://crypto-dash-gustavo.onrender.com';
```

Se o nome do servico no Render foi diferente, ajustar. Commit + push:

```bash
git add crypto_dashboard.html
git commit -m "ajusta URL do backend"
git push
```

---

## Etapa 5 — Habilitar GitHub Pages

1. github.com/gupayao-collab/crypto-dashboard → **Settings** → **Pages**
2. **Source:** Deploy from a branch
3. **Branch:** `main` / `(root)` → **Save**
4. Aguardar ~2 min
5. URL final: `https://gupayao-collab.github.io/crypto-dashboard/crypto_dashboard.html`

---

## Etapa 6 — Adicionar a Tela de Inicio no iPhone

1. Abrir a URL no **Safari**
2. Esperar ~30s na primeira carga (Render acordando)
3. Toque em **Compartilhar** (icone do quadrado com seta)
4. **Adicionar a Tela de Inicio**
5. Confirmar → vira app standalone, sem barra do Safari

---

## Etapa 7 — Como ficam as atualizacoes futuras

A regra de ouro: **so edite UM lugar**.

| Mudanca | Editar | Resultado |
|---|---|---|
| Cor, layout, novo grafico | `crypto_dashboard.html` | Vale pra PC e iPhone |
| Logica de coleta de dados | `binance_data.py` | Vale pra PC e iPhone |
| Comportamento do menu PC | `dashboard_collector.py` / `portfolio_collector.py` | So PC |
| Endpoints / cache do backend | `backend/app.py` | So iPhone |
| Heartbeat / fechar com browser | `servidor.py` | So PC |

Depois de editar:
- Mudou `crypto_dashboard.html`, `binance_data.py` ou `backend/`:
  ```bash
  git add . && git commit -m "descreva" && git push
  ```
  GitHub Pages e Render fazem deploy automatico.
- Mudou so `dashboard_collector.py`, `portfolio_collector.py`, `servidor.py` ou `iniciar_dashboard.bat`:
  Nao precisa push — afeta so o PC.

---

## Teste local do backend (antes de subir pro Render)

```bash
cd "PROGRAMAS\Monitor Cripto Binance\Dashboard"

# Criar .env local na pasta backend
copy backend\.env.example backend\.env
# Editar backend\.env com as credenciais reais (NAO vai pro Git)

# Instalar dependencias
pip install -r backend\requirements.txt

# Rodar
cd backend
python app.py
```

Em outro terminal:
```bash
curl http://localhost:5000/dados.json
curl http://localhost:5000/portfolio.json
```

Se retornar JSON valido nos dois, esta pronto pra deploy.

---

## Custos

| Servico | Custo | Limite |
|---|---|---|
| GitHub Pages | Gratis | 100GB banda/mes |
| Render Free | Gratis | 750h/mes (1 instancia 24/7), dorme apos 15min sem trafego |
| Binance API | Gratis | 1200 req/min |

Auto-refresh do dashboard a cada 60s = ~1440 req/dia. Bem dentro do limite.

---

## Em caso de problema

| Sintoma | Possivel causa | Solucao |
|---|---|---|
| iPhone mostra "ERRO: HTTP 502" | Backend offline ou cold start | Esperar 30s e atualizar |
| "ERRO: Credenciais nao configuradas" | Env vars faltando no Render | Verificar painel Environment |
| "ERRO: HTTP 401" | API Key invalida | Recriar no Binance |
| Portfolio vazio | Carteira sem moedas com par USDT | Comprar algo, esperar 30s (cache) |

Para vazamento de key: deletar no Binance, criar nova, atualizar env vars no Render, fazer Manual Deploy.
