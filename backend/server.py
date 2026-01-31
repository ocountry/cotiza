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
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
        }
        
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client_http:
            response = await client_http.get(url, headers=headers)
            
            # If blocked (403, 503, etc.), try fallback
            if response.status_code in [403, 503, 429]:
                logger.warning(f"Site {domain} returned {response.status_code}, trying fallback")
                return await extract_with_api_fallback(url)
            
            response.raise_for_status()
            
            html_text = response.text
            
            # Check if blocked by CloudFront or similar
            if '403 ERROR' in html_text or 'Request blocked' in html_text or len(html_text) < 1000:
                logger.warning(f"Site {domain} blocked direct access, trying fallback")
                return await extract_with_api_fallback(url)
            
            soup = BeautifulSoup(html_text, 'html.parser')
            
            # Default currency for Chilean sites
            default_currency = "CLP" if '.cl' in domain else "USD"
            
            # ========== TITLE EXTRACTION ==========
            title = None
            
            # Try og:title first
            og_title = soup.find('meta', property='og:title')
            if og_title and og_title.get('content'):
                title = og_title.get('content').strip()
                if '|' in title:
                    title = title.split('|')[0].strip()
                logger.debug(f"Title from og:title: {title}")
            
            # Try title tag
            if not title:
                title_tag = soup.find('title')
                if title_tag:
                    title = title_tag.get_text(strip=True)
                    if '|' in title:
                        title = title.split('|')[0].strip()
                    elif ' - ' in title:
                        title = title.split(' - ')[0].strip()
                    logger.debug(f"Title from title tag: {title}")
            
            # ========== PRICE EXTRACTION ==========
            all_prices = []
            currency = default_currency
            
            # Method 1: Search for JSON price patterns in raw HTML
            price_patterns = [
                r'"price"\s*:\s*"(\d{4,})"',      # "price":"69990"
                r'"price"\s*:\s*(\d{4,})[,}\]]',   # "price":69990,
                r'"lowPrice"\s*:\s*"?(\d{4,})"?',  # lowPrice
                r'"salePrice"\s*:\s*"?(\d{4,})"?', # salePrice  
            ]
            
            for pattern in price_patterns:
                matches = re.findall(pattern, html_text)
                for m in matches:
                    try:
                        p = float(m)
                        if p > 1000:  # Reasonable price threshold
                            all_prices.append(p)
                    except:
                        pass
            
            logger.debug(f"Prices from HTML patterns: {all_prices[:5]}")
            
            # Method 2: JSON-LD structured data
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    import json
                    data = json.loads(script.string)
                    items = data if isinstance(data, list) else [data]
                    
                    for item in items:
                        if not isinstance(item, dict):
                            continue
                        offers = item.get('offers', {})
                        offers_list = offers if isinstance(offers, list) else [offers]
                        
                        for offer in offers_list:
                            if isinstance(offer, dict):
                                for key in ['price', 'lowPrice', 'salePrice']:
                                    val = offer.get(key)
                                    if val:
                                        if isinstance(val, str):
                                            val = val.replace('.', '').replace(',', '.')
                                        try:
                                            p = float(val)
                                            if p > 1000:
                                                all_prices.append(p)
                                        except:
                                            pass
                except:
                    pass
            
            logger.debug(f"All found prices: {all_prices[:10]}")
            
            # Pick the lowest price (sale price)
            price = min(all_prices) if all_prices else None
            
            # ========== IMAGE EXTRACTION ==========
            image_url = None
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                image_url = og_image.get('content')
            
            # ========== DESCRIPTION ==========
            description = None
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                description = meta_desc.get('content')[:500]
            
            logger.info(f"Final extraction: title={title}, price={price}, currency={currency}")
            
            return ExtractedData(
                title=title[:200] if title else None,
                description=description,
                price=price,
                currency=currency,
                image_url=image_url
            )
    except httpx.HTTPStatusError as e:
        if e.response.status_code in [403, 503, 429]:
            logger.warning(f"HTTP {e.response.status_code} for {url}, trying fallback")
            return await extract_with_api_fallback(url)
        logger.error(f"HTTP error for {url}: {e}")
        return ExtractedData()
    except Exception as e:
        logger.error(f"Scraping error for {url}: {e}")
        return ExtractedData()


async def extract_with_api_fallback(url: str) -> ExtractedData:
    """Fallback extraction using external API for sites with anti-bot protection"""
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()
        default_currency = "CLP" if '.cl' in domain else "USD"
        
        # Use Jina reader API
        api_url = f"https://r.jina.ai/{url}"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(api_url)
            
            if response.status_code != 200:
                logger.warning(f"Jina API failed with status {response.status_code}")
                return ExtractedData()
            
            content = response.text
            
            # Check if we got a real page or an error
            if '403 ERROR' in content or 'Request blocked' in content:
                logger.warning(f"Site {domain} is protected. Use AI extraction method for better results.")
                return ExtractedData(
                    title=f"Protected site ({domain})",
                    description="This site has anti-bot protection. Try using AI extraction method instead.",
                    price=None,
                    currency=default_currency,
                    image_url=None
                )
            
            # Extract title from content
            title = None
            title_match = re.search(r'^Title:\s*(.+)$', content, re.MULTILINE)
            if title_match:
                title = title_match.group(1).strip()
                if '|' in title:
                    title = title.split('|')[0].strip()
            
            # Extract price - look for CLP format
            price = None
            # Chilean price patterns: $ 339.990 or $339.990
            price_patterns = [
                r'\$\s*([\d]{1,3}(?:\.[\d]{3})+)(?!\d)',  # $ 339.990
                r'(\d{4,})\s*(?:CLP|pesos)',  # 339990 CLP
            ]
            
            all_prices = []
            for pattern in price_patterns:
                matches = re.findall(pattern, content)
                for m in matches:
                    try:
                        # Remove dots (thousand separators)
                        clean_price = m.replace('.', '')
                        p = float(clean_price)
                        if p > 1000:
                            all_prices.append(p)
                    except:
                        pass
            
            if all_prices:
                price = min(all_prices)  # Get lowest (sale) price
            
            # Extract description
            description = None
            desc_match = re.search(r'^Description:\s*(.+)$', content, re.MULTILINE)
            if desc_match:
                description = desc_match.group(1).strip()[:500]
            
            # Extract image
            image_url = None
            img_match = re.search(r'(https?://[^\s]+\.(?:jpg|jpeg|png|webp))', content, re.IGNORECASE)
            if img_match:
                image_url = img_match.group(1)
            
            logger.info(f"API fallback extraction: title={title}, price={price}")
            
            return ExtractedData(
                title=title[:200] if title else None,
                description=description,
                price=price,
                currency=default_currency,
                image_url=image_url
            )
    except Exception as e:
        logger.error(f"API fallback error for {url}: {e}")
        return ExtractedData()

async def extract_with_ai(url: str) -> ExtractedData:
    """Use AI to extract product info from webpage"""
    try:
        from urllib.parse import urlparse
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        domain = urlparse(url).netloc.lower()
        default_currency = "CLP" if '.cl' in domain else "USD"
        
        # Try to get page content - first attempt direct scraping
        text_content = None
        
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client_http:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
                response = await client_http.get(url, headers=headers)
                
                if response.status_code == 200 and len(response.text) > 2000:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Remove scripts and styles
                    for tag in soup(['script', 'style', 'noscript']):
                        tag.decompose()
                    
                    text_content = soup.get_text(separator=' ', strip=True)[:8000]
        except:
            pass
        
        # If direct scraping failed, try Jina reader
        if not text_content or len(text_content) < 500:
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    jina_response = await client.get(f"https://r.jina.ai/{url}")
                    if jina_response.status_code == 200:
                        text_content = jina_response.text[:8000]
            except:
                pass
        
        if not text_content or len(text_content) < 100:
            logger.warning(f"Could not get content for {url}")
            return ExtractedData()
        
        api_key = os.environ.get('EMERGENT_LLM_KEY')
        if not api_key:
            logger.warning("EMERGENT_LLM_KEY not set")
            return ExtractedData()
        
        chat = LlmChat(
            api_key=api_key,
            session_id=f"extract_{uuid.uuid4().hex[:8]}",
            system_message=f"""You are a product data extractor for e-commerce sites. 
            Extract product information from the webpage content.
            The site domain is {domain}, so the currency is likely {default_currency}.
            
            For Chilean prices (CLP), prices are typically in the format $XX.XXX or $XXX.XXX (dots as thousand separators, no decimals).
            For example: $339.990 means 339990 CLP, $69.990 means 69990 CLP.
            
            Return ONLY a valid JSON object with these fields:
            - title: Product title/name (string)
            - description: Brief product description (string or null)
            - price: Numeric price value as INTEGER, no currency symbol, no dots (e.g., 339990 not "339.990")
            - currency: Currency code (CLP, USD, EUR, etc.)
            - image_url: Product image URL if found (string or null)
            
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
    pasted_content = body.get('pasted_content')  # Optional: user-provided content
    
    logger.info(f"Preview request: url={url}, method={method}, has_pasted_content={bool(pasted_content)}")
    
    if not url:
        raise HTTPException(status_code=400, detail="URL required")
    
    # If user provided pasted content, use AI to analyze it
    if pasted_content and len(pasted_content) > 100:
        extracted = await extract_from_pasted_content(url, pasted_content)
    elif method == "ai":
        extracted = await extract_with_ai(url)
    else:
        extracted = await extract_with_scraping(url)
    
    logger.info(f"Extraction result: title={extracted.title}, price={extracted.price}, currency={extracted.currency}")
    
    return extracted.model_dump()


async def extract_from_pasted_content(url: str, content: str) -> ExtractedData:
    """Extract product info from user-pasted content using AI"""
    try:
        from urllib.parse import urlparse
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        domain = urlparse(url).netloc.lower()
        default_currency = "CLP" if '.cl' in domain else "USD"
        
        api_key = os.environ.get('EMERGENT_LLM_KEY')
        if not api_key:
            logger.warning("EMERGENT_LLM_KEY not set")
            return ExtractedData()
        
        chat = LlmChat(
            api_key=api_key,
            session_id=f"extract_{uuid.uuid4().hex[:8]}",
            system_message=f"""You are a product data extractor for e-commerce sites. 
            Extract product information from the user-provided webpage content.
            The site domain is {domain}, so the currency is likely {default_currency}.
            
            For Chilean prices (CLP), prices are in format $XX.XXX or $XXX.XXX (dots = thousands, no decimals).
            Example: $339.990 = 339990 CLP, $69.990 = 69990 CLP.
            
            Return ONLY a valid JSON object:
            {{"title": "product name", "description": "brief description or null", "price": numeric_integer, "currency": "CLP", "image_url": "url or null"}}
            
            Price must be an INTEGER without dots or separators."""
        ).with_model("openai", "gpt-5.2")
        
        user_message = UserMessage(
            text=f"Extract product info from this content:\n\n{content[:8000]}"
        )
        
        response_text = await chat.send_message(user_message)
        
        # Parse JSON response
        import json
        response_text = response_text.strip()
        if response_text.startswith('```'):
            response_text = re.sub(r'^```\w*\n?', '', response_text)
            response_text = re.sub(r'\n?```$', '', response_text)
        
        data = json.loads(response_text)
        
        return ExtractedData(
            title=data.get('title'),
            description=data.get('description'),
            price=float(data['price']) if data.get('price') else None,
            currency=data.get('currency', default_currency),
            image_url=data.get('image_url')
        )
    except Exception as e:
        logger.error(f"Pasted content extraction error: {e}")
        return ExtractedData()

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
