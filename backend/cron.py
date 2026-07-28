"""Price check cron job - periodically checks prices for all active tracked items."""

import asyncio
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import db, logger, PRICE_CHECK_INTERVAL_HOURS
from models import PriceHistory
from scraping import extract_with_scraping
from llm import extract_with_ai
from notifications import send_notification

scheduler = AsyncIOScheduler()


async def check_all_prices():
    """Cron job to check prices for all active tracked items."""
    logger.info("=== Starting scheduled price check ===")

    try:
        items = await db.tracked_items.find({"is_active": True}).to_list(1000)
        logger.info(f"Found {len(items)} active items to check")

        for item in items:
            try:
                await check_single_item_price(item)
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Error checking item {item.get('item_id')}: {e}")
                continue

        logger.info("=== Scheduled price check completed ===")
    except Exception as e:
        logger.error(f"Price check cron error: {e}")


async def check_single_item_price(item: dict):
    """Check price for a single item and notify if changed."""
    item_id = item.get('item_id')
    url = item.get('url')
    old_price = item.get('current_price')
    extraction_method = item.get('extraction_method', 'scraping')

    logger.info(f"Checking price for: {item.get('title', url)[:50]}...")

    if extraction_method == "ai":
        extracted = await extract_with_ai(url)
    else:
        extracted = await extract_with_scraping(url)

    new_price = extracted.price

    await db.tracked_items.update_one(
        {"item_id": item_id},
        {"$set": {"last_checked": datetime.now(timezone.utc).isoformat()}},
    )

    if new_price is None:
        logger.warning(f"Could not extract price for item {item_id}")
        return

    if old_price is not None and new_price != old_price:
        logger.info(f"Price changed for {item_id}: {old_price} -> {new_price}")

        await db.tracked_items.update_one(
            {"item_id": item_id},
            {"$set": {
                "current_price": new_price,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }},
        )

        history = PriceHistory(
            item_id=item_id,
            price=new_price,
            currency=item.get('currency', 'USD'),
        )
        history_dict = history.model_dump()
        history_dict['checked_at'] = history_dict['checked_at'].isoformat()
        await db.price_history.insert_one(history_dict)

        user_doc = await db.users.find_one(
            {"user_id": item.get('user_id')},
            {"_id": 0},
        )
        if user_doc:
            await send_notification(item, old_price, new_price, user_doc)
    else:
        logger.debug(f"No price change for {item_id}: {old_price}")


def start_scheduler():
    """Start the price check scheduler."""
    scheduler.add_job(
        check_all_prices,
        trigger=IntervalTrigger(hours=PRICE_CHECK_INTERVAL_HOURS),
        id="price_check_job",
        name="Periodic Price Check",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Price check scheduler started - running every {PRICE_CHECK_INTERVAL_HOURS} hours")


def shutdown_scheduler():
    """Shutdown the scheduler."""
    scheduler.shutdown(wait=False)
    logger.info("Scheduler shutdown")