# Vigil - Price Tracking Platform

Vigil is a web application that allows users to track price changes on products or services from any website. Users can subscribe to items and receive notifications via email, WhatsApp, Telegram, or SMS when prices change.

## Features

- **URL-based Tracking**: Add any product or service by providing its URL
- **Smart Price Extraction**: Extracts title, price, description, and image using web scraping or AI
- **Multi-currency Support**: Supports CLP, USD, EUR, MXN, ARS, BRL, and GBP
- **Price History**: View historical price data with interactive charts
- **Notifications**: Get alerts via email, WhatsApp, Telegram, or SMS when prices change
- **Light/Dark Theme**: Automatically matches your system preference

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | React, Tailwind CSS, Shadcn UI |
| Backend | FastAPI (Python) |
| Database | MongoDB |
| Authentication | Google OAuth (via Emergent) |

## Project Structure

```
cotiza/
├── backend/
│   ├── server.py         # FastAPI application
│   └── requirements.txt  # Python dependencies
├── frontend/
│   ├── src/              # React source code
│   ├── package.json      # Node dependencies
│   └── README.md         # Frontend-specific documentation
├── DEPLOY.md             # Deployment guide
└── memory/
    └── PRD.md            # Product Requirements Document
```

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.10+
- MongoDB 6.0+

### Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file (copy from .env.example if available)
# Configure the following environment variables:
# - MONGO_URL: MongoDB connection string
# - DB_NAME: Database name
# - EMERGENT_LLM_KEY: For AI-based price extraction (optional)

# Run the server
uvicorn server:app --reload --port 8001
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
yarn install

# Create .env file
# REACT_APP_BACKEND_URL=http://localhost:8001

# Start development server
yarn start
```

The frontend will be available at http://localhost:3000.

## Environment Variables

### Backend (`backend/.env`)

```env
# MongoDB
MONGO_URL="mongodb://localhost:27017"
DB_NAME="vigil_db"

# Emergent LLM Key (optional - for AI extraction)
EMERGENT_LLM_KEY=your_key_here

# Price check interval in hours
PRICE_CHECK_INTERVAL_HOURS=12
```

### Frontend (`frontend/.env`)

```env
REACT_APP_BACKEND_URL=http://localhost:8001
```

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/session` | Create session from session_id |
| GET | `/api/auth/me` | Get current user |
| POST | `/api/auth/logout` | Logout user |

### Items

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/items` | List user's tracked items |
| POST | `/api/items` | Add new item to track |
| GET | `/api/items/{id}` | Get item details |
| PUT | `/api/items/{id}` | Update item |
| DELETE | `/api/items/{id}` | Remove item |
| POST | `/api/items/preview` | Preview extraction before adding |
| POST | `/api/items/{id}/check` | Manually trigger price check |

### Price History

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/items/{id}/history` | Get price history for item |

### Cron Jobs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/cron/status` | Get scheduler status |
| POST | `/api/cron/trigger` | Manually trigger price check |

## Deployment

For detailed deployment instructions, see [DEPLOY.md](DEPLOY.md).

## License

MIT
