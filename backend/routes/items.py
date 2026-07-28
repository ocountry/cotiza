"""Items API routes - CRUD, price check, preview, and history."""

from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime, timezone

from config import db, logger, PRICE_CHECK_INTERVAL_HOURS
from models import (
    TrackedItem, CreateItemRequest, UpdateItemRequest,
    PriceHistory, ExtractedData,
)
from auth import get_current_user
from scraping import extract_with_scraping
from llm import extract_with_ai, extract_from_pasted_content
from notifications import send_notification

router = APIRouter(prefix="/api", tags=["items"])


# ==================== ITEM CRUD ====================


@router.post("/items", status_code=201)
async def create_item(item_req: CreateItemRequest, user=Depends(get_current_user)):
    """Create a new tracked item."""
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
        notes=item_req.notes,
        last_checked=datetime.now(timezone.utc),
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
            currency=extracted.currency,
        )
        history_dict = history.model_dump()
        history_dict['checked_at'] = history_dict['checked_at'].isoformat()
        await db.price_history.insert_one(history_dict)

    return {**item_dict, "_id": None}


@router.get("/items")
async def get_items(user=Depends(get_current_user)):
    """Get all tracked items for current user."""
    items = await db.tracked_items.find(
        {"user_id": user.user_id},
        {"_id": 0},
    ).sort("created_at", -1).to_list(100)
    return items


@router.get("/items/{item_id}")
async def get_item(item_id: str, user=Depends(get_current_user)):
    """Get a specific tracked item."""
    item = await db.tracked_items.find_one(
        {"item_id": item_id, "user_id": user.user_id},
        {"_id": 0},
    )
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.put("/items/{item_id}")
async def update_item(
    item_id: str,
    update: UpdateItemRequest,
    user=Depends(get_current_user),
):
    """Update a tracked item."""
    item = await db.tracked_items.find_one(
        {"item_id": item_id, "user_id": user.user_id},
    )
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()

    await db.tracked_items.update_one(
        {"item_id": item_id},
        {"$set": update_data},
    )

    updated_item = await db.tracked_items.find_one(
        {"item_id": item_id},
        {"_id": 0},
    )
    return updated_item


@router.delete("/items/{item_id}")
async def delete_item(item_id: str, user=Depends(get_current_user)):
    """Delete a tracked item."""
    result = await db.tracked_items.delete_one(
        {"item_id": item_id, "user_id": user.user_id},
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")

    await db.price_history.delete_many({"item_id": item_id})
    return {"message": "Item deleted successfully"}


# ==================== PRICE CHECK ====================


@router.post("/items/{item_id}/check")
async def check_item_price(item_id: str, user=Depends(get_current_user)):
    """Manually check price for an item."""
    item = await db.tracked_items.find_one(
        {"item_id": item_id, "user_id": user.user_id},
    )
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if item.get('extraction_method') == "ai":
        extracted = await extract_with_ai(item['url'])
    else:
        extracted = await extract_with_scraping(item['url'])

    old_price = item.get('current_price')
    new_price = extracted.price
    price_changed = old_price is not None and new_price is not None and old_price != new_price

    update_data = {
        'current_price': new_price,
        'last_checked': datetime.now(timezone.utc).isoformat(),
        'updated_at': datetime.now(timezone.utc).isoformat(),
    }

    if extracted.title:
        update_data['title'] = extracted.title
    if extracted.description:
        update_data['description'] = extracted.description
    if extracted.image_url:
        update_data['image_url'] = extracted.image_url

    await db.tracked_items.update_one(
        {"item_id": item_id},
        {"$set": update_data},
    )

    if new_price:
        history = PriceHistory(
            item_id=item_id,
            price=new_price,
            currency=extracted.currency,
        )
        history_dict = history.model_dump()
        history_dict['checked_at'] = history_dict['checked_at'].isoformat()
        await db.price_history.insert_one(history_dict)

    if price_changed:
        user_doc = await db.users.find_one({"user_id": user.user_id}, {"_id": 0})
        await send_notification(item, old_price, new_price, user_doc)

    updated_item = await db.tracked_items.find_one(
        {"item_id": item_id},
        {"_id": 0},
    )

    return {
        "item": updated_item,
        "price_changed": price_changed,
        "old_price": old_price,
        "new_price": new_price,
    }


@router.get("/items/{item_id}/history")
async def get_price_history(item_id: str, user=Depends(get_current_user)):
    """Get price history for an item."""
    item = await db.tracked_items.find_one(
        {"item_id": item_id, "user_id": user.user_id},
    )
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    history = await db.price_history.find(
        {"item_id": item_id},
        {"_id": 0},
    ).sort("checked_at", 1).to_list(1000)
    return history


# ==================== PREVIEW ====================


@router.post("/preview")
async def preview_extraction(request: Request, user=Depends(get_current_user)):
    """Preview extraction for a URL before creating item."""
    body = await request.json()
    url = body.get('url')
    method = body.get('method', 'scraping')
    pasted_content = body.get('pasted_content')

    logger.info(f"Preview request: url={url}, method={method}, has_pasted_content={bool(pasted_content)}")

    if not url:
        raise HTTPException(status_code=400, detail="URL required")

    if pasted_content and len(pasted_content) > 100:
        extracted = await extract_from_pasted_content(url, pasted_content)
    elif method == "ai":
        extracted = await extract_with_ai(url)
    else:
        extracted = await extract_with_scraping(url)

    logger.info(f"Extraction result: title={extracted.title}, price={extracted.price}, currency={extracted.currency}")
    return extracted.model_dump()


# ==================== CRON STATUS ====================


@router.get("/cron/status")
async def get_cron_status():
    """Get the status of the price check cron job."""
    from cron import scheduler
    jobs = scheduler.get_jobs()

    return {
        "scheduler_running": scheduler.running,
        "interval_hours": interval_hours,
        "jobs": [
            {
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            }
            for job in jobs
        ],
    }


@router.post("/cron/trigger")
async def trigger_price_check(user=Depends(get_current_user)):
    """Manually trigger a price check for all items."""
    import asyncio
    from cron import check_all_prices
    asyncio.create_task(check_all_prices())
    return {"message": "Price check triggered", "status": "running"}