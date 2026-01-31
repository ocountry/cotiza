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

class UpdateItemRequest(BaseModel):
    notification_channels: Optional[List[str]] = None
    is_active: Optional[bool] = None
    extraction_method: Optional[str] = None

class UpdateUserProfileRequest(BaseModel):
    notification_email: Optional[str] = None
    notification_whatsapp: Optional[str] = None
    notification_telegram: Optional[str] = None
    notification_sms: Optional[str] = None

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

@api_router.put("/auth/profile")
async def update_profile(update: UpdateUserProfileRequest, user: User = Depends(get_current_user)):
    """Update user notification settings"""
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    
    if update_data:
        await db.users.update_one(
            {"user_id": user.user_id},
            {"$set": update_data}
        )
    
    updated_user = await db.users.find_one(
        {"user_id": user.user_id},
        {"_id": 0}
    )
    
    return updated_user

# ==================== EXTRACTION SERVICES ====================

def parse_price_and_currency(text: str) -> tuple:
    """
    Parse price from text supporting multiple currency formats:
    - USD: $1,299.99 or $1299.99
    - CLP: $69.990 or $1.299.990 (dots as thousand separators, no decimals)
    - EUR: €1.299,99 or 1.299,99 €
    - General: detects currency symbol and format
    """
    if not text:
        return None, "USD"
    
    # Clean the text
    text = text.strip()
    
    # Currency detection based on domain hints in text or common patterns
    detected_currency = "USD"
    
    # Check for Chilean peso indicators
    clp_indicators = ['sodimac', 'falabella', 'mercadolibre.cl', 'paris.cl', 'ripley.cl', 'lider.cl', 'clp', 'pesos chilenos']
    text_lower = text.lower()
    
    for indicator in clp_indicators:
        if indicator in text_lower:
            detected_currency = "CLP"
            break
    
    # If we see a price pattern like $XX.XXX (dot thousands, 3 digits after dot) it's likely CLP
    clp_pattern = r'\$\s*[\d]{1,3}(?:\.[\d]{3})+(?!\d|,)'
    if re.search(clp_pattern, text):
        detected_currency = "CLP"
    
    # Other currency detection
    if detected_currency == "USD":
        currency_patterns = {
            'EUR': [r'€', r'\bEUR\b', r'euros?'],
            'GBP': [r'£', r'\bGBP\b', r'pounds?'],
            'MXN': [r'\bMXN\b', r'pesos?\s*mexicanos?'],
            'ARS': [r'\bARS\b', r'pesos?\s*argentinos?'],
            'BRL': [r'R\$', r'\bBRL\b', r'reais'],
            'USD': [r'\bUSD\b', r'US\$', r'U\.S\.\s*dollars?'],
        }
        
        for curr, patterns in currency_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    detected_currency = curr
                    break
            if detected_currency != "USD":
                break
    
    # Price extraction patterns - order matters!
    price = None
    
    # Pattern 1: CLP format $69.990 or $1.299.990 (dots as thousand separators)
    clp_match = re.search(r'\$\s*([\d]{1,3}(?:\.[\d]{3})+)(?!\d|,)', text)
    if clp_match:
        price_str = clp_match.group(1).replace('.', '')
        try:
            price = float(price_str)
            if detected_currency == "USD":
                detected_currency = "CLP"
        except ValueError:
            pass
    
    # Pattern 2: US format $1,299.99 (comma thousands, dot decimal)
    if price is None:
        us_match = re.search(r'\$\s*([\d]{1,3}(?:,[\d]{3})*(?:\.[\d]{1,2})?)(?!\d)', text)
        if us_match:
            price_str = us_match.group(1).replace(',', '')
            try:
                price = float(price_str)
            except ValueError:
                pass
    
    # Pattern 3: European format €1.299,99 (dot thousands, comma decimal)
    if price is None:
        eu_match = re.search(r'€\s*([\d]{1,3}(?:\.[\d]{3})*),(\d{1,2})(?!\d)', text)
        if eu_match:
            integer_part = eu_match.group(1).replace('.', '')
            decimal_part = eu_match.group(2)
            try:
                price = float(f"{integer_part}.{decimal_part}")
                detected_currency = "EUR"
            except ValueError:
                pass
    
    # Pattern 4: Simple price $199.99 or $199
    if price is None:
        simple_match = re.search(r'[\$€£]\s*([\d]+(?:\.[\d]{1,2})?)(?!\d|\.)', text)
        if simple_match:
            try:
                price = float(simple_match.group(1))
            except ValueError:
                pass
    
    # Pattern 5: Just numbers with currency context
    if price is None:
        num_match = re.search(r'([\d]+(?:[.,][\d]+)?)', text)
        if num_match:
            price_str = num_match.group(1).replace(',', '.')
            try:
                price = float(price_str)
            except ValueError:
                pass
    
    return price, detected_currency


# Site-specific extractors
SITE_CONFIGS = {
    'sodimac.cl': {
        'price_selectors': ['[data-price]', '.price-value', '[class*="ProductPrice"]', '.product-price', 'script[type="application/ld+json"]'],
        'title_selectors': ['h1', '[class*="product-name"]', '[class*="ProductName"]'],
        'currency': 'CLP'
    },
    'mercadolibre.cl': {
        'price_selectors': ['[class*="price-tag"]', '.andes-money-amount', '[class*="ui-pdp-price"]', 'meta[itemprop="price"]'],
        'title_selectors': ['h1', '.ui-pdp-title'],
        'currency': 'CLP'
    },
    'falabella.com': {
        'price_selectors': ['[class*="price"]', '[data-testid*="price"]'],
        'title_selectors': ['h1', '[class*="product-name"]'],
        'currency': 'CLP'
    },
    'paris.cl': {
        'price_selectors': ['[class*="price"]', '.product-price'],
        'title_selectors': ['h1'],
        'currency': 'CLP'
    },
    'amazon': {
        'price_selectors': ['#priceblock_ourprice', '#priceblock_dealprice', '.a-price-whole', '[data-a-color="price"] .a-offscreen'],
        'title_selectors': ['#productTitle', 'h1'],
        'currency': 'USD'
    }
}

def get_site_config(url: str) -> dict:
    """Get site-specific configuration based on URL"""
    from urllib.parse import urlparse
    domain = urlparse(url).netloc.lower()
    
    for site_key, config in SITE_CONFIGS.items():
        if site_key in domain:
            return config
    return None


async def extract_with_scraping(url: str) -> ExtractedData:
    """Basic web scraping to extract product info"""
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()
        site_config = get_site_config(url)
        
        # Better headers for Chilean e-commerce sites
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client_http:
            response = await client_http.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Default currency based on domain
            default_currency = "CLP" if any(cl in domain for cl in ['.cl', 'chile']) else "USD"
            if site_config:
                default_currency = site_config.get('currency', default_currency)
            
            # Extract title - try multiple methods
            title = None
            
            # Method 1: og:title meta tag (most reliable for product pages)
            og_title = soup.find('meta', property='og:title')
            if og_title and og_title.get('content'):
                title = og_title.get('content').strip()[:200]
            
            # Method 2: title tag
            if not title:
                title_tag = soup.find('title')
                if title_tag:
                    raw_title = title_tag.get_text(strip=True)
                    # Clean up title (remove site name suffix like " | Sodimac Chile")
                    if '|' in raw_title:
                        title = raw_title.split('|')[0].strip()[:200]
                    elif ' - ' in raw_title:
                        title = raw_title.split(' - ')[0].strip()[:200]
                    else:
                        title = raw_title[:200]
            
            # Method 3: h1 and other selectors
            if not title or len(title) < 5:
                title_selectors = ['h1', '[class*="product-name"]', '[class*="ProductName"]', '[itemprop="name"]']
                if site_config:
                    title_selectors = site_config.get('title_selectors', []) + title_selectors
                
                for selector in title_selectors:
                    elem = soup.select_one(selector)
                    if elem:
                        candidate = elem.get_text(strip=True)[:200]
                        if candidate and len(candidate) > 5:
                            title = candidate
                            break
            
            # Method 4: Search in JSON data for product name
            if not title:
                name_pattern = r'"name"\s*:\s*"([^"]{10,100})"'
                name_matches = re.findall(name_pattern, response.text)
                # Filter out generic names
                for name in name_matches:
                    if name and len(name) > 10 and 'sodimac' not in name.lower() and 'category' not in name.lower():
                        title = name
                        break
            
            # Extract description
            description = None
            for selector in ['[class*="description"]', '[class*="product-desc"]', 'meta[name="description"]', '[class*="ProductDescription"]']:
                elem = soup.select_one(selector)
                if elem:
                    if elem.name == 'meta':
                        description = elem.get('content', '')[:500]
                    else:
                        description = elem.get_text(strip=True)[:500]
                    if description:
                        break
            
            # Collect ALL prices from different sources and pick the best one
            all_found_prices = []
            currency = default_currency
            
            # Source 1: JSON-LD scripts
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_ld_scripts:
                try:
                    import json
                    data = json.loads(script.string)
                    
                    items_to_check = data if isinstance(data, list) else [data]
                    
                    for item in items_to_check:
                        if not isinstance(item, dict):
                            continue
                            
                        offers = item.get('offers', item.get('Offers', {}))
                        offers_list = offers if isinstance(offers, list) else [offers] if isinstance(offers, dict) else []
                        
                        for offer in offers_list:
                            if isinstance(offer, dict):
                                for price_key in ['price', 'lowPrice', 'salePrice']:
                                    price_val = offer.get(price_key)
                                    if price_val:
                                        if isinstance(price_val, str):
                                            price_val = price_val.replace('.', '').replace(',', '.')
                                        try:
                                            p = float(price_val)
                                            if p > 100:  # Filter out tiny values
                                                all_found_prices.append(p)
                                                if offer.get('priceCurrency'):
                                                    currency = offer.get('priceCurrency')
                                        except:
                                            pass
                except Exception as json_err:
                    logger.debug(f"JSON-LD parse error: {json_err}")
                    continue
            
            # Source 2: Raw HTML JSON patterns (catches dynamic/JS prices)
            html_text = response.text
            price_json_patterns = [
                r'"price"\s*:\s*"(\d{4,})"',
                r'"price"\s*:\s*(\d{4,})[,}\]]',
                r'"lowPrice"\s*:\s*"?(\d{4,})"?',
                r'"salePrice"\s*:\s*"?(\d{4,})"?',
            ]
            
            for pattern in price_json_patterns:
                matches = re.findall(pattern, html_text)
                for m in matches:
                    try:
                        p = float(m)
                        if p > 100:
                            all_found_prices.append(p)
                    except:
                        pass
            
            # Source 3: HTML elements with price class/data
            price = None
            if not all_found_prices:
                price_selectors = [
                    '[class*="price"]', '[data-price]', '[itemprop="price"]',
                    '[class*="Price"]', '[class*="producto-precio"]', '[class*="ProductPrice"]'
                ]
                if site_config:
                    price_selectors = site_config.get('price_selectors', []) + price_selectors
                
                for selector in price_selectors:
                    elements = soup.select(selector)
                    for elem in elements:
                        if elem.get('data-price'):
                            try:
                                p = float(elem.get('data-price'))
                                if p > 100:
                                    all_found_prices.append(p)
                            except:
                                pass
                        if elem.get('content'):
                            try:
                                p = float(elem.get('content'))
                                if p > 100:
                                    all_found_prices.append(p)
                            except:
                                pass
                        
                        text = elem.get_text(strip=True)
                        if text:
                            parsed_price, parsed_currency = parse_price_and_currency(text + f" {domain}")
                            if parsed_price and parsed_price > 100:
                                all_found_prices.append(parsed_price)
                                if parsed_currency != "USD":
                                    currency = parsed_currency
            
            # Pick the best price: lowest (sale price) if we have multiple
            if all_found_prices:
                price = min(all_found_prices)
            
            # Last resort: search full page for price patterns
            if price is None:
                full_text = soup.get_text()
                # Add domain context for currency detection
                parsed_price, parsed_currency = parse_price_and_currency(full_text[:5000] + f" {domain}")
                if parsed_price:
                    price = parsed_price
                    currency = parsed_currency
            
            # Extract image
            image_url = None
            image_selectors = [
                'meta[property="og:image"]',
                '[class*="product"] img',
                '[class*="gallery"] img', 
                'img[itemprop="image"]',
                '[class*="ProductImage"] img',
                '.product-image img'
            ]
            
            for selector in image_selectors:
                elem = soup.select_one(selector)
                if elem:
                    if elem.name == 'meta':
                        image_url = elem.get('content')
                    else:
                        image_url = elem.get('src') or elem.get('data-src') or elem.get('data-lazy-src')
                    if image_url:
                        if not image_url.startswith('http'):
                            from urllib.parse import urljoin
                            image_url = urljoin(url, image_url)
                        # Skip placeholder images
                        if 'placeholder' not in image_url.lower() and 'default' not in image_url.lower():
                            break
                        else:
                            image_url = None
            
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
        user_doc = await db.users.find_one({"user_id": user.user_id}, {"_id": 0})
        await send_notification(item, old_price, new_price, user_doc)
    
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

async def send_notification(item: dict, old_price: float, new_price: float, user: dict):
    """Send notification about price change via system webhook"""
    webhook_url = os.environ.get('NOTIFICATION_WEBHOOK_URL')
    if not webhook_url:
        logger.warning("NOTIFICATION_WEBHOOK_URL not configured")
        return
    
    channels = item.get('notification_channels', ['email'])
    
    # Build notification targets from user profile
    notification_targets = {}
    if 'email' in channels and user.get('notification_email'):
        notification_targets['email'] = user.get('notification_email')
    if 'whatsapp' in channels and user.get('notification_whatsapp'):
        notification_targets['whatsapp'] = user.get('notification_whatsapp')
    if 'telegram' in channels and user.get('notification_telegram'):
        notification_targets['telegram'] = user.get('notification_telegram')
    if 'sms' in channels and user.get('notification_sms'):
        notification_targets['sms'] = user.get('notification_sms')
    
    if not notification_targets:
        logger.info(f"No notification targets configured for item {item.get('item_id')}")
        return
    
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
        "notification_targets": notification_targets,
        "user_id": user.get('user_id'),
        "user_name": user.get('name'),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client_http:
            response = await client_http.post(webhook_url, json=payload)
            logger.info(f"Notification sent to webhook: {response.status_code}")
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
