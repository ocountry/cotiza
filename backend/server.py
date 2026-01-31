from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import httpx
import re
from bs4 import BeautifulSoup

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== MODELS ====================

class User(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    # Notification channels configuration
    notification_email: Optional[str] = None
    notification_whatsapp: Optional[str] = None
    notification_telegram: Optional[str] = None
    notification_sms: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserSession(BaseModel):
    session_id: str
    user_id: str
    session_token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TrackedItem(BaseModel):
    item_id: str = Field(default_factory=lambda: f"item_{uuid.uuid4().hex[:12]}")
    user_id: str
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    current_price: Optional[float] = None
    currency: str = "USD"
    extraction_method: str = "scraping"  # "scraping" or "ai"
    notification_channels: List[str] = Field(default_factory=lambda: ["email"])
    notification_endpoint: Optional[str] = None
    is_active: bool = True
    last_checked: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PriceHistory(BaseModel):
    history_id: str = Field(default_factory=lambda: f"ph_{uuid.uuid4().hex[:12]}")
    item_id: str
    price: float
    currency: str = "USD"
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CreateItemRequest(BaseModel):
    url: str
    extraction_method: str = "scraping"
    notification_channels: List[str] = Field(default_factory=lambda: ["email"])
    notification_endpoint: Optional[str] = None

class UpdateItemRequest(BaseModel):
    notification_channels: Optional[List[str]] = None
    notification_endpoint: Optional[str] = None
    is_active: Optional[bool] = None
    extraction_method: Optional[str] = None

class ExtractedData(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    currency: str = "USD"
    image_url: Optional[str] = None

# ==================== AUTH HELPERS ====================

async def get_current_user(request: Request) -> User:
    """Get current user from session token"""
    session_token = request.cookies.get("session_token")
    
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.split(" ")[1]
    
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    session_doc = await db.user_sessions.find_one(
        {"session_token": session_token},
        {"_id": 0}
    )
    
    if not session_doc:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    expires_at = session_doc["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")
    
    user_doc = await db.users.find_one(
        {"user_id": session_doc["user_id"]},
        {"_id": 0}
    )
    
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    
    return User(**user_doc)

# ==================== AUTH ENDPOINTS ====================

@api_router.post("/auth/session")
async def create_session(request: Request, response: Response):
    """Exchange session_id for session_token"""
    body = await request.json()
    session_id = body.get("session_id")
    
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    
    # Get user data from Emergent auth
    async with httpx.AsyncClient() as client_http:
        auth_response = await client_http.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": session_id}
        )
        
        if auth_response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid session_id")
        
        user_data = auth_response.json()
    
    # Check if user exists
    existing_user = await db.users.find_one(
        {"email": user_data["email"]},
        {"_id": 0}
    )
    
    if existing_user:
        user_id = existing_user["user_id"]
        # Update user info
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "name": user_data["name"],
                "picture": user_data.get("picture")
            }}
        )
    else:
        # Create new user
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        new_user = {
            "user_id": user_id,
            "email": user_data["email"],
            "name": user_data["name"],
            "picture": user_data.get("picture"),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(new_user)
    
    # Create session
    session_token = user_data.get("session_token", f"st_{uuid.uuid4().hex}")
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    
    session_doc = {
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Remove old sessions for this user
    await db.user_sessions.delete_many({"user_id": user_id})
    await db.user_sessions.insert_one(session_doc)
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7 * 24 * 60 * 60
    )
    
    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    
    return {
        "user": user_doc,
        "session_token": session_token
    }

@api_router.get("/auth/me")
async def get_me(user: User = Depends(get_current_user)):
    """Get current authenticated user"""
    return user.model_dump()

@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    """Logout user"""
    session_token = request.cookies.get("session_token")
    
    if session_token:
        await db.user_sessions.delete_many({"session_token": session_token})
    
    response.delete_cookie(key="session_token", path="/")
    return {"message": "Logged out successfully"}

# ==================== EXTRACTION SERVICES ====================

def parse_price_and_currency(text: str) -> tuple:
    """
    Parse price from text supporting multiple currency formats:
    - USD: $1,299.99 or $1299.99
    - CLP: $1.299.990 or $1,299,990 (no decimals)
    - EUR: €1.299,99 or 1.299,99 €
    - General: detects currency symbol and format
    """
    if not text:
        return None, "USD"
    
    # Currency detection patterns
    currency_patterns = {
        'CLP': [r'CLP', r'\$\s*[\d\.]+(?:\.\d{3})+(?!\d)', r'pesos?\s*chilenos?'],
        'USD': [r'USD', r'US\$', r'U\.S\.\s*dollars?'],
        'EUR': [r'EUR', r'€', r'euros?'],
        'GBP': [r'GBP', r'£', r'pounds?'],
        'MXN': [r'MXN', r'pesos?\s*mexicanos?'],
        'ARS': [r'ARS', r'pesos?\s*argentinos?'],
        'BRL': [r'BRL', r'R\$', r'reais'],
    }
    
    detected_currency = "USD"
    
    # Detect currency
    text_lower = text.lower()
    for curr, patterns in currency_patterns.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                detected_currency = curr
                break
        if detected_currency != "USD":
            break
    
    # Price extraction patterns for different formats
    price_patterns = [
        # CLP format: $1.299.990 (dots as thousand separators, no decimals)
        (r'\$\s*([\d]+(?:\.[\d]{3})+)(?!\d|,)', 'dot_thousands'),
        # Format with comma as thousand separator: $1,299,990 or 1,299,990
        (r'[\$€£]?\s*([\d]+(?:,[\d]{3})+)(?:\.(\d{1,2}))?(?!\d)', 'comma_thousands'),
        # European format: 1.299,99 (dot thousands, comma decimals)
        (r'[\$€£]?\s*([\d]+(?:\.[\d]{3})+),(\d{1,2})(?!\d)', 'european'),
        # Simple format: $1299.99 or 1299.99
        (r'[\$€£]?\s*([\d]+)(?:\.(\d{1,2}))?(?!\d|\.)', 'simple'),
        # Format: 1299 (integer only)
        (r'[\$€£]\s*([\d]+)(?!\d|[.,])', 'integer'),
    ]
    
    price = None
    
    for pattern, format_type in price_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                if format_type == 'dot_thousands':
                    # CLP: 1.299.990 -> 1299990
                    price_str = match.group(1).replace('.', '')
                    price = float(price_str)
                elif format_type == 'comma_thousands':
                    # US: 1,299,990.99 -> 1299990.99
                    integer_part = match.group(1).replace(',', '')
                    decimal_part = match.group(2) if match.lastindex >= 2 and match.group(2) else '0'
                    price = float(f"{integer_part}.{decimal_part}")
                elif format_type == 'european':
                    # EU: 1.299,99 -> 1299.99
                    integer_part = match.group(1).replace('.', '')
                    decimal_part = match.group(2)
                    price = float(f"{integer_part}.{decimal_part}")
                elif format_type == 'simple':
                    integer_part = match.group(1)
                    decimal_part = match.group(2) if match.lastindex >= 2 and match.group(2) else '0'
                    price = float(f"{integer_part}.{decimal_part}")
                elif format_type == 'integer':
                    price = float(match.group(1))
                
                if price and price > 0:
                    break
            except (ValueError, AttributeError):
                continue
    
    return price, detected_currency


async def extract_with_scraping(url: str) -> ExtractedData:
    """Basic web scraping to extract product info"""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client_http:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = await client_http.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract title
            title = None
            for selector in ['h1', '[class*="title"]', '[class*="product-name"]', 'title']:
                elem = soup.select_one(selector)
                if elem:
                    title = elem.get_text(strip=True)[:200]
                    break
            
            # Extract description
            description = None
            for selector in ['[class*="description"]', '[class*="product-desc"]', 'meta[name="description"]']:
                elem = soup.select_one(selector)
                if elem:
                    if elem.name == 'meta':
                        description = elem.get('content', '')[:500]
                    else:
                        description = elem.get_text(strip=True)[:500]
                    break
            
            # Extract price with improved multi-currency support
            price = None
            currency = "USD"
            
            # First try price-specific elements
            price_elements = soup.select('[class*="price"], [data-price], [itemprop="price"], [class*="Price"], [class*="valor"], [class*="monto"]')
            for elem in price_elements:
                text = elem.get_text()
                price, currency = parse_price_and_currency(text)
                if price:
                    break
            
            # If no price found in elements, search full page
            if not price:
                # Look for price patterns in the full text
                full_text = soup.get_text()
                # Find text around price indicators
                price_indicators = ['precio', 'price', 'valor', 'total', 'costo', 'cost', '$', '€', '£']
                for indicator in price_indicators:
                    pattern = rf'.{{0,50}}{re.escape(indicator)}.{{0,100}}'
                    matches = re.findall(pattern, full_text, re.IGNORECASE)
                    for match in matches:
                        price, currency = parse_price_and_currency(match)
                        if price:
                            break
                    if price:
                        break
            
            # Extract image
            image_url = None
            for selector in ['[class*="product"] img', '[class*="gallery"] img', 'img[itemprop="image"]', 'meta[property="og:image"]']:
                elem = soup.select_one(selector)
                if elem:
                    if elem.name == 'meta':
                        image_url = elem.get('content')
                    else:
                        image_url = elem.get('src') or elem.get('data-src')
                    if image_url and not image_url.startswith('http'):
                        from urllib.parse import urljoin
                        image_url = urljoin(url, image_url)
                    break
            
            return ExtractedData(
                title=title,
                description=description,
                price=price,
                currency=currency,
                image_url=image_url
            )
    except Exception as e:
        logger.error(f"Scraping error for {url}: {e}")
        return ExtractedData()

async def extract_with_ai(url: str) -> ExtractedData:
    """Use AI to extract product info from webpage"""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        # First get the page content
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client_http:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = await client_http.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove scripts and styles
            for tag in soup(['script', 'style', 'noscript']):
                tag.decompose()
            
            # Get clean text (limit to 8000 chars)
            text_content = soup.get_text(separator=' ', strip=True)[:8000]
        
        api_key = os.environ.get('EMERGENT_LLM_KEY')
        if not api_key:
            logger.warning("EMERGENT_LLM_KEY not set, falling back to scraping")
            return await extract_with_scraping(url)
        
        chat = LlmChat(
            api_key=api_key,
            session_id=f"extract_{uuid.uuid4().hex[:8]}",
            system_message="""You are a product data extractor. Extract product information from webpage content.
            Return ONLY a JSON object with these fields:
            - title: Product title/name
            - description: Brief product description
            - price: Numeric price value (no currency symbol)
            - currency: Currency code (USD, EUR, etc.)
            - image_url: Product image URL if found
            
            If a field cannot be determined, use null."""
        ).with_model("openai", "gpt-5.2")
        
        user_message = UserMessage(
            text=f"Extract product information from this webpage content:\n\n{text_content}"
        )
        
        response_text = await chat.send_message(user_message)
        
        # Parse JSON response
        import json
        # Clean response
        response_text = response_text.strip()
        if response_text.startswith('```'):
            response_text = re.sub(r'^```\w*\n?', '', response_text)
            response_text = re.sub(r'\n?```$', '', response_text)
        
        data = json.loads(response_text)
        
        return ExtractedData(
            title=data.get('title'),
            description=data.get('description'),
            price=float(data['price']) if data.get('price') else None,
            currency=data.get('currency', 'USD'),
            image_url=data.get('image_url')
        )
    except Exception as e:
        logger.error(f"AI extraction error for {url}: {e}")
        # Fallback to scraping
        return await extract_with_scraping(url)

# ==================== ITEM ENDPOINTS ====================

@api_router.post("/items", status_code=201)
async def create_item(item_req: CreateItemRequest, user: User = Depends(get_current_user)):
    """Create a new tracked item"""
    # Extract data based on method
    if item_req.extraction_method == "ai":
        extracted = await extract_with_ai(item_req.url)
    else:
        extracted = await extract_with_scraping(item_req.url)
    
    item = TrackedItem(
        user_id=user.user_id,
        url=item_req.url,
        title=extracted.title or "Unknown Product",
        description=extracted.description,
        image_url=extracted.image_url,
        current_price=extracted.price,
        currency=extracted.currency,
        extraction_method=item_req.extraction_method,
        notification_channels=item_req.notification_channels,
        notification_endpoint=item_req.notification_endpoint,
        last_checked=datetime.now(timezone.utc)
    )
    
    item_dict = item.model_dump()
    item_dict['created_at'] = item_dict['created_at'].isoformat()
    item_dict['updated_at'] = item_dict['updated_at'].isoformat()
    item_dict['last_checked'] = item_dict['last_checked'].isoformat() if item_dict['last_checked'] else None
    
    await db.tracked_items.insert_one(item_dict)
    
    # Save initial price to history
    if extracted.price:
        history = PriceHistory(
            item_id=item.item_id,
            price=extracted.price,
            currency=extracted.currency
        )
        history_dict = history.model_dump()
        history_dict['checked_at'] = history_dict['checked_at'].isoformat()
        await db.price_history.insert_one(history_dict)
    
    return {**item_dict, "_id": None}

@api_router.get("/items")
async def get_items(user: User = Depends(get_current_user)):
    """Get all tracked items for current user"""
    items = await db.tracked_items.find(
        {"user_id": user.user_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return items

@api_router.get("/items/{item_id}")
async def get_item(item_id: str, user: User = Depends(get_current_user)):
    """Get a specific tracked item"""
    item = await db.tracked_items.find_one(
        {"item_id": item_id, "user_id": user.user_id},
        {"_id": 0}
    )
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    return item

@api_router.put("/items/{item_id}")
async def update_item(item_id: str, update: UpdateItemRequest, user: User = Depends(get_current_user)):
    """Update a tracked item"""
    item = await db.tracked_items.find_one(
        {"item_id": item_id, "user_id": user.user_id}
    )
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    await db.tracked_items.update_one(
        {"item_id": item_id},
        {"$set": update_data}
    )
    
    updated_item = await db.tracked_items.find_one(
        {"item_id": item_id},
        {"_id": 0}
    )
    
    return updated_item

@api_router.delete("/items/{item_id}")
async def delete_item(item_id: str, user: User = Depends(get_current_user)):
    """Delete a tracked item"""
    result = await db.tracked_items.delete_one(
        {"item_id": item_id, "user_id": user.user_id}
    )
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Also delete price history
    await db.price_history.delete_many({"item_id": item_id})
    
    return {"message": "Item deleted successfully"}

@api_router.post("/items/{item_id}/check")
async def check_item_price(item_id: str, user: User = Depends(get_current_user)):
    """Manually check price for an item"""
    item = await db.tracked_items.find_one(
        {"item_id": item_id, "user_id": user.user_id}
    )
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Extract new data
    if item.get('extraction_method') == "ai":
        extracted = await extract_with_ai(item['url'])
    else:
        extracted = await extract_with_scraping(item['url'])
    
    old_price = item.get('current_price')
    new_price = extracted.price
    price_changed = old_price is not None and new_price is not None and old_price != new_price
    
    # Update item
    update_data = {
        'current_price': new_price,
        'last_checked': datetime.now(timezone.utc).isoformat(),
        'updated_at': datetime.now(timezone.utc).isoformat()
    }
    
    if extracted.title:
        update_data['title'] = extracted.title
    if extracted.description:
        update_data['description'] = extracted.description
    if extracted.image_url:
        update_data['image_url'] = extracted.image_url
    
    await db.tracked_items.update_one(
        {"item_id": item_id},
        {"$set": update_data}
    )
    
    # Save to history
    if new_price:
        history = PriceHistory(
            item_id=item_id,
            price=new_price,
            currency=extracted.currency
        )
        history_dict = history.model_dump()
        history_dict['checked_at'] = history_dict['checked_at'].isoformat()
        await db.price_history.insert_one(history_dict)
    
    # Send notification if price changed
    if price_changed:
        await send_notification(item, old_price, new_price)
    
    updated_item = await db.tracked_items.find_one(
        {"item_id": item_id},
        {"_id": 0}
    )
    
    return {
        "item": updated_item,
        "price_changed": price_changed,
        "old_price": old_price,
        "new_price": new_price
    }

@api_router.get("/items/{item_id}/history")
async def get_price_history(item_id: str, user: User = Depends(get_current_user)):
    """Get price history for an item"""
    # Verify ownership
    item = await db.tracked_items.find_one(
        {"item_id": item_id, "user_id": user.user_id}
    )
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    history = await db.price_history.find(
        {"item_id": item_id},
        {"_id": 0}
    ).sort("checked_at", 1).to_list(1000)
    
    return history

# ==================== NOTIFICATION SERVICE ====================

async def send_notification(item: dict, old_price: float, new_price: float):
    """Send notification about price change"""
    endpoint = item.get('notification_endpoint')
    if not endpoint:
        logger.info(f"No notification endpoint for item {item.get('item_id')}")
        return
    
    channels = item.get('notification_channels', ['email'])
    
    payload = {
        "item_id": item.get('item_id'),
        "url": item.get('url'),
        "title": item.get('title'),
        "old_price": old_price,
        "new_price": new_price,
        "currency": item.get('currency', 'USD'),
        "price_change": new_price - old_price,
        "price_change_percent": ((new_price - old_price) / old_price) * 100 if old_price else 0,
        "channels": channels,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client_http:
            response = await client_http.post(endpoint, json=payload)
            logger.info(f"Notification sent to {endpoint}: {response.status_code}")
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")

# ==================== PREVIEW ENDPOINT ====================

@api_router.post("/preview")
async def preview_extraction(request: Request, user: User = Depends(get_current_user)):
    """Preview extraction for a URL before creating item"""
    body = await request.json()
    url = body.get('url')
    method = body.get('method', 'scraping')
    
    if not url:
        raise HTTPException(status_code=400, detail="URL required")
    
    if method == "ai":
        extracted = await extract_with_ai(url)
    else:
        extracted = await extract_with_scraping(url)
    
    return extracted.model_dump()

# ==================== ROOT ENDPOINT ====================

@api_router.get("/")
async def root():
    return {"message": "Vigil API - Price Tracking Service"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
