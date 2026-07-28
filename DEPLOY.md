# Guía de Instalación - Vigil Price Tracker

---

## 🐳 Paso a Paso: Despliegue con Docker

Esta guía asume que tienes Docker instalado en tu servidor. Si también tienes CloudPanel, se incluyen instrucciones específicas para que no haya conflictos.

---

### 📋 Requisitos

| Requisito | Versión Mínima | Cómo verificar |
|---|---|---|
| **Docker** | 24+ | `docker --version` |
| **Docker Compose** | v2 | `docker compose version` |
| **Git** | — | `git --version` |

Si no tienes Docker instalado:

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Cerrar sesión y volver a entrar, o ejecutar: newgrp docker
```

---

### Índice

1. [Clonar el repositorio](#1-clonar-el-repositorio)
2. [Configurar variables de entorno](#2-configurar-variables-de-entorno)
3. [Crear credenciales de Google OAuth](#3-crear-credenciales-de-google-oauth)
4. [Iniciar los servicios](#4-iniciar-los-servicios)
5. [Verificar que todo funciona](#5-verificar-que-todo-funciona)
6. [Configurar CloudPanel (opcional)](#6-configurar-cloudpanel-opcional)
7. [Comandos de administración](#7-comandos-de-administración)
8. [Troubleshooting](#8-troubleshooting)

---

### 1. Clonar el repositorio

```bash
# Ve al directorio donde quieres instalar Vigil
cd /home/usuario  # o /opt, /srv, etc.

# Clona el repositorio
git clone https://github.com/ocountry/cotiza.git
cd cotiza

# Verifica que los archivos Docker existen
ls -la docker-compose.yml backend/Dockerfile frontend/Dockerfile frontend/nginx.conf
```

**Salida esperada:**
```
-rw-r--r--  docker-compose.yml
-rw-r--r--  backend/Dockerfile
-rw-r--r--  frontend/Dockerfile
-rw-r--r--  frontend/nginx.conf
```

---

### 2. Configurar variables de entorno

```bash
# Copia el template de variables de entorno para Docker
cp .env.docker .env

# Edita el archivo con tus valores
nano .env
```

El archivo `.env` debe verse así (con tus valores reales):

```bash
# ==============================================
# Vigil - Variables de Entorno para Docker
# ==============================================

# MongoDB (no tocar — usa DNS interno de Docker)
MONGO_URL=mongodb://mongodb:27017
DB_NAME=vigil_db

# ──────────────────────────────────────────────
# Google OAuth — REQUERIDO
# Ve al paso 3 para crear estas credenciales
# ──────────────────────────────────────────────
GOOGLE_CLIENT_ID=123456789-abc123def456.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-tu_secret_aqui
GOOGLE_REDIRECT_URI=http://localhost/api/auth/google/callback
# ⚠️ Para producción con CloudPanel, cambia a:
# GOOGLE_REDIRECT_URI=https://vigil.tudominio.com/api/auth/google/callback

# URL del frontend (para redirects OAuth)
FRONTEND_URL=http://localhost
# ⚠️ Para producción con CloudPanel, cambia a:
# FRONTEND_URL=https://vigil.tudominio.com

# Puerto del frontend (no usar 80 si hay CloudPanel)
VIGIL_PORT=3000
# Si el puerto 3000 está ocupado, usa otro:
# VIGIL_PORT=3001

# ──────────────────────────────────────────────
# Firecrawl — Opcional (para sitios con anti-bot)
# ──────────────────────────────────────────────
FIRECRAWL_MODE=cloud
FIRECRAWL_API_KEY=fc-xxxxxxxxxxxx
# O self-hosted:
# FIRECRAWL_MODE=selfhosted
# FIRECRAWL_SELFHOSTED_URL=http://tu-servidor:3002/v2/scrape

# ──────────────────────────────────────────────
# LLM (IA) — Opcional (para extracción por IA)
# ──────────────────────────────────────────────
LLM_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
# Para OpenAI: no tocar LLM_API_URL (default)
# Para Anthropic: LLM_API_URL=https://api.anthropic.com/v1/messages
# Para Ollama local: LLM_API_URL=http://host.docker.internal:11434/v1/chat/completions

# ──────────────────────────────────────────────
# Notificaciones — Opcional
# ──────────────────────────────────────────────
NOTIFICATION_WEBHOOK_URL=https://hooks.example.com/notify

# ──────────────────────────────────────────────
# Verificación periódica de precios
# ──────────────────────────────────────────────
PRICE_CHECK_INTERVAL_HOURS=12
```

**⛔ Archivos que NO se deben subir a Git** (ya están en `.gitignore`):
- `.env` — contiene tus credenciales reales
- `.env.local` — variables locales
- `venv/`, `node_modules/` — dependencias

---

### 3. Crear credenciales de Google OAuth

Google OAuth es **obligatorio** — Vigil no funciona sin autenticación.

#### Paso 3.1: Ir a Google Cloud Console

1. Abre [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Inicia sesión con tu cuenta de Google
3. Si es la primera vez, crea un proyecto o selecciona uno existente

#### Paso 3.2: Crear Credenciales OAuth

1. Haz clic en **"Create Credentials"** → **"OAuth client ID"**
2. En **Application type**: selecciona **"Web application"**
3. En **Name**: ponle `Vigil` o `Cotiza`
4. En **Authorized JavaScript origins**: déjalo vacío (no es necesario)
5. En **Authorized redirect URIs**: agrega las URLs según tu caso:

   **Para Docker local (pruebas):**
   ```
   http://localhost/api/auth/google/callback
   ```

   **Para producción con CloudPanel:**
   ```
   https://vigil.tudominio.com/api/auth/google/callback
   ```

6. Haz clic en **"Create"**

#### Paso 3.3: Copiar las credenciales

Google te mostrará una ventana con:

```
Client ID:     123456789-abc123def456.apps.googleusercontent.com
Client Secret: GOCSPX-tu_secret_aqui
```

Copia estos valores y pégalos en tu archivo `.env`:

```bash
GOOGLE_CLIENT_ID=123456789-abc123def456.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-tu_secret_aqui
```

**⚠️ Importante:** El `GOOGLE_REDIRECT_URI` en tu `.env` debe coincidir **exactamente** con lo que registraste en Google Cloud Console. Si no coincide, el login fallará con error `redirect_uri_mismatch`.

---

### 4. Iniciar los servicios

#### Primer inicio (construye las imágenes)

```bash
# Desde la raíz del proyecto (donde está docker-compose.yml)
cd /ruta/a/cotiza

# Construye e inicia todos los servicios
docker compose up -d
```

**Lo que hace este comando:**

1. **Construye la imagen del backend** (Python 3.11-slim, instala dependencias, copia el código)
2. **Construye la imagen del frontend** (compila React con Node 18, luego sirve con nginx)
3. **Descarga MongoDB 7** (si no está en caché)
4. **Crea una red interna** para que los contenedores se comuniquen
5. **Inicia en orden**: MongoDB → Backend → Frontend

**Salida esperada:**
```
[+] Building ... (backend)
[+] Building ... (frontend)
[+] Running 4/4
 ✔ Network cotiza_default       Created
 ✔ Container vigil-mongodb      Started
 ✔ Container vigil-backend      Started
 ✔ Container vigil-frontend     Started
```

#### Verificar que los servicios están corriendo

```bash
docker compose ps
```

**Salida esperada:**
```
NAME                IMAGE               STATUS                   PORTS
vigil-mongodb       mongo:7             Up (healthy)             27017/tcp
vigil-backend       cotiza-backend      Up (healthy)             8001/tcp
vigil-frontend      cotiza-frontend     Up (healthy)             0.0.0.0:3000->80/tcp
```

Los tres deben mostrar `Up (healthy)`. Si alguno no está healthy, espera unos segundos más y vuelve a intentar (MongoDB tarda ~15s en inicializar).

---

### 5. Verificar que todo funciona

#### Prueba 1: API del backend

```bash
curl http://127.0.0.1:3000/api/
```

**Respuesta esperada:**
```json
{"message": "Vigil API - Price Tracking Service"}
```

#### Prueba 2: Frontend

```bash
curl -s http://127.0.0.1:3000/ | head -5
```

**Respuesta esperada:**
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    ...
```

#### Prueba 3: Estado del cron

```bash
curl http://127.0.0.1:3000/api/cron/status
```

**Respuesta esperada:**
```json
{"scheduler_running": true, "interval_hours": 12, "jobs": [...]}
```

#### Prueba 4: Health check de cada contenedor

```bash
docker inspect --format='{{json .State.Health.Status}}' vigil-mongodb
docker inspect --format='{{json .State.Health.Status}}' vigil-backend
docker inspect --format='{{json .State.Health.Status}}' vigil-frontend
```

**Todos deben responder:** `"healthy"`

---

### 6. Configurar CloudPanel (opcional)

Si tienes CloudPanel en tu servidor, sigue estos pasos para que Vigil quede accesible desde un subdominio con SSL automático.

#### 6.1. Asegúrate de que Vigil esté corriendo

```bash
docker compose ps
# vigil-frontend debe estar en 127.0.0.1:3000
```

#### 6.2. Crea el sitio en CloudPanel

1. Abre CloudPanel en tu navegador: `https://cloudpanel.tudominio.com`
2. Ve a **Sites** → **Add Site**
3. Configura:
   - **Domain**: `vigil.tudominio.com`
   - **SSL Certificate**: ✅ **Create a Let's Encrypt certificate** (recomendado)
   - **Site User**: déjalo por defecto
4. Haz clic en **Create**

#### 6.3. Configura el Reverse Proxy

1. En CloudPanel, ve a **Sites** → selecciona `vigil.tudominio.com`
2. Ve a **Settings** → **Reverse Proxy**
3. Configura:
   - **Type**: Proxy
   - **Target**: `http://127.0.0.1:3000`
4. Haz clic en **Save**

#### 6.4. Actualiza las variables de entorno (si ya configuraste antes)

Ahora que sabes el dominio definitivo, actualiza el `.env`:

```bash
nano .env
```

Cambia estas líneas:

```bash
GOOGLE_REDIRECT_URI=https://vigil.tudominio.com/api/auth/google/callback
FRONTEND_URL=https://vigil.tudominio.com
```

#### 6.5. Reconstruye y reinicia

```bash
docker compose up -d --build
```

#### 6.6. Actualiza Google Cloud Console

Agrega la nueva redirect URI en [Google Cloud Console](https://console.cloud.google.com/apis/credentials):

```
https://vigil.tudominio.com/api/auth/google/callback
```

#### 6.7. ¡Listo!

Abre `https://vigil.tudominio.com` en tu navegador. Deberías ver la pantalla de login de Vigil. Haz clic en **"Sign In with Google"** para iniciar sesión.

---

### 7. Comandos de administración

#### Gestión de servicios

```bash
# Iniciar
docker compose up -d

# Detener (conserva los datos)
docker compose down

# Detener y eliminar volúmenes (⚠️ borra TODOS los datos)
docker compose down -v

# Reiniciar un servicio específico
docker compose restart backend
docker compose restart frontend
docker compose restart mongodb

# Pausar / reanudar
docker compose pause
docker compose unpause
```

#### Logs

```bash
# Ver logs de todos los servicios
docker compose logs -f

# Ver logs de un servicio específico
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f mongodb

# Últimas 50 líneas de un servicio
docker compose logs --tail=50 backend

# Logs desde una fecha/hora
docker compose logs --since="2026-07-27T10:00:00" frontend
```

#### Actualizar Vigil

```bash
# 1. Bajar servicios
docker compose down

# 2. Obtener la última versión del código
git pull origin main

# 3. Reconstruir y reiniciar
docker compose up -d --build
```

#### Hacer backup de la base de datos

```bash
# Exportar MongoDB desde el contenedor
docker exec vigil-mongodb mongodump --db vigil_db --out /tmp/backup
docker cp vigil-mongodb:/tmp/backup ./backup-vigil-$(date +%Y%m%d)

# Restaurar
docker cp ./backup-vigil-20260727 vigil-mongodb:/tmp/backup
docker exec vigil-mongodb mongorestore --db vigil_db /tmp/backup/vigil_db
```

---

### 8. Troubleshooting

#### ❌ Error: `GOOGLE_CLIENT_ID: error` o `GOOGLE_CLIENT_SECRET: error`

**Causa:** No configuraste las variables en `.env`.

**Solución:**
```bash
nano .env
# Asegúrate de que GOOGLE_CLIENT_ID y GOOGLE_CLIENT_SECRET tienen valores reales
# Luego reinicia
docker compose up -d
```

#### ❌ Error: `redirect_uri_mismatch` al hacer login con Google

**Causa:** La URI en Google Cloud Console no coincide con `GOOGLE_REDIRECT_URI` del `.env`.

**Solución:** Verifica ambos valores:

```bash
# 1. Revisa qué URI está configurada en Vigil
grep GOOGLE_REDIRECT_URI .env

# 2. Ve a Google Cloud Console → APIs & Services → Credentials
#    → Edita tu OAuth client → Authorized redirect URIs
#    Deben coincidir EXACTAMENTE (incluyendo http vs https, la barra al final, etc.)
```

#### ❌ Error: `port is already allocated` al iniciar

**Causa:** El puerto 3000 (o el configurado) está ocupado.

**Solución:**
```bash
# 1. Verifica qué está usando el puerto
sudo lsof -i :3000

# 2. Cambia el puerto de Vigil
nano .env
# VIGIL_PORT=3001

# 3. Reinicia
docker compose up -d
```

#### ❌ Error: `Connection refused` al acceder al frontend

**Causa:** El frontend no está listo (el build de React puede tardar).

**Solución:**
```bash
# Espera unos segundos más y verifica
docker compose ps
docker compose logs frontend --tail=20
```

#### ❌ Error: `Cannot connect to MongoDB` en los logs del backend

**Causa:** MongoDB no está listo aún.

**Solución:**
```bash
# Verifica el estado de MongoDB
docker compose logs mongodb --tail=20

# Si MongoDB está healthy, espera que el backend se reconecte automáticamente
# (FastAPI maneja reconexión)
```

#### ❌ CloudPanel: el sitio devuelve 502 Bad Gateway

**Causa:** CloudPanel no puede alcanzar Vigil en el puerto configurado.

**Solución:**
```bash
# 1. Verifica que Vigil está corriendo
docker compose ps

# 2. Verifica que responde localmente
curl http://127.0.0.1:3000/api/

# 3. Verifica la configuración de CloudPanel
#    Sites → vigil.tudominio.com → Settings → Reverse Proxy
#    Target debe ser: http://127.0.0.1:3000
```

#### 🔍 Logs útiles para diagnóstico

```bash
# Ver todos los logs de arranque
docker compose logs --tail=100

# Ver logs en tiempo real
docker compose logs -f

# Ver detalles de un contenedor
docker inspect vigil-backend

# Ver uso de recursos
docker stats
```

---

## 📦 Instalación Tradicional (Sin Docker)

Si prefieres instalar Vigil directamente en el servidor sin Docker, consulta la sección a continuación.

### Requisitos del Servidor

- **Sistema Operativo**: Ubuntu 20.04+ / Debian 11+
- **Node.js**: v18+
- **Python**: 3.10+
- **MongoDB**: 6.0+
- **RAM**: Mínimo 2GB
- **Disco**: 10GB+

### 1. Instalar Dependencias del Sistema

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Node.js 18
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Instalar Python 3.10+ y pip
sudo apt install -y python3 python3-pip python3-venv

# Instalar MongoDB
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | sudo gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg
echo "deb [signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg] http://repo.mongodb.org/apt/debian bookworm/mongodb-org/7.0 main" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt update
sudo apt install -y mongodb-org

# Iniciar MongoDB
sudo systemctl start mongod
sudo systemctl enable mongod

# Instalar Yarn
npm install -g yarn
```

### 2. Clonar y Configurar

```bash
git clone https://github.com/ocountry/cotiza.git
cd cotiza

# Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env  # Configurar variables
uvicorn server:app --host 0.0.0.0 --port 8001 &

# Frontend
cd ../frontend
yarn install
cp .env.example .env
nano .env  # REACT_APP_BACKEND_URL=http://localhost:8001
yarn build
npx serve -s build -l 3000
```

---

## Referencia Rápida de Docker

| Comando | Descripción |
|---|---|
| `docker compose up -d` | Iniciar todos los servicios en segundo plano |
| `docker compose up -d --build` | Reconstruir imágenes y reiniciar |
| `docker compose down` | Detener servicios (conserva datos) |
| `docker compose down -v` | Detener y eliminar datos (⚠️ destructivo) |
| `docker compose ps` | Estado de servicios |
| `docker compose logs -f backend` | Logs del backend en tiempo real |
| `docker compose restart backend` | Reiniciar solo el backend |
| `docker compose pull` | Actualizar imágenes base (MongoDB) |
| `docker system prune` | Limpiar imágenes y contenedores no usados |