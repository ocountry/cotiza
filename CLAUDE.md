# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Vigil** — Plataforma de monitoreo de precios. Los usuarios ingresan URLs de productos, el sistema extrae la información (precio, título, descripción, imagen) y notifica cambios de precio vía webhook. Stack: FastAPI + MongoDB + React (Create React App + CRACO + Tailwind CSS + Shadcn UI).

## Comandos

### Docker (producción y desarrollo reproducible)
```bash
# Configurar variables de entorno (requiere Google OAuth)
cp .env.docker .env
# Editar .env con GOOGLE_CLIENT_ID y GOOGLE_CLIENT_SECRET

# Iniciar todos los servicios
docker compose up -d

# Reconstruir después de cambios
docker compose up -d --build

# Ver logs
docker compose logs -f backend

# Detener
docker compose down

# Con CloudPanel: Vigil corre en 127.0.0.1:3000, CloudPanel proxy reversa
# Más detalles en DEPLOY.md
```

### Backend (desarrollo local)
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Configurar variables
uvicorn server:app --reload --port 8001
```

### Frontend
```bash
cd frontend
yarn install
cp .env.example .env  # REACT_APP_BACKEND_URL=http://localhost:8001
yarn start             # CRACO dev server on port 3000
yarn build             # Production build
```

### Tests
```bash
python3 backend_test.py --base-url http://localhost:8001/api
```

## Variables de Entorno

### Backend (`backend/.env`)
| Variable | Descripción |
|---|---|
| `MONGO_URL` | URI de MongoDB (ej: `mongodb://localhost:27017`) |
| `DB_NAME` | Nombre de la base de datos |
| `GOOGLE_CLIENT_ID` | Client ID de Google OAuth (requerido) |
| `GOOGLE_CLIENT_SECRET` | Client Secret de Google OAuth (requerido) |
| `GOOGLE_REDIRECT_URI` | URI de callback OAuth |
| `FRONTEND_URL` | URL del frontend para redirects |
| `FIRECRAWL_MODE` | `cloud` o `selfhosted` |
| `FIRECRAWL_API_KEY` | API key de Firecrawl.dev |
| `LLM_API_KEY` | API key para extracción por IA (OpenAI u OpenAI-compatible) |
| `LLM_PROVIDER` | Proveedor LLM (default: `openai`) |
| `LLM_MODEL` | Modelo (default: `gpt-4o-mini`) |
| `LLM_API_URL` | URL de API (default: `https://api.openai.com/v1/chat/completions`) |
| `NOTIFICATION_WEBHOOK_URL` | URL del webhook para notificaciones |
| `PRICE_CHECK_INTERVAL_HOURS` | Intervalo de verificación (default: 12) |

### Frontend (`frontend/.env`)
| Variable | Descripción |
|---|---|
| `REACT_APP_BACKEND_URL` | URL del backend (ej: `http://localhost:8001`) |

## Arquitectura

```
/
├── backend/
│   ├── server.py            # Entry point FastAPI (importa routers)
│   ├── config.py            # Config centralizada: env vars, MongoDB, logging
│   ├── models.py            # Modelos Pydantic (User, TrackedItem, etc.)
│   ├── auth.py              # Google OAuth, sesiones, get_current_user
│   ├── scraping.py          # Web scraping: BeautifulSoup, Firecrawl, price parsing
│   ├── llm.py               # Extracción por IA (OpenAI-compatible API)
│   ├── notifications.py     # Servicio de notificaciones vía webhook
│   ├── cron.py              # Scheduler de verificación periódica de precios
│   ├── routes/
│   │   ├── __init__.py
│   │   └── items.py         # CRUD items, price check, preview, cron status
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.js           # Router principal (React Router v7)
│   │   ├── index.js         # Entry point
│   │   ├── index.css        # Tailwind + variables CSS + animaciones
│   │   ├── lib/
│   │   │   ├── api.js       # API utility con auth token automático
│   │   │   └── utils.js     # cn() utility (clsx + tailwind-merge)
│   │   ├── contexts/
│   │   │   ├── AuthContext.js   # Auth global (Google OAuth + Bearer token)
│   │   │   └── ThemeContext.js  # Tema light/dark/system
│   │   ├── pages/
│   │   │   ├── LandingPage.js   # Landing + hero + features
│   │   │   ├── AuthCallback.js  # Procesa callback OAuth (token desde query params)
│   │   │   ├── Dashboard.js     # Grid de items tracked
│   │   │   ├── AddItem.js       # Formulario: URL + preview + método + canales
│   │   │   ├── ItemDetail.js    # Detalle + gráfico Recharts + edición
│   │   │   └── Settings.js      # Perfil + canales de notificación + tema
│   │   └── components/ui/  # ~45 componentes Shadcn UI (Radix primitives)
│   ├── nginx.conf           # Nginx config para Docker (proxy /api → backend)
│   ├── Dockerfile           # Multi-stage build (node → nginx)
│   ├── craco.config.js
│   └── tailwind.config.js
├── docker-compose.yml       # 3 servicios: MongoDB, backend, frontend (CloudPanel-ready)
├── .dockerignore            # Excluye venv, node_modules, .env, etc.
├── .env.docker              # Template de env vars para Docker
├── backend/Dockerfile       # Python 3.11-slim + uvicorn
├── memory/PRD.md
├── design_guidelines.json
├── DEPLOY.md
├── backend_test.py
└── CLAUDE.md
```

### Stack Técnico

- **Backend**: FastAPI, Pydantic, Motor (async MongoDB), BeautifulSoup, httpx, APScheduler, Firecrawl SDK
- **Frontend**: React 19, React Router 7, CRACO, Tailwind 3, Shadcn UI (Radix), Recharts, Sonner, Lucide
- **Base de datos**: MongoDB
- **Autenticación**: Google OAuth directo (sin Emergent)
- **Scraping**: Híbrido — BeautifulSoup + JSON-LD + Firecrawl (cloud/self-hosted)
- **LLM**: OpenAI-compatible API (configurable: OpenAI, Anthropic, local, etc.)

### API Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/auth/google/login` | Inicia flujo Google OAuth |
| GET | `/api/auth/google/callback` | Callback OAuth de Google |
| POST | `/api/auth/session` | (Legacy) Intercambia session_id por token |
| GET | `/api/auth/me` | Usuario actual |
| POST | `/api/auth/logout` | Cerrar sesión |
| PUT | `/api/auth/profile` | Actualizar canales de notificación |
| POST | `/api/items` | Crear item (con extracción) |
| GET | `/api/items` | Listar items del usuario |
| GET | `/api/items/{id}` | Detalle de item |
| PUT | `/api/items/{id}` | Actualizar item |
| DELETE | `/api/items/{id}` | Eliminar item + historial |
| POST | `/api/items/{id}/check` | Verificar precio manualmente |
| GET | `/api/items/{id}/history` | Historial de precios |
| POST | `/api/preview` | Vista previa de extracción |
| GET | `/api/cron/status` | Estado del scheduler |
| POST | `/api/cron/trigger` | Disparar verificación manual |

### Flujo de Autenticación

1. Usuario hace clic en "Sign In" → `AuthContext.login()` → redirect a `/api/auth/google/login`
2. Backend redirige a Google OAuth consent screen
3. Google redirige a `/api/auth/google/callback?code=xxx`
4. Backend intercambia code por tokens, obtiene datos del usuario
5. Backend crea/actualiza usuario en MongoDB, genera session_token
6. Backend redirige a `FRONTEND_URL/auth/callback?token=xxx`
7. `AuthCallback.js` extrae el token, `processSession()` lo guarda en localStorage
8. Todas las requests incluyen `Authorization: Bearer <token>` vía `apiFetch()`

### Modelos de Datos (MongoDB)

- **users**: `{user_id, email, name, picture, google_id, notification_email, notification_whatsapp, notification_telegram, notification_sms, created_at, last_login}`
- **user_sessions**: `{session_id, user_id, session_token, expires_at, created_at}`
- **tracked_items**: `{item_id, user_id, url, title, description, image_url, current_price, currency, extraction_method, notification_channels, notes, is_active, last_checked, created_at, updated_at}`
- **price_history**: `{history_id, item_id, price, currency, checked_at}`

### Diseño UI

- **Tipografía**: Playfair Display (headings), Manrope (body), JetBrains Mono (mono)
- **Colores**: Esquema "Swiss Luxury" — fondo claro `#F2F2F0`, acento teal `#00C2CB`
- **Estilo**: Bordes sharp (`rounded-none`), botones pill, tracking expandido, noise overlay, glassmorphism
- **Tema**: Light/dark automático según preferencia del sistema

## Configuración Local

### 1. Prerrequisitos
- Python 3.10+, Node.js 18+, MongoDB 6.0+, Yarn

### 2. Google OAuth
1. Ir a [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Crear OAuth 2.0 Client ID (Web application)
3. Agregar `http://localhost:8001/api/auth/google/callback` como Authorized redirect URI
4. Copiar Client ID y Client Secret a `backend/.env`

### 3. Iniciar
```bash
# Backend
cd backend && source venv/bin/activate && uvicorn server:app --reload --port 8001

# Frontend (otra terminal)
cd frontend && yarn start
```

## Notas

- El token de sesión se almacena en `localStorage` como `vigil_session_token` y se envía como Bearer token
- El backend también soporta cookies para mismositio (producción con mismo dominio)
- La extracción por IA requiere una API key de OpenAI u otro proveedor compatible
- Firecrawl es opcional pero recomendado para sitios con protección anti-bot