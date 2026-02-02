# Guía de Instalación - Vigil Price Tracker

## Requisitos del Servidor

- **Sistema Operativo**: Ubuntu 20.04+ / Debian 11+
- **Node.js**: v18+ 
- **Python**: 3.10+
- **MongoDB**: 6.0+
- **RAM**: Mínimo 2GB
- **Disco**: 10GB+

---

## 1. Instalar Dependencias del Sistema

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Node.js 18
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Instalar Python 3.10+ y pip
sudo apt install -y python3 python3-pip python3-venv

# Instalar MongoDB
curl -fsSL https://www.mongodb.org/static/pgp/server-6.0.asc | sudo gpg --dearmor -o /usr/share/keyrings/mongodb-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/mongodb-archive-keyring.gpg] https://repo.mongodb.org/apt/ubuntu $(lsb_release -cs)/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list
sudo apt update
sudo apt install -y mongodb-org

# Iniciar MongoDB
sudo systemctl start mongod
sudo systemctl enable mongod

# Instalar Yarn
npm install -g yarn

# Instalar Supervisor (para gestionar procesos)
sudo apt install -y supervisor
```

---

## 2. Clonar el Repositorio

```bash
cd /opt
sudo git clone https://github.com/TU_USUARIO/vigil.git
sudo chown -R $USER:$USER /opt/vigil
cd /opt/vigil
```

---

## 3. Configurar Backend

```bash
cd /opt/vigil/backend

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Instalar emergentintegrations (si usas Emergent LLM Key)
pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/
```

### Configurar variables de entorno

```bash
cp .env.example .env  # O crear desde cero
nano .env
```

**Contenido de `/opt/vigil/backend/.env`:**

```env
# MongoDB
MONGO_URL="mongodb://localhost:27017"
DB_NAME="vigil_db"

# CORS
CORS_ORIGINS="*"

# Emergent LLM Key (para extracción AI) - Opcional
EMERGENT_LLM_KEY=tu_key_aqui

# Firecrawl - para sitios protegidos
FIRECRAWL_MODE=cloud
FIRECRAWL_API_KEY=tu_firecrawl_api_key
# O usar self-hosted:
# FIRECRAWL_MODE=selfhosted
# FIRECRAWL_SELFHOSTED_URL=http://tu-servidor:3002/v2/scrape

# Webhook para notificaciones
NOTIFICATION_WEBHOOK_URL="https://tu-webhook-url.com/notify"

# Intervalo de verificación de precios (en horas)
PRICE_CHECK_INTERVAL_HOURS=12
```

---

## 4. Configurar Frontend

```bash
cd /opt/vigil/frontend

# Instalar dependencias
yarn install
```

### Configurar variables de entorno

```bash
nano .env
```

**Contenido de `/opt/vigil/frontend/.env`:**

```env
REACT_APP_BACKEND_URL=https://tu-dominio.com
```

### Compilar para producción

```bash
yarn build
```

---

## 5. Configurar Supervisor

Crear archivo de configuración:

```bash
sudo nano /etc/supervisor/conf.d/vigil.conf
```

**Contenido:**

```ini
[program:vigil-backend]
directory=/opt/vigil/backend
command=/opt/vigil/backend/venv/bin/uvicorn server:app --host 0.0.0.0 --port 8001
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/supervisor/vigil-backend.err.log
stdout_logfile=/var/log/supervisor/vigil-backend.out.log
environment=PATH="/opt/vigil/backend/venv/bin"

[program:vigil-frontend]
directory=/opt/vigil/frontend
command=npx serve -s build -l 3000
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/supervisor/vigil-frontend.err.log
stdout_logfile=/var/log/supervisor/vigil-frontend.out.log
```

### Iniciar servicios

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start all
sudo supervisorctl status
```

---

## 6. Configurar Nginx (Reverse Proxy)

```bash
sudo apt install -y nginx
sudo nano /etc/nginx/sites-available/vigil
```

**Contenido:**

```nginx
server {
    listen 80;
    server_name tu-dominio.com;

    # Frontend
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API
    location /api {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Activar sitio

```bash
sudo ln -s /etc/nginx/sites-available/vigil /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 7. Configurar SSL (HTTPS) con Let's Encrypt

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d tu-dominio.com
```

---

## 8. Comandos Útiles

```bash
# Ver estado de servicios
sudo supervisorctl status

# Reiniciar backend
sudo supervisorctl restart vigil-backend

# Reiniciar frontend
sudo supervisorctl restart vigil-frontend

# Ver logs del backend
tail -f /var/log/supervisor/vigil-backend.err.log

# Ver logs del frontend
tail -f /var/log/supervisor/vigil-frontend.err.log

# Verificar estado del cron
curl http://localhost:8001/api/cron/status
```

---

## 9. Estructura de Archivos

```
/opt/vigil/
├── backend/
│   ├── .env              # Variables de entorno
│   ├── server.py         # Aplicación FastAPI
│   ├── requirements.txt  # Dependencias Python
│   └── venv/             # Entorno virtual
├── frontend/
│   ├── .env              # Variables de entorno
│   ├── build/            # Archivos compilados
│   ├── src/              # Código fuente
│   └── package.json      # Dependencias Node
└── DEPLOY.md             # Esta guía
```

---

## 10. Obtener API Keys

### Firecrawl (para scraping de sitios protegidos)
1. Ir a https://www.firecrawl.dev/
2. Crear cuenta y obtener API Key
3. Agregar a `FIRECRAWL_API_KEY` en `.env`

### Emergent LLM Key (opcional, para extracción AI)
1. Usar la plataforma Emergent
2. Ir a Profile -> Universal Key
3. Agregar a `EMERGENT_LLM_KEY` en `.env`

---

## Troubleshooting

### MongoDB no inicia
```bash
sudo systemctl status mongod
sudo journalctl -u mongod
```

### Backend no inicia
```bash
tail -100 /var/log/supervisor/vigil-backend.err.log
```

### Frontend no carga
```bash
# Verificar que el build existe
ls -la /opt/vigil/frontend/build/

# Recompilar
cd /opt/vigil/frontend && yarn build
```

### Verificar puertos
```bash
sudo netstat -tlnp | grep -E '3000|8001|27017'
```
