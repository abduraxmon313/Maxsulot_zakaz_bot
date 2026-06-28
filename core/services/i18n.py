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
