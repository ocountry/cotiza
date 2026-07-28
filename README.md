# Vigil — Price Tracking Platform

**Vigil** es una plataforma de monitoreo de precios. Los usuarios ingresan URLs de productos, el sistema extrae la información (precio, título, descripción, imagen) mediante scraping o IA, y notifica cambios de precio vía webhook.

---

## ✨ Funcionalidades

- **Seguimiento de productos**: Agrega cualquier URL de producto y Vigil extrae precio, título, descripción e imagen automáticamente
- **Extracción inteligente**: Dos métodos — scraping (BeautifulSoup + Firecrawl) o extracción por IA (OpenAI/Anthropic/local)
- **Soporte multi-sitio**: Sodimac, Falabella, MercadoLibre, Paris, Amazon y cualquier tienda online
- **Notificaciones**: Webhook configurable para alertar cuando cambia un precio
- **Historial de precios**: Registro completo de todos los cambios con gráficos
- **Verificación periódica**: Cron automático configurable (cada N horas)
- **Autenticación Google**: Login con Google OAuth
- **Diseño Swiss Luxury**: Interfaz moderna con tema claro/oscuro

---

## 🏗️ Arquitectura

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Browser   │────▶│  nginx :80   │────▶│  FastAPI    │
│  (React)    │     │  (frontend)  │     │  :8001      │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                 │
                                                 ▼
                                          ┌─────────────┐
                                          │   MongoDB   │
                                          │  :27017     │
                                          └─────────────┘
```

### Componentes

| Componente | Tecnología | Puerto |
|---|---|---|
| **Frontend** | React 19 + CRA + CRACO + Tailwind CSS + Shadcn UI | 80 (nginx) |
| **Backend** | FastAPI + Python 3.11 | 8001 |
| **Base de datos** | MongoDB 7 | 27017 |
| **Proxy** | nginx (frontend → backend) | — |

---

## 🚀 Tecnologías

### Backend
- **FastAPI** — Framework web asíncrono
- **Pydantic** — Validación de datos y modelos
- **Motor** — Driver asíncrono de MongoDB
- **BeautifulSoup** — Scraping HTML
- **Firecrawl** — Scraping de sitios protegidos (anti-bot)
- **httpx** — Cliente HTTP asíncrono
- **APScheduler** — Cron de verificación periódica

### Frontend
- **React 19** — UI
- **React Router 7** — Routing SPA
- **CRACO** — Config overlay sobre CRA
- **Tailwind CSS 3** — Estilos utilitarios
- **Shadcn UI** — Componentes (Radix primitives)
- **Recharts** — Gráficos de historial de precios
- **Sonner** — Toast notifications

---

## 📦 Inicio Rápido (Docker)

```bash
# 1. Clonar
git clone https://github.com/ocountry/cotiza.git
cd cotiza

# 2. Configurar variables de entorno
cp .env.docker .env
# Editar .env con tus credenciales de Google OAuth
# GOOGLE_CLIENT_ID y GOOGLE_CLIENT_SECRET son REQUERIDOS

# 3. Iniciar
docker compose up -d

# 4. Abrir http://localhost
```

### Configurar Google OAuth

1. Ir a [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Crear OAuth 2.0 Client ID (Web application)
3. Agregar **Authorized redirect URI**:
   - Docker local: `http://localhost/api/auth/google/callback`
   - Producción: `https://tudominio.com/api/auth/google/callback`

---

## 💻 Desarrollo Local

### Requisitos
- Python 3.10+
- Node.js 18+
- MongoDB 6.0+
- Yarn 1.x

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Editar .env con tus credenciales
uvicorn server:app --reload --port 8001
```

### Frontend

```bash
cd frontend
yarn install
cp .env.example .env
# REACT_APP_BACKEND_URL=http://localhost:8001
yarn start
```

### Tests

```bash
python3 backend_test.py --base-url http://localhost:8001/api
```

---

## 🖥️ Despliegue con CloudPanel

Si tienes CloudPanel en tu servidor:

```bash
# 1. Configurar
cp .env.docker .env
# Editar VIGIL_PORT si 3000 está ocupado

# 2. Iniciar Vigil
docker compose up -d
# Vigil escucha en 127.0.0.1:3000 (no expuesto al exterior)

# 3. CloudPanel → Sites → Add Site → vigil.tudominio.com
#    Settings → Reverse Proxy → http://127.0.0.1:3000
#    ✅ SSL automático
```

---

## ⚙️ Variables de Entorno

### Backend

| Variable | Requerido | Default | Descripción |
|---|---|---|---|
| `MONGO_URL` | Sí | — | URI de MongoDB |
| `DB_NAME` | No | `vigil_db` | Nombre de base de datos |
| `GOOGLE_CLIENT_ID` | **Sí** | — | Client ID de Google OAuth |
| `GOOGLE_CLIENT_SECRET` | **Sí** | — | Client Secret de Google OAuth |
| `GOOGLE_REDIRECT_URI` | No | `http://localhost:8001/api/auth/google/callback` | URI de callback |
| `FRONTEND_URL` | No | `http://localhost:3000` | URL del frontend (CORS + redirects) |
| `FIRECRAWL_MODE` | No | `cloud` | `cloud` o `selfhosted` |
| `FIRECRAWL_API_KEY` | No | — | API key de Firecrawl |
| `FIRECRAWL_SELFHOSTED_URL` | No | — | URL de Firecrawl self-hosted |
| `LLM_API_KEY` | No | — | API key para extracción por IA |
| `LLM_PROVIDER` | No | `openai` | Proveedor LLM |
| `LLM_MODEL` | No | `gpt-4o-mini` | Modelo LLM |
| `LLM_API_URL` | No | `https://api.openai.com/v1/chat/completions` | URL de API LLM |
| `NOTIFICATION_WEBHOOK_URL` | No | — | Webhook para notificaciones |
| `PRICE_CHECK_INTERVAL_HOURS` | No | `12` | Intervalo de verificación |

### Docker

| Variable | Default | Descripción |
|---|---|---|
| `VIGIL_PORT` | `3000` | Puerto del frontend (no usar 80 si hay CloudPanel) |

### Frontend

| Variable | Descripción |
|---|---|
| `REACT_APP_BACKEND_URL` | URL del backend (ej: `http://localhost:8001`) |

---

## 📡 API Endpoints

### Autenticación

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/auth/google/login` | Inicia flujo Google OAuth |
| `GET` | `/api/auth/google/callback` | Callback OAuth de Google |
| `GET` | `/api/auth/me` | Usuario actual |
| `POST` | `/api/auth/logout` | Cerrar sesión |
| `PUT` | `/api/auth/profile` | Actualizar canales de notificación |

### Items (requieren autenticación)

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/items` | Crear item (con extracción automática) |
| `GET` | `/api/items` | Listar items del usuario |
| `GET` | `/api/items/{id}` | Detalle de item |
| `PUT` | `/api/items/{id}` | Actualizar item |
| `DELETE` | `/api/items/{id}` | Eliminar item + historial |
| `POST` | `/api/items/{id}/check` | Verificar precio manualmente |
| `GET` | `/api/items/{id}/history` | Historial de precios |

### Utilidades

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/preview` | Vista previa de extracción |
| `GET` | `/api/cron/status` | Estado del scheduler |
| `POST` | `/api/cron/trigger` | Disparar verificación manual |

---

## 📖 Ejemplos de Uso

### Agregar un producto (API)

```bash
curl -X POST http://localhost:8001/api/items \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.sodimac.cl/sodimac-cl/producto/123456",
    "extraction_method": "scraping"
  }'
```

### Verificar precio manualmente

```bash
curl -X POST http://localhost:8001/api/items/{item_id}/check \
  -H "Authorization: Bearer <token>"
```

### Obtener historial de precios

```bash
curl http://localhost:8001/api/items/{item_id}/history \
  -H "Authorization: Bearer <token>"
```

### Vista previa de extracción (sin crear item)

```bash
curl -X POST http://localhost:8001/api/preview \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.amazon.com/dp/B0EXAMPLE",
    "method": "ai"
  }'
```

### Verificar estado del cron

```bash
curl http://localhost:8001/api/cron/status
```

---

## 📁 Estructura del Proyecto

```
cotiza/
├── backend/
│   ├── server.py              # Entry point FastAPI
│   ├── config.py              # Config: env vars, MongoDB, logging
│   ├── models.py              # Modelos Pydantic
│   ├── auth.py                # Google OAuth, sesiones
│   ├── scraping.py            # Scraping: BeautifulSoup, Firecrawl
│   ├── llm.py                 # Extracción por IA (OpenAI-compatible)
│   ├── notifications.py       # Webhook de notificaciones
│   ├── cron.py                # Scheduler de verificación periódica
│   ├── routes/
│   │   ├── __init__.py
│   │   └── items.py           # CRUD items, price check, preview
│   ├── Dockerfile
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.js             # Router principal (React Router v7)
│   │   ├── index.js           # Entry point
│   │   ├── index.css          # Tailwind + variables CSS
│   │   ├── lib/
│   │   │   ├── api.js         # API utility con auth token
│   │   │   └── utils.js       # cn() utility
│   │   ├── contexts/
│   │   │   ├── AuthContext.js  # Google OAuth + Bearer token
│   │   │   └── ThemeContext.js # Tema light/dark/system
│   │   ├── pages/
│   │   │   ├── LandingPage.js
│   │   │   ├── AuthCallback.js
│   │   │   ├── Dashboard.js
│   │   │   ├── AddItem.js
│   │   │   ├── ItemDetail.js
│   │   │   └── Settings.js
│   │   └── components/ui/     # ~45 componentes Shadcn UI
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── craco.config.js
│   └── tailwind.config.js
├── docker-compose.yml         # 3 servicios: MongoDB, backend, frontend
├── .dockerignore
├── .env.docker                # Template de env vars para Docker
├── CLAUDE.md                  # Guía para Claude Code
├── DEPLOY.md                  # Guía de instalación completa
└── backend_test.py            # Tests automatizados
```

---

## 🛠️ Comandos Útiles

```bash
# Docker
docker compose up -d            # Iniciar
docker compose up -d --build    # Reconstruir
docker compose down             # Detener
docker compose logs -f backend  # Ver logs del backend
docker compose ps               # Estado de servicios

# Backend (local)
uvicorn server:app --reload --port 8001

# Frontend (local)
yarn start                      # Dev server (CRACO)
yarn build                      # Build producción
```

---

## 🎨 Diseño

- **Tipografía**: Playfair Display (headings), Manrope (body), JetBrains Mono (mono)
- **Colores**: Esquema "Swiss Luxury" — fondo claro `#F2F2F0`, acento teal `#00C2CB`
- **Estilo**: Bordes sharp, botones pill, tracking expandido, noise overlay, glassmorphism
- **Tema**: Light/dark automático según preferencia del sistema

---

## 📄 Licencia

MIT