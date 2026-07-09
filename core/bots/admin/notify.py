"""Admin botga yangi buyurtma bildirishnomasi (API'dan chaqiriladi)."""
from __future__ import annotations

from core.bots.admin.keyboards import order_actions
from core.services import notify_service
from core.utils import order_summary_text


async def notify_new_order(order, currency: str = "so'm") -> int:
    """Yangi buyurtma haqida barcha adminlarga xabar yuboradi."""
    text = "🔔 <b>YANGI BUYURTMA!</b>\n\n" + order_summary_text(order, currency, for_admin=True)
    kb = order_actions(order.id, order.status)
    return await notify_service.notify_admins(text, kb)
