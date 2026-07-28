"""LLM-based product extraction service.

Supports any OpenAI-compatible API (OpenAI, Anthropic, local LLMs, etc.).
Configure via env vars:
- LLM_API_KEY: API key
- LLM_PROVIDER: provider name (for logging, default: openai)
- LLM_MODEL: model name (default: gpt-4o-mini)
- LLM_API_URL: API endpoint URL (default: https://api.openai.com/v1/chat/completions)
"""

import re
import json
import httpx
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from config import logger, LLM_API_KEY, LLM_MODEL, LLM_API_URL
from models import ExtractedData


async def extract_with_llm(text_content: str, domain: str, default_currency: str) -> ExtractedData:
    """Extract product info from text content using an LLM API."""
    if not LLM_API_KEY:
        logger.warning("LLM_API_KEY not set")
        return ExtractedData()

    system_prompt = f"""You are a product data extractor for e-commerce sites.
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

    user_prompt = f"Extract product information from this webpage content:\n\n{text_content[:8000]}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                LLM_API_URL,
                headers={
                    "Authorization": f"Bearer {LLM_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 1000,
                },
            )

            if response.status_code != 200:
                logger.error(f"LLM API error: {response.status_code} - {response.text}")
                return ExtractedData()

            result = response.json()
            content = result["choices"][0]["message"]["content"]

            content = content.strip()
            if content.startswith('```'):
                content = re.sub(r'^```\w*\n?', '', content)
                content = re.sub(r'\n?```$', '', content)

            data = json.loads(content)

            return ExtractedData(
                title=data.get('title'),
                description=data.get('description'),
                price=float(data['price']) if data.get('price') else None,
                currency=data.get('currency', 'USD'),
                image_url=data.get('image_url'),
            )
    except Exception as e:
        logger.error(f"LLM extraction error: {e}")
        return ExtractedData()


async def extract_with_ai(url: str) -> ExtractedData:
    """Use AI to extract product info from webpage."""
    try:
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

        return await extract_with_llm(text_content, domain, default_currency)

    except Exception as e:
        logger.error(f"AI extraction error for {url}: {e}")
        # Fallback to scraping
        from scraping import extract_with_scraping
        return await extract_with_scraping(url)


async def extract_from_pasted_content(url: str, content: str) -> ExtractedData:
    """Extract product info from user-pasted content using AI."""
    try:
        domain = urlparse(url).netloc.lower()
        default_currency = "CLP" if '.cl' in domain else "USD"
        return await extract_with_llm(content, domain, default_currency)
    except Exception as e:
        logger.error(f"Pasted content extraction error: {e}")
        return ExtractedData()