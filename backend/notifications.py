"""Notification service for price change alerts."""

import httpx
from datetime import datetime, timezone

from config import db, logger, NOTIFICATION_WEBHOOK_URL


async def send_notification(item: dict, old_price: float, new_price: float, user: dict):
    """Send notification about price change via system webhook."""
    if not NOTIFICATION_WEBHOOK_URL:
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
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client_http:
            response = await client_http.post(NOTIFICATION_WEBHOOK_URL, json=payload)
            logger.info(f"Notification sent to webhook: {response.status_code}")
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")