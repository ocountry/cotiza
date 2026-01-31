# Vigil - Price Tracking Platform PRD

## Original Problem Statement
Desarrollar una web que permita a usuarios suscribirse a cambios de precio en productos o servicios publicados en cualquier sitio web (vuelos, hoteles, ropa, herramientas, etc). El usuario ingresa una URL, el sistema analiza la página y extrae información (precio, título, descripción), creando el item en la cuenta del usuario con opciones de notificación (email, whatsapp, telegram).

## User Personas
1. **Cazador de Ofertas**: Busca los mejores precios antes de comprar productos costosos
2. **Viajero Frecuente**: Monitorea precios de vuelos y hoteles para encontrar las mejores tarifas
3. **Coleccionista**: Sigue artículos específicos esperando bajadas de precio

## Core Requirements
- Autenticación con Google OAuth (Emergent-managed)
- Extracción de datos por URL (scraping básico o AI con GPT-5.2)
- Tracking de múltiples items por usuario
- Notificaciones via webhook a endpoint del usuario
- Historial de precios con gráficos
- Tema light/dark según preferencia del sistema

## What's Been Implemented (Jan 31, 2026)

### Backend (FastAPI + MongoDB)
- ✅ Autenticación con Emergent Google OAuth
- ✅ Modelos: User, UserSession, TrackedItem, PriceHistory
- ✅ Endpoints CRUD para items (/api/items)
- ✅ **Extracción mejorada con scraping** (soporta Sodimac, Falabella, sitios chilenos)
- ✅ Extracción con IA (GPT-5.2 via emergentintegrations)
- ✅ Preview de extracción antes de crear item
- ✅ Verificación manual de precio (/api/items/{id}/check)
- ✅ Historial de precios (/api/items/{id}/history)
- ✅ Sistema de notificaciones via webhook (NOTIFICATION_WEBHOOK_URL env var)
- ✅ **Multi-currency price parsing** (CLP, USD, EUR, MXN, ARS, BRL, GBP)
- ✅ **User notification channel config** (email, whatsapp, telegram, SMS)
- ✅ **PUT /api/auth/profile** para actualizar canales de notificación
- ✅ **Campo notes opcional** en TrackedItem para notas del usuario

### Frontend (React + Tailwind + Shadcn)
- ✅ Landing page elegante con hero section
- ✅ Tema light/dark automático según sistema
- ✅ Dashboard con lista de items tracked
- ✅ Formulario para agregar nuevos items
- ✅ Selector de método de extracción (scraping/AI)
- ✅ Selector de canales de notificación (muestra estado configurado/no configurado)
- ✅ Vista detallada de item con gráfico de precios
- ✅ Acciones: actualizar, verificar precio, eliminar
- ✅ **Settings con configuración de canales** (email, whatsapp, telegram, SMS)
- ✅ **Formateo de precios por moneda** (CLP sin decimales, USD/EUR con decimales)
- ✅ **Bloqueo de agregar items sin precio detectado** - muestra mensaje de sitio no habilitado
- ✅ **Campo de notas opcional** al agregar item

### Extracción de Precios Mejorada (Jan 31)
- ✅ **Sodimac.cl**: Extrae título, precio (69.990 CLP), descripción e imagen
- ✅ Detecta precios en formato CLP ($69.990) automáticamente
- ✅ Busca en JSON-LD y patrones HTML raw
- ✅ Selecciona el precio más bajo (precio de oferta) cuando hay múltiples
- ⚠️ **MercadoLibre**: Requiere verificación anti-bot, recomendado usar extracción AI

## Architecture
```
/app
├── backend/
│   ├── server.py          # FastAPI app con todos los endpoints
│   └── .env               # MONGO_URL, EMERGENT_LLM_KEY
├── frontend/
│   ├── src/
│   │   ├── App.js         # Router principal
│   │   ├── contexts/      # AuthContext, ThemeContext
│   │   └── pages/         # Landing, Dashboard, AddItem, ItemDetail, Settings
│   └── .env               # REACT_APP_BACKEND_URL
```

## Prioritized Backlog

### P0 - Critical (Not blocking but important)
- [ ] Scheduled price checking (cron job cada 12 horas)
- [ ] Validación de URL antes de extracción

### P1 - Important
- [ ] Historial de notificaciones enviadas
- [ ] Filtros y búsqueda en dashboard
- [ ] Soporte para múltiples monedas
- [ ] Target price alerts (notificar cuando precio < X)

### P2 - Nice to Have
- [ ] Exportar datos a CSV
- [ ] Compartir tracking con otros usuarios
- [ ] Extensión de navegador para agregar items
- [ ] Estadísticas y analytics

## Next Tasks
1. Implementar cron job para verificación automática cada 12 horas
2. Agregar target price para alertas personalizadas
3. Mejorar extracción con selectores CSS específicos por sitio
