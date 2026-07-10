"""
Oddiy, bog'liqliksiz ko'p tilli (i18n) tizim: UZ / RU / EN.

UI matnlari shu yerda. Mahsulot/kategoriya nomlari do'kon tilida (admin kiritadi)
saqlanadi. Til topilmasa default (uz) ga, kalit topilmasa kalitning o'ziga qaytadi.
"""
from __future__ import annotations

from core.config import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES

TRANSLATIONS: dict[str, dict[str, str]] = {
    # ── Sotuv bot ──
    "btn_open_shop": {"uz": "🛍 Do'konni ochish", "ru": "🛍 Открыть магазин", "en": "🛍 Open shop"},
    "btn_my_orders": {"uz": "📦 Buyurtmalarim", "ru": "📦 Мои заказы", "en": "📦 My orders"},
    "btn_contact": {"uz": "☎️ Aloqa", "ru": "☎️ Контакты", "en": "☎️ Contact"},
    "btn_language": {"uz": "🌐 Til", "ru": "🌐 Язык", "en": "🌐 Language"},
    "btn_shop_address": {"uz": "📍 Do'kon manzili", "ru": "📍 Адрес магазина", "en": "📍 Shop address"},
    "tap_to_open": {
        "uz": "🛍 Do'kon katalogini ochish uchun quyidagi tugmani bosing 👇",
        "ru": "🛍 Нажмите кнопку ниже, чтобы открыть каталог магазина 👇",
        "en": "🛍 Tap the button below to open the shop catalog 👇",
    },
    "shop_address_none": {
        "uz": "Do'kon manzili hozircha kiritilmagan.",
        "ru": "Адрес магазина пока не указан.",
        "en": "The shop address is not set yet.",
    },
    "shop_address_caption": {
        "uz": "📍 <b>Do'kon manzili</b>\n{note}\n\n🗺 <a href=\"{link}\">Yandex xaritada ochish</a>",
        "ru": "📍 <b>Адрес магазина</b>\n{note}\n\n🗺 <a href=\"{link}\">Открыть в Яндекс.Картах</a>",
        "en": "📍 <b>Shop address</b>\n{note}\n\n🗺 <a href=\"{link}\">Open in Yandex Maps</a>",
    },
    "choose_language": {"uz": "Tilni tanlang:", "ru": "Выберите язык:", "en": "Choose language:"},
    "language_set": {"uz": "✅ Til o'zgartirildi.", "ru": "✅ Язык изменён.", "en": "✅ Language updated."},
    "no_orders": {"uz": "Sizda hali buyurtmalar yo'q.", "ru": "У вас пока нет заказов.", "en": "You have no orders yet."},
    "contact_info": {"uz": "☎️ Aloqa", "ru": "☎️ Контакты", "en": "☎️ Contact"},
    "shop_closed": {
        "uz": "⏰ Hozir do'kon yopiq. Ish vaqti: {hours}",
        "ru": "⏰ Магазин сейчас закрыт. Время работы: {hours}",
        "en": "⏰ The shop is currently closed. Hours: {hours}",
    },

    # ── Onboarding (telefon ulashish) ──
    "onboard_phone": {
        "uz": "Assalomu alaykum! 👋\nBuyurtma berishni boshlash uchun telefon raqamingizni ulashing.",
        "ru": "Здравствуйте! 👋\nЧтобы начать заказывать, поделитесь номером телефона.",
        "en": "Welcome! 👋\nShare your phone number to start ordering.",
    },
    "btn_share_phone": {
        "uz": "📱 Telefon raqamni ulashish",
        "ru": "📱 Поделиться номером",
        "en": "📱 Share phone number",
    },
    "onboard_need_contact": {
        "uz": "Iltimos, pastdagi «📱 Telefon raqamni ulashish» tugmasini bosing.",
        "ru": "Пожалуйста, нажмите кнопку «📱 Поделиться номером» ниже.",
        "en": "Please tap the «📱 Share phone number» button below.",
    },
    "onboard_thanks": {
        "uz": "Rahmat, {name}! ✅ Endi xarid qilishingiz mumkin.",
        "ru": "Спасибо, {name}! ✅ Теперь вы можете делать покупки.",
        "en": "Thank you, {name}! ✅ You can start shopping now.",
    },

    # ── Buyurtma statuslari (mijozga) ──
    "status_created": {"uz": "🆕 Buyurtmangiz qabul qilindi", "ru": "🆕 Заказ принят", "en": "🆕 Order received"},
    "status_confirmed": {"uz": "✅ Buyurtmangiz tasdiqlandi", "ru": "✅ Заказ подтверждён", "en": "✅ Order confirmed"},
    "status_preparing": {"uz": "👨‍🍳 Buyurtmangiz tayyorlanmoqda", "ru": "👨‍🍳 Заказ готовится", "en": "👨‍🍳 Your order is being prepared"},
    "status_on_way": {"uz": "🚗 Buyurtmangiz yo'lda", "ru": "🚗 Заказ в пути", "en": "🚗 Your order is on the way"},
    "status_delivered": {"uz": "📍 Buyurtmangiz yetkazildi", "ru": "📍 Заказ доставлен", "en": "📍 Order delivered"},
    "status_completed": {"uz": "🎉 Buyurtma yakunlandi. Rahmat!", "ru": "🎉 Заказ завершён. Спасибо!", "en": "🎉 Order completed. Thank you!"},
    "status_canceled": {"uz": "❌ Buyurtmangiz bekor qilindi", "ru": "❌ Заказ отменён", "en": "❌ Order canceled"},
    "status_rejected": {"uz": "❌ Buyurtmangiz rad etildi", "ru": "❌ Заказ отклонён", "en": "❌ Order rejected"},

    "order_number": {"uz": "Buyurtma", "ru": "Заказ", "en": "Order"},
    "cancel_reason_label": {"uz": "Sabab", "ru": "Причина", "en": "Reason"},

    # ── Buyurtma / to'lov oqimi ──
    "order_empty": {
        "uz": "Savat bo'sh. Iltimos, avval mahsulot tanlang.",
        "ru": "Корзина пуста. Пожалуйста, сначала выберите товар.",
        "en": "Your cart is empty. Please choose a product first.",
    },
    "order_saved_pay": {
        "uz": "🧾 Buyurtmangiz #{number} saqlandi!\nJami to'lov: <b>{total}</b>\n\nTo'lovni amalga oshirish uchun quyidagi tugmani bosing 👇",
        "ru": "🧾 Ваш заказ #{number} сохранён!\nК оплате: <b>{total}</b>\n\nНажмите кнопку ниже, чтобы оплатить 👇",
        "en": "🧾 Your order #{number} is saved!\nTotal: <b>{total}</b>\n\nTap the button below to pay 👇",
    },
    "btn_pay_order": {"uz": "💳 To'lov qilish", "ru": "💳 Оплатить", "en": "💳 Pay"},
    "choose_provider": {
        "uz": "To'lov usulini tanlang 👇",
        "ru": "Выберите способ оплаты 👇",
        "en": "Choose a payment method 👇",
    },
    "btn_cancel_order": {"uz": "❌ Bekor qilish", "ru": "❌ Отменить", "en": "❌ Cancel"},
    "paying": {"uz": "💳 To'lov amalga oshirilmoqda…", "ru": "💳 Проводим оплату…", "en": "💳 Processing payment…"},
    "payment_success": {
        "uz": "✅ To'lov muvaffaqiyatli qabul qilindi!\n{provider} orqali to'landi.\n\nBuyurtma #{number} qabul qilindi va tez orada tasdiqlanadi. Rahmat! 🙌",
        "ru": "✅ Оплата прошла успешно!\nОплачено через {provider}.\n\nЗаказ #{number} принят и скоро будет подтверждён. Спасибо! 🙌",
        "en": "✅ Payment successful!\nPaid via {provider}.\n\nOrder #{number} is accepted and will be confirmed soon. Thank you! 🙌",
    },
    "order_already_paid": {"uz": "Bu buyurtma allaqachon to'langan.", "ru": "Этот заказ уже оплачен.", "en": "This order is already paid."},
    "order_not_found": {"uz": "Buyurtma topilmadi.", "ru": "Заказ не найден.", "en": "Order not found."},
    "pay_offline": {"uz": "💵 Naqd (yetkazishda)", "ru": "💵 Наличными (при доставке)", "en": "💵 Cash (on delivery)"},
    "order_offline_ok": {
        "uz": "✅ Buyurtmangiz qabul qilindi!\nTo'lov: 💵 Naqd (yetkazishda to'laysiz).\n\nBuyurtma #{number} tez orada tasdiqlanadi. Rahmat! 🙌",
        "ru": "✅ Ваш заказ принят!\nОплата: 💵 Наличными (при доставке).\n\nЗаказ #{number} скоро будет подтверждён. Спасибо! 🙌",
        "en": "✅ Your order is accepted!\nPayment: 💵 Cash (on delivery).\n\nOrder #{number} will be confirmed soon. Thank you! 🙌",
    },
    "dtype_delivery": {"uz": "🚚 Yetkazib berish", "ru": "🚚 Доставка", "en": "🚚 Delivery"},
    "dtype_pickup": {"uz": "🏃 Olib ketish", "ru": "🏃 Самовывоз", "en": "🏃 Pickup"},
}

# Mahsulot ro'yxatidagi status nomlari (admin/super admin uchun ham qulay).
STATUS_LABELS = {
    "created": "🆕 Yangi",
    "confirmed": "✅ Tasdiqlangan",
    "preparing": "👨‍🍳 Tayyorlanmoqda",
    "on_way": "🚗 Yo'lda",
    "delivered": "📍 Yetkazilgan",
    "completed": "🎉 Yakunlangan",
    "canceled": "❌ Bekor qilingan",
    "rejected": "❌ Rad etilgan",
}


def normalize_lang(lang: str | None) -> str:
    lang = (lang or "").strip().lower()
    return lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def t(key: str, lang: str | None = None, **kwargs) -> str:
    lang = normalize_lang(lang)
    entry = TRANSLATIONS.get(key)
    if not entry:
        return key
    text = entry.get(lang) or entry.get(DEFAULT_LANGUAGE) or key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text
