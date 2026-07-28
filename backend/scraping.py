"""Web scraping module for product price extraction.

Supports:
- Direct HTML scraping with BeautifulSoup + JSON-LD parsing
- Firecrawl API (cloud and self-hosted) for anti-bot protected sites
- Site-specific configurations for Chilean e-commerce
- Multi-currency price parsing (CLP, USD, EUR, etc.)
"""

import re
import json
import logging
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from config import (
    logger, FIRECRAWL_MODE, FIRECRAWL_API_KEY, FIRECRAWL_SELFHOSTED_URL,
)
from models import ExtractedData


# ==================== PRICE PARSING ====================


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

    text = text.strip()
    detected_currency = "USD"

    # Check for Chilean peso indicators
    clp_indicators = [
        'sodimac', 'falabella', 'mercadolibre.cl', 'paris.cl',
        'ripley.cl', 'lider.cl', 'clp', 'pesos chilenos',
    ]
    text_lower = text.lower()

    for indicator in clp_indicators:
        if indicator in text_lower:
            detected_currency = "CLP"
            break

    # CLP pattern: $XX.XXX (dot thousands, 3 digits after dot)
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

    # Price extraction patterns
    price = None

    # Pattern 1: CLP format $69.990 or $1.299.990
    clp_match = re.search(r'\$\s*([\d]{1,3}(?:\.[\d]{3})+)(?!\d|,)', text)
    if clp_match:
        price_str = clp_match.group(1).replace('.', '')
        try:
            price = float(price_str)
            if detected_currency == "USD":
                detected_currency = "CLP"
        except ValueError:
            pass

    # Pattern 2: US format $1,299.99
    if price is None:
        us_match = re.search(r'\$\s*([\d]{1,3}(?:,[\d]{3})*(?:\.[\d]{1,2})?)(?!\d)', text)
        if us_match:
            price_str = us_match.group(1).replace(',', '')
            try:
                price = float(price_str)
            except ValueError:
                pass

    # Pattern 3: European format €1.299,99
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


# ==================== SITE-SPECIFIC CONFIGURATION ====================


SITE_CONFIGS = {
    'sodimac.cl': {
        'price_selectors': ['[data-price]', '.price-value', '[class*="ProductPrice"]', '.product-price', 'script[type="application/ld+json"]'],
        'title_selectors': ['h1', '[class*="product-name"]', '[class*="ProductName"]'],
        'currency': 'CLP',
    },
    'mercadolibre.cl': {
        'price_selectors': ['[class*="price-tag"]', '.andes-money-amount', '[class*="ui-pdp-price"]', 'meta[itemprop="price"]'],
        'title_selectors': ['h1', '.ui-pdp-title'],
        'currency': 'CLP',
    },
    'falabella.com': {
        'price_selectors': ['[class*="price"]', '[data-testid*="price"]'],
        'title_selectors': ['h1', '[class*="product-name"]'],
        'currency': 'CLP',
    },
    'paris.cl': {
        'price_selectors': ['[class*="price"]', '.product-price'],
        'title_selectors': ['h1'],
        'currency': 'CLP',
    },
    'amazon': {
        'price_selectors': ['#priceblock_ourprice', '#priceblock_dealprice', '.a-price-whole', '[data-a-color="price"] .a-offscreen'],
        'title_selectors': ['#productTitle', 'h1'],
        'currency': 'USD',
    },
}


def get_site_config(url: str) -> dict:
    """Get site-specific configuration based on URL."""
    domain = urlparse(url).netloc.lower()
    for site_key, config in SITE_CONFIGS.items():
        if site_key in domain:
            return config
    return None


# ==================== DIRECT SCRAPING ====================


async def extract_with_scraping(url: str) -> ExtractedData:
    """Basic web scraping to extract product info."""
    try:
        domain = urlparse(url).netloc.lower()

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
        }

        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client_http:
            response = await client_http.get(url, headers=headers)

            if response.status_code in [403, 503, 429]:
                logger.warning(f"Site {domain} returned {response.status_code}, trying fallback")
                return await extract_with_api_fallback(url)

            response.raise_for_status()
            html_text = response.text

            if '403 ERROR' in html_text or 'Request blocked' in html_text or len(html_text) < 1000:
                logger.warning(f"Site {domain} blocked direct access, trying fallback")
                return await extract_with_api_fallback(url)

            soup = BeautifulSoup(html_text, 'html.parser')
            default_currency = "CLP" if '.cl' in domain else "USD"

            # ========== TITLE EXTRACTION ==========
            title = None
            og_title = soup.find('meta', property='og:title')
            if og_title and og_title.get('content'):
                title = og_title.get('content').strip()
                if '|' in title:
                    title = title.split('|')[0].strip()

            if not title:
                title_tag = soup.find('title')
                if title_tag:
                    title = title_tag.get_text(strip=True)
                    if '|' in title:
                        title = title.split('|')[0].strip()
                    elif ' - ' in title:
                        title = title.split(' - ')[0].strip()

            # ========== PRICE EXTRACTION ==========
            all_prices = []
            jsonld_price = None
            currency = default_currency

            # Method 1: JSON-LD structured data (HIGHEST PRIORITY)
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string)
                    items = data if isinstance(data, list) else [data]

                    for item in items:
                        if not isinstance(item, dict) or item.get('@type') != 'Product':
                            continue

                        offers = item.get('offers', {})
                        offers_list = offers if isinstance(offers, list) else [offers]

                        for offer in offers_list:
                            if isinstance(offer, dict):
                                for key in ['price', 'lowPrice', 'salePrice']:
                                    val = offer.get(key)
                                    if val:
                                        try:
                                            if isinstance(val, str):
                                                if '.' in val and val.replace('.', '').isdigit():
                                                    val = val.replace('.', '')
                                                elif ',' in val:
                                                    val = val.replace(',', '')
                                            p = float(val)
                                            if 1000 <= p <= 100000000:
                                                if jsonld_price is None:
                                                    jsonld_price = p
                                                all_prices.append(p)
                                        except:
                                            pass

                                if offer.get('priceCurrency'):
                                    currency = offer.get('priceCurrency')
                except:
                    pass

            if jsonld_price:
                price = jsonld_price
            else:
                # Method 2: Fallback to JSON price patterns in raw HTML
                price_patterns = [
                    r'"price"\s*:\s*"(\d{4,})"',
                    r'"price"\s*:\s*(\d{4,})[,}\]]',
                    r'"lowPrice"\s*:\s*"?(\d{4,})"?',
                    r'"salePrice"\s*:\s*"?(\d{4,})"?',
                ]
                for pattern in price_patterns:
                    matches = re.findall(pattern, html_text)
                    for m in matches:
                        try:
                            p = float(m)
                            if 1000 <= p <= 100000000:
                                all_prices.append(p)
                        except:
                            pass

                price = all_prices[0] if all_prices else None

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
                image_url=image_url,
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


# ==================== FIRECRAWL (ANTI-BOT PROTECTION) ====================


async def extract_with_api_fallback(url: str) -> ExtractedData:
    """Fallback extraction using Firecrawl API for sites with anti-bot protection."""
    try:
        domain = urlparse(url).netloc.lower()
        default_currency = "CLP" if '.cl' in domain else "USD"

        if FIRECRAWL_MODE == 'selfhosted':
            return await extract_with_firecrawl_selfhosted(url, domain, default_currency)
        else:
            return await extract_with_firecrawl_cloud(url, domain, default_currency)

    except Exception as e:
        logger.error(f"Firecrawl error for {url}: {e}")
        return ExtractedData()


async def extract_with_firecrawl_selfhosted(url: str, domain: str, default_currency: str) -> ExtractedData:
    """Extract using self-hosted Firecrawl instance."""
    try:
        if not FIRECRAWL_SELFHOSTED_URL:
            logger.warning("FIRECRAWL_SELFHOSTED_URL not set, falling back to cloud")
            return await extract_with_firecrawl_cloud(url, domain, default_currency)

        logger.info(f"Using Firecrawl SELF-HOSTED for: {domain}")

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                FIRECRAWL_SELFHOSTED_URL,
                json={"url": url, "formats": ["markdown"]},
                headers={"Content-Type": "application/json"},
            )

            if response.status_code != 200:
                logger.warning(f"Firecrawl self-hosted returned status {response.status_code}, falling back to cloud")
                return await extract_with_firecrawl_cloud(url, domain, default_currency)

            result = response.json()

            if result.get('success') == False:
                error_code = result.get('code', '')
                error_msg = result.get('error', '')
                antibot_errors = ['SCRAPE_DOCUMENT_ANTIBOT_ERROR', 'ANTIBOT', 'BLOCKED', 'CAPTCHA', 'ACCESS_DENIED', 'FORBIDDEN']
                should_fallback = any(err in error_code.upper() for err in antibot_errors) or \
                                  any(err.lower() in error_msg.lower() for err in ['anti-bot', 'blocked', 'captcha', 'forbidden'])

                if should_fallback:
                    logger.warning(f"Firecrawl self-hosted blocked ({error_code}), falling back to CLOUD")
                    return await extract_with_firecrawl_cloud(url, domain, default_currency)
                else:
                    logger.warning(f"Firecrawl self-hosted error: {error_code} - {error_msg}")
                    return ExtractedData()

            if not result.get('data'):
                return ExtractedData()

            data = result.get('data', {})
            markdown = data.get('markdown', '')
            metadata = data.get('metadata', {})

            title = metadata.get('title') or metadata.get('og:title') or metadata.get('ogTitle')
            if title and '|' in title:
                title = title.split('|')[0].strip()

            description = metadata.get('description') or metadata.get('og:description') or metadata.get('ogDescription')
            image_url = metadata.get('og:image') or metadata.get('ogImage')
            if not image_url:
                image_url = extract_image_from_markdown(markdown)

            price = extract_price_from_markdown(markdown, default_currency)

            return ExtractedData(
                title=title[:200] if title else None,
                description=description[:500] if description else None,
                price=price,
                currency=default_currency,
                image_url=image_url,
            )

    except Exception as e:
        logger.error(f"Firecrawl self-hosted error for {url}: {e}, falling back to cloud")
        return await extract_with_firecrawl_cloud(url, domain, default_currency)


async def extract_with_firecrawl_cloud(url: str, domain: str, default_currency: str) -> ExtractedData:
    """Extract using Firecrawl cloud SDK."""
    try:
        from firecrawl import FirecrawlApp

        if not FIRECRAWL_API_KEY:
            logger.warning("FIRECRAWL_API_KEY not set")
            return ExtractedData()

        logger.info(f"Using Firecrawl CLOUD for: {domain}")

        app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)
        result = app.scrape(url, formats=['markdown'])

        if not result:
            logger.warning(f"Firecrawl cloud returned empty result for {url}")
            return ExtractedData()

        markdown = result.markdown or ''
        metadata = result.metadata

        title = None
        if metadata:
            title = metadata.title or metadata.og_title
            if title and '|' in title:
                title = title.split('|')[0].strip()

        description = None
        if metadata:
            description = metadata.description or metadata.og_description

        image_url = None
        if metadata:
            image_url = metadata.og_image
        if not image_url:
            image_url = extract_image_from_markdown(markdown)

        price = extract_price_from_markdown(markdown, default_currency)

        return ExtractedData(
            title=title[:200] if title else None,
            description=description[:500] if description else None,
            price=price,
            currency=default_currency,
            image_url=image_url,
        )

    except Exception as e:
        logger.error(f"Firecrawl cloud error for {url}: {e}")
        return ExtractedData()


# ==================== MARKDOWN PRICE EXTRACTION ====================


def extract_price_from_markdown(markdown: str, default_currency: str) -> float:
    """Extract price from markdown content (Firecrawl output)."""
    price_pattern = r'\$\s*([\d]{1,3}(?:\.[\d]{3})+)'
    exclude_patterns = ['cuota', 'mensual', 'cae', 'costo total', 'financ']

    # First: context patterns (most reliable)
    context_patterns = [
        r'(?:carrito|cart|comprar|buy|añadir|agregar)[^$\n]{0,20}\$\s*([\d]{1,3}(?:\.[\d]{3})+)',
        r'\$\s*([\d]{1,3}(?:\.[\d]{3})+)\s*(?:\$[\d.,]+)?\s*(?:oferta|descuento|off|sale|-\d+%)',
    ]

    for ctx_pattern in context_patterns:
        match = re.search(ctx_pattern, markdown, re.IGNORECASE)
        if match:
            try:
                clean_price = match.group(1).replace('.', '')
                price = float(clean_price)
                start = max(0, match.start() - 50)
                end = min(len(markdown), match.end() + 50)
                nearby_context = markdown[start:end].lower()
                if any(exc in nearby_context for exc in exclude_patterns):
                    continue
                if 1000 <= price <= 100000000:
                    logger.info(f"Found price in context pattern: {price}")
                    return price
            except:
                pass

    # Second: find all prices and filter
    all_matches = list(re.finditer(price_pattern, markdown))
    valid_prices = []

    for match in all_matches:
        try:
            start = max(0, match.start() - 100)
            end = min(len(markdown), match.end() + 100)
            context = markdown[start:end].lower()

            if any(exc in context for exc in exclude_patterns):
                continue

            clean_price = match.group(1).replace('.', '')
            price = float(clean_price)

            if 5000 <= price <= 100000000:
                valid_prices.append(price)
        except:
            pass

    if valid_prices:
        if len(valid_prices) >= 2:
            first, second = valid_prices[0], valid_prices[1]
            if first > 50000 and second > 50000:
                ratio = max(first, second) / min(first, second)
                if ratio < 1.5:
                    return second

        return valid_prices[0]

    return None


def extract_image_from_markdown(markdown: str) -> str:
    """Extract product image URL from markdown."""
    img_pattern = r'!\[[^\]]*\]\((https?://[^\s\)]+\.(?:jpg|jpeg|png|webp|gif)(?:\?[^\s\)]*)?)\)'
    matches = re.findall(img_pattern, markdown, re.IGNORECASE)

    if len(matches) < 3:
        cdn_pattern = r'(https?://[^\s\)]+/product-medias/[^\s\)]+\.(?:jpg|jpeg|png|webp))'
        cdn_matches = re.findall(cdn_pattern, markdown, re.IGNORECASE)
        matches.extend(cdn_matches)

        prd_pattern = r'(https?://[^\s]+/prd-cl/[^\s\)]+\.(?:jpg|jpeg|png|webp))'
        prd_matches = re.findall(prd_pattern, markdown, re.IGNORECASE)
        matches.extend(prd_matches)

    if matches:
        for img_url in matches:
            img_lower = img_url.lower()
            if any(skip in img_lower for skip in ['icon', 'logo', 'banner', 'avatar', 'sprite', 'huincha', 'voladora']):
                continue
            if any(prod in img_lower for prod in ['product', 'prd-', '/prd/', 'item', 'sku', 'media']):
                return img_url

        for img_url in matches:
            if not any(skip in img_url.lower() for skip in ['icon', 'logo', 'banner', 'avatar', 'sprite', 'huincha']):
                return img_url

    return None