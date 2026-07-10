/* ═══════════════════════════════════════════════════════════
   Maxsulot Zakaz — Mini App (Premium warm). Vanilla JS + Telegram WebApp.
   Manzil Yandex xarita orqali tanlanadi, buyurtma /api/orders ga saqlanadi,
   to'lov esa bot ichida (Click/Payme/Uzum/Paylov) amalga oshiriladi.
   ═══════════════════════════════════════════════════════════ */
'use strict';

const tg = window.Telegram ? window.Telegram.WebApp : null;
if (tg) { tg.ready(); tg.expand(); try { tg.enableClosingConfirmation(); } catch (e) {} }

const TASHKENT = { lat: 41.311081, lng: 69.279729 };

const State = {
  config: null, categories: [], products: [], cart: loadCart(),
  currentCategory: null, search: '',
  lang: localStorage.getItem('lang') || ((tg && tg.initDataUnsafe && tg.initDataUnsafe.user && tg.initDataUnsafe.user.language_code) || 'uz'),
  view: 'home',
  _map: null, _pickLat: null, _pickLng: null, _pickAddr: '', _geoT: null, _time: '',
};
if (!['uz', 'ru', 'en'].includes(State.lang)) State.lang = 'uz';

let _ymapsPromise = null;
// Markazdagi manzil belgisi (to'ldirilgan pin — data-ic stroke uslubidan farqli).
const MAP_PIN_SVG = '<svg viewBox="0 0 24 24" width="42" height="42" fill="var(--primary)" stroke="#fff" stroke-width="1.5"><path d="M12 23s8-7 8-13a8 8 0 1 0-16 0c0 6 8 13 8 13Z"/><circle cx="12" cy="10" r="3" fill="#fff" stroke="none"/></svg>';

/* ── Lucide-uslubidagi SVG ikonalar (emoji ishlatilmaydi) ── */
const ICONS = {
  search: '<svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>',
  x: '<svg viewBox="0 0 24 24"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>',
  cart: '<svg viewBox="0 0 24 24"><circle cx="8" cy="21" r="1"/><circle cx="19" cy="21" r="1"/><path d="M2.05 2.05h2l2.66 12.42a2 2 0 0 0 2 1.58h9.78a2 2 0 0 0 2-1.58l1.65-7.42H5.12"/></svg>',
  home: '<svg viewBox="0 0 24 24"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9 22V12h6v10"/></svg>',
  receipt: '<svg viewBox="0 0 24 24"><path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1Z"/><path d="M8 7h8"/><path d="M8 11h8"/><path d="M8 15h5"/></svg>',
  user: '<svg viewBox="0 0 24 24"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
  clock: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
  package: '<svg viewBox="0 0 24 24"><path d="M16.5 9.4 7.55 4.24"/><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><polyline points="3.29 7 12 12 20.71 7"/><line x1="12" y1="22" x2="12" y2="12"/></svg>',
  chevron: '<svg viewBox="0 0 24 24"><path d="m6 9 6 6 6-6"/></svg>',
  plus: '<svg viewBox="0 0 24 24"><path d="M5 12h14"/><path d="M12 5v14"/></svg>',
  minus: '<svg viewBox="0 0 24 24"><path d="M5 12h14"/></svg>',
  trash: '<svg viewBox="0 0 24 24"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>',
  phone: '<svg viewBox="0 0 24 24"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92Z"/></svg>',
  store: '<svg viewBox="0 0 24 24"><path d="M4 9V4h16v5"/><path d="M4 9h16l-1 11H5L4 9Z"/><path d="M9 20v-6h6v6"/></svg>',
  check: '<svg viewBox="0 0 24 24"><path d="M20 6 9 17l-5-5"/></svg>',
  checkCircle: '<svg viewBox="0 0 24 24"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
  card: '<svg viewBox="0 0 24 24"><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/></svg>',
  cash: '<svg viewBox="0 0 24 24"><rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="2"/><path d="M6 12h.01M18 12h.01"/></svg>',
  truck: '<svg viewBox="0 0 24 24"><path d="M10 17h4V5H2v12h3"/><path d="M20 17h2v-3.34a4 4 0 0 0-1.17-2.83L19 9h-5v8h1"/><circle cx="7.5" cy="17.5" r="1.5"/><circle cx="17.5" cy="17.5" r="1.5"/></svg>',
  run: '<svg viewBox="0 0 24 24"><circle cx="13" cy="4" r="2"/><path d="m5 21 3-6 4 2 2-3"/><path d="m8 15-2-4 5-2 3 3 3 1"/></svg>',
  globe: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>',
  bag: '<svg viewBox="0 0 24 24"><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"/><path d="M3 6h18"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>',
  pin: '<svg viewBox="0 0 24 24"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>',
  locate: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="7"/><line x1="12" y1="2" x2="12" y2="5"/><line x1="12" y1="19" x2="12" y2="22"/><line x1="2" y1="12" x2="5" y2="12"/><line x1="19" y1="12" x2="22" y2="12"/><circle cx="12" cy="12" r="2.5"/></svg>',
  alert: '<svg viewBox="0 0 24 24"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
};

function applyIcons(root) {
  (root || document).querySelectorAll('[data-ic]').forEach((node) => {
    if (node.dataset.icDone === '1') return;
    const name = node.getAttribute('data-ic');
    if (ICONS[name]) { node.innerHTML = ICONS[name]; node.dataset.icDone = '1'; }
  });
}

/* ── I18N ── */
const I18N = {
  search: { uz: 'Mahsulot qidirish…', ru: 'Поиск товаров…', en: 'Search products…' },
  products: { uz: 'Mahsulotlar', ru: 'Товары', en: 'Products' },
  all: { uz: 'Hammasi', ru: 'Все', en: 'All' },
  add: { uz: 'Savatga', ru: 'В корзину', en: 'Add' },
  cart_empty: { uz: "Savat bo'sh", ru: 'Корзина пуста', en: 'Cart is empty' },
  start_shopping: { uz: 'Xaridni boshlash', ru: 'Начать покупки', en: 'Start shopping' },
  checkout: { uz: 'Rasmiylashtirish', ru: 'Оформить', en: 'Checkout' },
  order_btn: { uz: 'Buyurtma berish', ru: 'Заказать', en: 'Place order' },
  items_total: { uz: 'Mahsulotlar', ru: 'Товары', en: 'Items' },
  delivery: { uz: 'Yetkazib berish', ru: 'Доставка', en: 'Delivery' },
  pickup: { uz: 'Olib ketish', ru: 'Самовывоз', en: 'Pickup' },
  total: { uz: 'Jami', ru: 'Итого', en: 'Total' },
  free: { uz: 'Bepul', ru: 'Бесплатно', en: 'Free' },
  out_of_stock: { uz: 'Tugagan', ru: 'Нет в наличии', en: 'Out of stock' },
  in_stock: { uz: 'Mavjud', ru: 'В наличии', en: 'In stock' },
  min_order: { uz: 'Minimal buyurtma', ru: 'Мин. заказ', en: 'Min. order' },
  note: { uz: 'Izoh (ixtiyoriy)', ru: 'Комментарий (необязательно)', en: 'Note (optional)' },
  payment: { uz: "To'lov usuli", ru: 'Способ оплаты', en: 'Payment method' },
  delivery_type: { uz: 'Yetkazib berish turi', ru: 'Тип доставки', en: 'Delivery type' },
  cash: { uz: 'Naqd', ru: 'Наличные', en: 'Cash' },
  card: { uz: 'Karta / Onlayn', ru: 'Карта / Онлайн', en: 'Card / Online' },
  no_orders: { uz: "Sizda hali buyurtmalar yo'q", ru: 'Заказов пока нет', en: 'No orders yet' },
  order_sent: { uz: '✓ Buyurtma botga yuborildi', ru: '✓ Заказ отправлен в бот', en: '✓ Order sent to the bot' },
  no_products: { uz: 'Mahsulot topilmadi', ru: 'Товары не найдены', en: 'No products found' },
  language: { uz: 'Til', ru: 'Язык', en: 'Language' },
  contacts: { uz: 'Aloqa', ru: 'Контакты', en: 'Contacts' },
  delivery_fee: { uz: 'Yetkazib berish', ru: 'Доставка', en: 'Delivery' },
  paid: { uz: "To'langan", ru: 'Оплачено', en: 'Paid' },
  online_shop: { uz: 'Onlayn do\'kon', ru: 'Онлайн магазин', en: 'Online shop' },
  closed: { uz: 'Do\'kon hozircha yopiq', ru: 'Магазин закрыт', en: 'Shop is closed' },
  address_label: { uz: 'Yetkazish manzili', ru: 'Адрес доставки', en: 'Delivery address' },
  address_ph: { uz: 'Ko\'cha, uy, mo\'ljal…', ru: 'Улица, дом, ориентир…', en: 'Street, house, landmark…' },
  landmark: { uz: 'Xonadon / qavat / mo\'ljal (ixtiyoriy)', ru: 'Квартира / этаж / ориентир (необяз.)', en: 'Apartment / floor / landmark (optional)' },
  map_hint: { uz: 'Xaritani suring — belgi kerakli joyga to\'g\'rilansin', ru: 'Двигайте карту, чтобы указать точку', en: 'Drag the map to set the point' },
  map_unavailable: { uz: 'Xarita yuklanmadi. Manzilni qo\'lda kiriting.', ru: 'Карта не загрузилась. Введите адрес вручную.', en: 'Map unavailable. Enter address manually.' },
  save_and_pay: { uz: 'Buyurtmani saqlash va to\'lovga o\'tish', ru: 'Сохранить заказ и перейти к оплате', en: 'Save order and go to payment' },
  need_address: { uz: 'Iltimos, yetkazib berish manzilini kiriting', ru: 'Пожалуйста, введите адрес доставки', en: 'Please enter a delivery address' },
  saving: { uz: 'Saqlanmoqda…', ru: 'Сохранение…', en: 'Saving…' },
  order_saved_title: { uz: 'Buyurtma saqlandi!', ru: 'Заказ сохранён!', en: 'Order saved!' },
  go_to_bot: { uz: 'Botga o\'ting va «To\'lov qilish» tugmasini bosing', ru: 'Перейдите в бот и нажмите «Оплатить»', en: 'Go to the bot and tap “Pay”' },
  open_bot: { uz: 'Botga o\'tish', ru: 'Перейти в бот', en: 'Go to the bot' },
  locating: { uz: 'Joylashuv aniqlanmoqda…', ru: 'Определяем локацию…', en: 'Locating…' },
  delivery_time: { uz: 'Yetkazib berish vaqti', ru: 'Время доставки', en: 'Delivery time' },
  asap: { uz: 'Imkon qadar tez', ru: 'Как можно скорее', en: 'As soon as possible' },
  gate_title: { uz: 'Do\'kon faqat Telegram orqali ochiladi', ru: 'Магазин открывается только через Telegram', en: 'The shop opens only via Telegram' },
  gate_text: { uz: 'Iltimos, do\'kon botini oching va «Do\'konni ochish» tugmasi orqali kiring.', ru: 'Пожалуйста, откройте бота магазина и войдите через кнопку «Открыть магазин».', en: 'Please open the shop bot and enter via the “Open shop” button.' },
  open_via_menu: { uz: 'Buyurtma va to\'lov uchun do\'konni pastdagi ☰ menyu tugmasi orqali oching.', ru: 'Для заказа и оплаты откройте магазин через кнопку меню ☰ внизу.', en: 'To order & pay, open the shop via the ☰ menu button below.' },
  map_error: { uz: 'Xarita yuklashda xatolik. Yetkazib berish uchun manzil tanlab bo\'lmaydi — faqat «Olib ketish» mavjud.', ru: 'Ошибка загрузки карты. Адрес доставки выбрать нельзя — доступен только «Самовывоз».', en: 'Map failed to load. Delivery address can\'t be selected — only “Pickup” is available.' },
  map_note: { uz: 'Xarita yuklanmadi — manzilingizni quyida matn ko\'rinishida yozing yoki «Olib ketish»ni tanlang.', ru: 'Карта не загрузилась — введите адрес текстом ниже или выберите «Самовывоз».', en: 'Map didn\'t load — type your address below or choose “Pickup”.' },
  loc_fail: { uz: 'Joylashuvni aniqlab bo\'lmadi', ru: 'Не удалось определить локацию', en: 'Could not detect location' },
};
const ST = {
  created: { uz: 'Yangi', ru: 'Новый', en: 'New' }, confirmed: { uz: 'Tasdiqlandi', ru: 'Подтверждён', en: 'Confirmed' },
  preparing: { uz: 'Tayyorlanmoqda', ru: 'Готовится', en: 'Preparing' }, on_way: { uz: "Yo'lda", ru: 'В пути', en: 'On the way' },
  delivered: { uz: 'Yetkazildi', ru: 'Доставлен', en: 'Delivered' }, completed: { uz: 'Yakunlandi', ru: 'Завершён', en: 'Completed' },
  canceled: { uz: 'Bekor qilindi', ru: 'Отменён', en: 'Canceled' }, rejected: { uz: 'Rad etildi', ru: 'Отклонён', en: 'Rejected' },
};
const L = (k) => (I18N[k] && I18N[k][State.lang]) || (I18N[k] && I18N[k].uz) || k;
const el = (id) => document.getElementById(id);

/* ── Helpers ── */
window.__imgErr = function (img) { const w = img.parentNode; if (w) w.innerHTML = '<div class="ph"><span data-ic="package"></span></div>'; applyIcons(w); };
function imgHtml(src) { if (src) return `<img src="${src}" alt="" loading="lazy" onerror="window.__imgErr(this)">`; return '<div class="ph"><span data-ic="package"></span></div>'; }
function money(n) { const cur = State.config ? State.config.currency : "so'm"; return (Number(n) || 0).toLocaleString('ru-RU').replace(/,/g, ' ') + ' ' + cur; }
function haptic(t) { try { tg && tg.HapticFeedback && tg.HapticFeedback.impactOccurred(t || 'light'); } catch (e) {} }
function toast(msg) { const t = el('toast'); t.textContent = msg; t.classList.add('show'); clearTimeout(toast._t); toast._t = setTimeout(() => t.classList.remove('show'), 2600); }
function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }
function escAttr(s) { return esc(s).replace(/"/g, '&quot;'); }

async function api(path, options = {}) {
  const headers = Object.assign({ 'Content-Type': 'application/json' }, options.headers || {});
  const initData = (tg && tg.initData) ? tg.initData : '';
  let url = '/api' + path;
  if (initData) {
    headers['X-Telegram-Init-Data'] = initData;
    // Zaxira: ba'zi muhitlar maxsus header'ni olib tashlashi mumkin — query orqali ham yuboramiz.
    url += (url.includes('?') ? '&' : '?') + 'tgWebAppData=' + encodeURIComponent(initData);
  }
  // Kesh-buster: har so'rov noyob bo'lsin (Telegram/brauzer eski javobni bermasin —
  // masalan do'kon holati eski "yopiq" bo'lib qolmasligi uchun).
  url += (url.includes('?') ? '&' : '?') + '_=' + Date.now();
  const res = await fetch(url, Object.assign({}, options, { headers, cache: 'no-store' }));
  if (!res.ok) { let d = 'Xatolik yuz berdi'; try { d = (await res.json()).detail || d; } catch (e) {} throw new Error(d); }
  return res.json();
}

/* ── Cart ── */
function loadCart() { try { return JSON.parse(localStorage.getItem('cart') || '[]'); } catch (e) { return []; } }
function saveCart() { localStorage.setItem('cart', JSON.stringify(State.cart)); updateBadge(); }
function cartQty(id) { const it = State.cart.find(x => x.id === id); return it ? it.qty : 0; }
function cartCount() { return State.cart.reduce((s, x) => s + x.qty, 0); }
function cartItemsTotal() { return State.cart.reduce((s, x) => s + x.price * x.qty, 0); }
function addToCart(p) { const it = State.cart.find(x => x.id === p.id); if (it) it.qty += 1; else State.cart.push({ id: p.id, name: p.name, price: p.price, image: p.image, qty: 1 }); saveCart(); haptic('light'); }
function changeQty(id, d) { const it = State.cart.find(x => x.id === id); if (!it) return; it.qty += d; if (it.qty <= 0) State.cart = State.cart.filter(x => x.id !== id); saveCart(); haptic('light'); }
function updateBadge() {
  const c = cartCount();
  [el('cartBadge'), el('navCartBadge')].forEach(b => { if (!b) return; if (c > 0) { b.textContent = c; b.hidden = false; } else { b.hidden = true; } });
}

/* ── Banners / Categories / Products ── */
function renderBanners(banners) {
  const wrap = el('banners');
  if (!banners || !banners.length) { wrap.style.display = 'none'; return; }
  wrap.style.display = 'flex';
  wrap.innerHTML = banners.map(b => `<div class="banner">${b.image ? imgHtml(b.image) : ''}</div>`).join('');
}
function renderCategories() {
  const wrap = el('categories');
  let html = `<button class="cat-chip ${State.currentCategory === null ? 'active' : ''}" data-cat="all"><span class="cc-ic">🛍️</span><span class="lbl">${L('all')}</span></button>`;
  html += State.categories.map(c => `<button class="cat-chip ${State.currentCategory === c.id ? 'active' : ''}" data-cat="${c.id}">${c.emoji ? `<span class="cc-ic">${esc(c.emoji)}</span>` : ''}<span class="lbl">${esc(c.name)}</span></button>`).join('');
  wrap.innerHTML = html;
  wrap.querySelectorAll('.cat-chip').forEach(chip => chip.onclick = () => { const v = chip.dataset.cat; State.currentCategory = v === 'all' ? null : Number(v); renderCategories(); loadProducts(); });
}
function skeletonGrid() { el('products').innerHTML = Array.from({ length: 6 }).map(() => `<div class="skeleton"><div class="sk-img"></div><div class="sk-line" style="width:55%"></div><div class="sk-line" style="width:85%"></div></div>`).join(''); }
function renderProducts() {
  const wrap = el('products'), empty = el('emptyProducts');
  if (!State.products.length) { wrap.innerHTML = ''; empty.hidden = false; empty.querySelector('p').textContent = L('no_products'); applyIcons(empty); return; }
  empty.hidden = true; wrap.innerHTML = State.products.map(productCard).join(''); applyIcons(wrap); bindCards();
}
function productCard(p) {
  const disc = p.old_price && p.old_price > p.price ? `<div class="discount-badge">-${Math.round((1 - p.price / p.old_price) * 100)}%</div>` : '';
  const out = !p.in_stock ? `<div class="out-badge">${L('out_of_stock')}</div>` : '';
  const qty = cartQty(p.id); let action;
  if (!p.in_stock) action = `<button class="add" disabled>${L('out_of_stock')}</button>`;
  else if (qty > 0) action = `<div class="qty-mini" data-id="${p.id}"><button data-act="dec"><span data-ic="minus"></span></button><span>${qty}</span><button data-act="inc"><span data-ic="plus"></span></button></div>`;
  else action = `<button class="add" data-add="${p.id}">${L('add')}</button>`;
  const old = p.old_price && p.old_price > p.price ? `<span class="old">${money(p.old_price)}</span>` : '';
  return `<div class="card"><div class="imgwrap" data-open="${p.id}">${disc}${imgHtml(p.image)}${out}</div><div class="info"><div class="price">${money(p.price)} ${old}</div><div class="pname" data-open="${p.id}">${esc(p.name)}</div>${action}</div></div>`;
}
function bindCards() {
  const wrap = el('products');
  wrap.querySelectorAll('[data-open]').forEach(c => c.onclick = () => openProduct(Number(c.dataset.open)));
  wrap.querySelectorAll('[data-add]').forEach(b => b.onclick = (e) => { e.stopPropagation(); addToCart(State.products.find(x => x.id === Number(b.dataset.add))); renderProducts(); });
  wrap.querySelectorAll('.qty-mini').forEach(q => { const id = Number(q.dataset.id); q.querySelector('[data-act="inc"]').onclick = (e) => { e.stopPropagation(); changeQty(id, 1); renderProducts(); }; q.querySelector('[data-act="dec"]').onclick = (e) => { e.stopPropagation(); changeQty(id, -1); renderProducts(); }; });
}
async function openProduct(id) {
  let p = State.products.find(x => x.id === id);
  try { p = await api('/products/' + id); } catch (e) {}
  if (!p) return;
  const old = p.old_price && p.old_price > p.price ? `<span class="pd-old">${money(p.old_price)}</span>` : '';
  el('productContent').innerHTML = `<div class="pd-img">${imgHtml(p.image)}</div><div class="pd-name">${esc(p.name)}</div><div><span class="pd-price">${money(p.price)}</span>${old}</div>${p.description ? `<div class="pd-desc">${esc(p.description)}</div>` : ''}<div class="pd-meta">${p.in_stock ? '✓ ' + L('in_stock') : L('out_of_stock')}</div><button class="btn" id="pdAdd" ${p.in_stock ? '' : 'disabled'}><span data-ic="cart"></span>${L('add')} · ${money(p.price)}</button>`;
  applyIcons(el('productContent'));
  if (p.in_stock) el('pdAdd').onclick = () => { addToCart(p); closeSheets(); renderProducts(); toast(L('add') + ' ✓'); };
  openSheet('sheetProduct');
}

/* ── Cart view ── */
function renderCart() {
  const wrap = el('cartItems'), empty = el('cartEmpty'), footer = el('cartFooter');
  if (!State.cart.length) { wrap.innerHTML = ''; empty.hidden = false; empty.querySelector('p').textContent = L('cart_empty'); applyIcons(empty); footer.innerHTML = ''; return; }
  empty.hidden = true;
  wrap.innerHTML = State.cart.map(it => `<div class="cart-item"><div class="ci-img">${imgHtml(it.image)}</div><div class="ci-info"><div class="ci-name">${esc(it.name)}</div><div class="ci-price">${money(it.price)}</div></div><div class="qty"><button data-dec="${it.id}"><span data-ic="minus"></span></button><span>${it.qty}</span><button data-inc="${it.id}"><span data-ic="plus"></span></button></div></div>`).join('');
  applyIcons(wrap);
  wrap.querySelectorAll('[data-inc]').forEach(b => b.onclick = () => { changeQty(Number(b.dataset.inc), 1); renderCart(); renderProducts(); });
  wrap.querySelectorAll('[data-dec]').forEach(b => b.onclick = () => { changeQty(Number(b.dataset.dec), -1); renderCart(); renderProducts(); });
  const itemsTotal = cartItemsTotal(), min = State.config.min_order_amount || 0, belowMin = min > 0 && itemsTotal < min;
  footer.innerHTML = `<div class="cf-inner"><div class="sum-row"><span>${L('items_total')}</span><span>${money(itemsTotal)}</span></div><div class="sum-row total"><span>${L('total')}</span><span>${money(itemsTotal)}</span></div>${belowMin ? `<div class="min-warn">${L('min_order')}: ${money(min)}</div>` : ''}<button class="btn" id="goCheckout" ${belowMin ? 'disabled' : ''}><span data-ic="bag"></span>${L('checkout')}</button></div>`;
  applyIcons(footer);
  if (!belowMin) el('goCheckout').onclick = openCheckout;
}

/* ── Yandex Maps loader ── */
function ymLang() { return State.lang === 'en' ? 'en_US' : 'ru_RU'; }
function loadYandexMaps() {
  if (window.ymaps && window.ymaps.Map) return Promise.resolve();
  if (_ymapsPromise) return _ymapsPromise;
  const key = State.config && State.config.maps_api_key;
  if (!key) return Promise.reject(new Error('no_key'));
  _ymapsPromise = new Promise((resolve, reject) => {
    // Xato bo'lsa promise'ni reset qilamiz — keyingi urinishda qayta yuklansin.
    const fail = (e) => { _ymapsPromise = null; reject(e || new Error('load')); };
    const s = document.createElement('script');
    s.src = `https://api-maps.yandex.ru/2.1/?apikey=${encodeURIComponent(key)}&lang=${ymLang()}`;
    s.async = true;
    s.onload = () => { if (window.ymaps && window.ymaps.ready) window.ymaps.ready(resolve); else fail(new Error('no_ymaps')); };
    s.onerror = () => fail(new Error('script_error'));
    document.head.appendChild(s);
    // Osilib qolmasligi uchun timeout.
    setTimeout(() => { if (!(window.ymaps && window.ymaps.Map)) fail(new Error('timeout')); }, 15000);
  });
  return _ymapsPromise;
}
function initAddressMap(node) {
  if (!node || !window.ymaps) return;
  const start = (State._pickLat && State._pickLng) ? [State._pickLat, State._pickLng] : [TASHKENT.lat, TASHKENT.lng];
  try {
    State._map = new ymaps.Map(node, { center: start, zoom: 15, controls: [] }, { suppressMapOpenBlock: true, yandexMapDisablePoiInteractivity: true });
    State._map.events.add('boundschange', () => { clearTimeout(State._geoT); State._geoT = setTimeout(reverseGeocodeCenter, 450); });
    setTimeout(() => { try { State._map && State._map.container.fitToViewport(); } catch (e) {} }, 250);
    reverseGeocodeCenter();
  } catch (e) { console.error('Yandex map init error', e); }
}
function reverseGeocodeCenter() {
  if (!State._map || !window.ymaps) return;
  const c = State._map.getCenter();
  State._pickLat = c[0]; State._pickLng = c[1];
  ymaps.geocode(c, { results: 1 }).then((res) => {
    const obj = res.geoObjects.get(0);
    const addr = obj ? obj.getAddressLine() : '';
    State._pickAddr = addr;
    const inp = el('afAddress'); if (inp) inp.value = addr;
  }).catch(() => {});
}
function locateMeYandex(btn) {
  if (!navigator.geolocation) { toast(L('loc_fail')); return; }
  const orig = btn ? btn.innerHTML : '';
  if (btn) { btn.classList.add('busy'); }
  navigator.geolocation.getCurrentPosition(
    (pos) => { if (State._map) { State._map.setCenter([pos.coords.latitude, pos.coords.longitude], 17); haptic('medium'); } if (btn) btn.classList.remove('busy'); },
    () => { if (btn) btn.classList.remove('busy'); toast(L('loc_fail')); },
    { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
  );
}

/* ── Checkout: yetkazish turi + Yandex xarita manzil + saqlab to'lovga o'tish ──
   Xarita yuklanmasa → ogohlantirish + faqat «Olib ketish» (yetkazib berish bloklanadi). */
function openCheckout() {
  const hasMap = !!(State.config && State.config.maps_api_key);
  State._mapOk = hasMap;         // optimistik; xarita yuklanmasa false bo'ladi
  let deliveryType = 'delivery';

  el('checkoutContent').innerHTML = `
    <div class="field"><label>${L('delivery_type')}</label>
      <div class="seg" id="segDelivery">
        <button class="active" data-v="delivery"><span data-ic="truck"></span>${L('delivery')}</button>
        <button data-v="pickup"><span data-ic="run"></span>${L('pickup')}</button>
      </div>
    </div>
    <div id="addrBlock">
      <div class="map-wrap"><div id="mapEl"></div><div class="map-pin">${MAP_PIN_SVG}</div><button type="button" class="map-locate" id="locBtn" data-ic="locate"></button><div id="mapLoading" class="map-loading"><div class="spinner"></div></div></div>
      <p class="map-hint">${L('map_hint')}</p>
      <div id="mapNote" class="map-warn" hidden><span data-ic="alert"></span><span>${L('map_note')}</span></div>
      <div class="field"><label>${L('address_label')}</label><input id="afAddress" placeholder="${L('address_ph')}" /></div>
      <div class="field"><input id="afLandmark" placeholder="${L('landmark')}" /></div>
    </div>
    <div class="field"><label>${L('delivery_time')}</label><div class="time-slots" id="timeSlots"></div></div>
    <div class="field"><label>${L('note')}</label><textarea id="ckNote" placeholder="${L('note')}"></textarea></div>
    <div id="ckSummary"></div>
    <button class="btn" id="submitOrder"><span data-ic="bag"></span>${L('save_and_pay')}</button>`;

  const segD = el('segDelivery'), addrBlock = el('addrBlock');
  const setType = (v) => {
    deliveryType = v;
    segD.querySelectorAll('button').forEach(x => x.classList.toggle('active', x.dataset.v === v));
    // Manzil bloki (xarita + ogohlantirish + matn) faqat «Yetkazib berish»da ko'rinadi —
    // shu sabab «Olib ketish»da xarita ogohlantirishi ko'rinmaydi.
    addrBlock.style.display = (v === 'delivery') ? '' : 'none';
    renderSummary(v);
  };
  segD.querySelectorAll('button').forEach(b => b.onclick = () => setType(b.dataset.v));

  // Xarita yuklanmasa: xaritani yashiramiz, LEKIN yetkazib berishni bloklamaymiz —
  // mijoz manzilni matnda yozadi yoki «Olib ketish»ni tanlaydi.
  const onMapFailed = () => {
    State._mapOk = false;
    const wrap = document.querySelector('.map-wrap'); if (wrap) wrap.style.display = 'none';
    const hint = document.querySelector('.map-hint'); if (hint) hint.style.display = 'none';
    const note = el('mapNote'); if (note) { note.hidden = false; applyIcons(note); }
  };
  const onMapOk = () => {
    State._mapOk = true;
    const ld = el('mapLoading'); if (ld) ld.style.display = 'none';
    // Agar avvalroq ogohlantirish ko'rinib qolgan bo'lsa — uni yashirib, xaritani qaytaramiz.
    const note = el('mapNote'); if (note) note.hidden = true;
    const wrap = document.querySelector('.map-wrap'); if (wrap) wrap.style.display = '';
    const hint = document.querySelector('.map-hint'); if (hint) hint.style.display = '';
  };

  applyIcons(el('checkoutContent'));
  renderTimeSlots();
  setType('delivery');
  el('submitOrder').onclick = () => submitOrder(deliveryType);
  openSheet('sheetCheckout');

  if (!hasMap) { onMapFailed(); return; }

  const locBtn = el('locBtn'); if (locBtn) locBtn.onclick = () => locateMeYandex(locBtn);
  loadYandexMaps()
    .then(() => {
      // Xarita konteyneri tayyor bo'lishi uchun bir necha marta urinamiz (0.4s oralab).
      // Faqat hamma urinish muvaffaqiyatsiz bo'lgandagina ogohlantirish chiqadi.
      const tryInit = (attempt) => {
        try { initAddressMap(el('mapEl')); } catch (e) { console.error('map init', e); }
        if (State._map) { onMapOk(); return; }
        if (attempt < 3) { setTimeout(() => tryInit(attempt + 1), 400); return; }
        console.warn('Yandex xarita init muvaffaqiyatsiz (barcha urinishlar)');
        onMapFailed();
      };
      requestAnimationFrame(() => setTimeout(() => tryInit(0), 120));
    })
    .catch((e) => { console.warn('Yandex xarita yuklanmadi:', e && e.message); onMapFailed(); });
}
function renderTimeSlots() {
  const wrap = el('timeSlots'); if (!wrap) return;
  const slots = (State.config && State.config.delivery_slots) || [];
  State._time = '';
  let html = `<button type="button" class="slot active" data-t="">${L('asap')}</button>`;
  html += slots.map(s => `<button type="button" class="slot" data-t="${esc(s)}">${esc(s)}</button>`).join('');
  wrap.innerHTML = html;
  wrap.querySelectorAll('.slot').forEach(b => b.onclick = () => {
    wrap.querySelectorAll('.slot').forEach(x => x.classList.remove('active'));
    b.classList.add('active'); State._time = b.dataset.t; haptic('light');
  });
}
function deliveryFeeFor(t) { const c = State.config; if (!c) return 0; let f = c.delivery_fee || 0; if (c.free_delivery_from && t >= c.free_delivery_from) f = 0; return f; }
function renderSummary(deliveryType) {
  const itemsTotal = cartItemsTotal(), fee = deliveryType === 'delivery' ? deliveryFeeFor(itemsTotal) : 0;
  el('ckSummary').innerHTML = `<div class="sum-row"><span>${L('items_total')}</span><span>${money(itemsTotal)}</span></div>${deliveryType === 'delivery' ? `<div class="sum-row"><span>${L('delivery_fee')}</span><span>${fee ? money(fee) : L('free')}</span></div>` : ''}<div class="sum-row total"><span>${L('total')}</span><span>${money(itemsTotal + fee)}</span></div>`;
}
function submitOrder(deliveryType) {
  if (!State.cart.length) { toast(L('cart_empty')); return; }
  const min = State.config.min_order_amount || 0;
  if (min && cartItemsTotal() < min) { toast(L('min_order') + ': ' + money(min)); return; }
  let address = null, lat = null, lng = null;
  if (deliveryType === 'delivery') {
    // Xarita ishlamasa ham manzilni matnda yozish mumkin — bloklamaymiz.
    const base = (el('afAddress') && el('afAddress').value.trim()) || State._pickAddr || '';
    const landmark = (el('afLandmark') && el('afLandmark').value.trim()) || '';
    address = [base, landmark].filter(Boolean).join(', ');
    if (!address) { toast(L('need_address')); return; }
    lat = State._mapOk ? State._pickLat : null;
    lng = State._mapOk ? State._pickLng : null;
  }
  const note = (el('ckNote') && el('ckNote').value.trim()) || '';
  const deliveryTime = State._time || L('asap');
  const btn = el('submitOrder');
  if (btn) { btn.disabled = true; btn.textContent = L('saving'); }
  const body = { items: State.cart.map(x => ({ product_id: x.id, qty: x.qty })), delivery_type: deliveryType, address, lat, lng, delivery_time: deliveryTime, note };
  api('/orders', { method: 'POST', body: JSON.stringify(body) })
    .then((order) => { State.cart = []; saveCart(); renderProducts(); haptic('medium'); showOrderSuccess(order); })
    .catch((e) => { toast('❌ ' + e.message); if (btn) { btn.disabled = false; btn.innerHTML = `<span data-ic="bag"></span>${L('save_and_pay')}`; applyIcons(btn); } });
}
function showOrderSuccess(order) {
  try { if (State._map && State._map.destroy) { State._map.destroy(); } } catch (e) {}
  State._map = null;
  el('checkoutContent').innerHTML = `
    <div class="order-success">
      <div class="os-check" data-ic="checkCircle"></div>
      <h3>${L('order_saved_title')}</h3>
      <p class="os-num"># ${order.order_number} · ${money(order.grand_total)}</p>
      <div class="os-hint">${L('go_to_bot')}</div>
      <button class="btn" id="osOpenBot"><span data-ic="bag"></span>${L('open_bot')}</button>
    </div>`;
  applyIcons(el('checkoutContent'));
  el('osOpenBot').onclick = () => { if (tg && tg.close) tg.close(); else { closeSheets(); switchView('orders'); } };
  updateBadge();
}

/* ── Orders ── */
async function loadOrders() {
  const wrap = el('ordersList'), empty = el('emptyOrders');
  wrap.innerHTML = Array.from({ length: 3 }).map(() => `<div class="skeleton" style="height:96px;border-radius:18px"></div>`).join('');
  try {
    const orders = await api('/orders');
    if (!orders.length) { wrap.innerHTML = ''; empty.hidden = false; empty.querySelector('p').textContent = L('no_orders'); applyIcons(empty); return; }
    empty.hidden = true;
    wrap.innerHTML = orders.map(o => {
      const stTxt = (ST[o.status] && ST[o.status][State.lang]) || o.status;
      const items = o.items.map(i => `${esc(i.name)} ×${i.qty}`).join(', ');
      const paid = o.is_paid ? `<span class="order-paid"><span data-ic="check"></span>${L('paid')}</span>` : '';
      return `<div class="order-card"><div class="order-head"><span class="order-num"># ${o.order_number}</span><span class="order-status st-${o.status}">${stTxt}</span></div><div class="order-items-mini">${items}</div><div class="order-total">${money(o.grand_total)}${paid}</div></div>`;
    }).join('');
    applyIcons(wrap);
  } catch (e) { wrap.innerHTML = ''; toast(e.message); }
}

/* ── Profile ── */
function renderProfile() {
  const user = (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) || {};
  const name = [user.first_name, user.last_name].filter(Boolean).join(' ') || 'Mijoz';
  const initial = (name.trim()[0] || 'M').toUpperCase();
  const c = State.config || {};
  const langs = [['uz', "O'zbek"], ['ru', 'Русский'], ['en', 'English']];
  el('profileContent').innerHTML = `
    <div class="profile">
      <div class="prof-card"><div class="prof-head"><div class="prof-avatar">${esc(initial)}</div><div><div class="prof-name">${esc(name)}</div><div class="prof-phone">${user.username ? '@' + esc(user.username) : ''}</div></div></div></div>
      <div class="prof-card"><div class="prof-section-title">${L('language')}</div><div class="lang-row">${langs.map(l => `<button class="lang-pick ${State.lang === l[0] ? 'active' : ''}" data-lang="${l[0]}">${l[1]}</button>`).join('')}</div></div>
      <div class="prof-card"><div class="prof-section-title">${L('contacts')}</div>
        <div class="prof-row"><span class="pr-ic" data-ic="store"></span><div class="pr-text">${esc(c.shop_name || '')}</div></div>
        ${c.phone ? `<div class="prof-row"><span class="pr-ic" data-ic="phone"></span><div class="pr-text">${esc(c.phone)}</div></div>` : ''}
        ${c.working_hours ? `<div class="prof-row"><span class="pr-ic" data-ic="clock"></span><div class="pr-text">${esc(c.working_hours)}</div></div>` : ''}
      </div>
    </div>`;
  applyIcons(el('profileContent'));
  el('profileContent').querySelectorAll('[data-lang]').forEach(b => b.onclick = () => { setLang(b.dataset.lang); renderProfile(); });
}

/* ── Sheets ── */
function openSheet(id) { el(id).classList.add('open'); if (tg && tg.BackButton) tg.BackButton.show(); }
function closeSheets() {
  document.querySelectorAll('.sheet').forEach(s => s.classList.remove('open'));
  try { if (State._map && State._map.destroy) State._map.destroy(); } catch (e) {}
  State._map = null;
  if (tg && tg.BackButton) tg.BackButton.hide();
}

/* ── Nav ── */
function switchView(view) {
  State.view = view;
  document.querySelectorAll('.nav-item').forEach(n => n.classList.toggle('active', n.dataset.nav === view));
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  el('view-' + view).classList.add('active');
  if (view === 'cart') renderCart();
  if (view === 'orders') loadOrders();
  if (view === 'profile') renderProfile();
  window.scrollTo(0, 0);
}

async function loadProducts() {
  skeletonGrid();
  try {
    const params = new URLSearchParams();
    if (State.currentCategory) params.set('category_id', State.currentCategory);
    if (State.search) params.set('q', State.search);
    State.products = await api('/products?' + params.toString());
    renderProducts();
  } catch (e) { el('products').innerHTML = ''; toast(e.message); }
}

function setLang(lang) {
  State.lang = lang; localStorage.setItem('lang', lang);
  el('searchInput').placeholder = L('search');
  el('productsTitle').textContent = L('products');
  el('shopStatus').textContent = L('online_shop');
  renderCategories(); renderProducts();
}

function applyTheme() {
  // Rang butunlay CSS (brend palitrasi) tomonidan boshqariladi — DB'dagi eski
  // primary_color (masalan sovuq #7000FF) endi QO'LLANILMAYDI.
  if (tg) { try { tg.setHeaderColor && tg.setHeaderColor('#FFFDF8'); tg.setBackgroundColor && tg.setBackgroundColor('#FFFDF8'); } catch (e) {} }
}

/* Faqat Telegram orqali ochilishi kerak — aks holda "gate" ekran ko'rsatiladi. */
function showTelegramGate() {
  const sp = el('splash'); if (sp) sp.style.display = 'none';
  const gate = document.createElement('div');
  gate.className = 'tg-gate';
  gate.innerHTML = `<div class="gate-logo">${ICONS.bag}</div><h2>${L('gate_title')}</h2><p>${L('gate_text')}</p>`;
  document.body.appendChild(gate);
}

function isInTelegram() {
  // Telegram ichida ekanligini bir nechta signal bilan aniqlaymiz. `initData` ba'zi
  // launch usullarida bo'sh kelishi mumkin — shунga qaramay Telegram deb hisoblaymiz.
  // (Oddiy brauzerda: initData bo'sh, user yo'q, platform 'unknown' → gate ko'rinadi.)
  if (!tg) return false;
  if (typeof tg.initData === 'string' && tg.initData.length > 0) return true;
  if (tg.initDataUnsafe && tg.initDataUnsafe.user && tg.initDataUnsafe.user.id) return true;
  if (tg.platform && tg.platform !== 'unknown') return true;
  return false;
}

function setShopLogo() {
  const logo = el('shopLogo');
  if (logo && State.config && State.config.shop_image) {
    logo.style.backgroundImage = `url(${State.config.shop_image})`;
  }
}

function showAuthBanner() {
  if (el('authBanner')) return;
  const b = document.createElement('div');
  b.id = 'authBanner';
  b.className = 'auth-banner';
  b.innerHTML = `<span data-ic="alert"></span><span>${L('open_via_menu')}</span>`;
  document.body.appendChild(b);
  applyIcons(b);
}

async function init() {
  // Faqat Telegram ichida ishlaydi.
  if (!isInTelegram()) { showTelegramGate(); return; }
  // Telegram ichida, lekin initData bo'sh bo'lsa — buyurtma/auth ishlamaydi.
  // Foydalanuvchini ishonchli ☰ menyu tugmasiga yo'naltiramiz.
  if (!tg.initData || tg.initData.length === 0) { showAuthBanner(); }
  applyIcons(document);
  try { State.config = await api('/config'); }
  catch (e) { State.config = { shop_name: "Do'kon", currency: "so'm", primary_color: '#7A573F', min_order_amount: 0, delivery_fee: 0, free_delivery_from: 0, is_open: true, delivery_slots: [] }; }
  el('searchInput').placeholder = L('search');
  el('productsTitle').textContent = L('products');
  el('shopName').textContent = State.config.shop_name || "Do'kon";
  el('shopStatus').textContent = L('online_shop');
  applyTheme();
  setShopLogo();
  if (State.config.is_open === false) { const cb = el('closedBanner'); cb.hidden = false; cb.querySelector('span:last-child').textContent = L('closed'); applyIcons(cb); }
  skeletonGrid();
  try { State.categories = await api('/categories'); } catch (e) { State.categories = []; }
  renderCategories();
  await loadProducts();
  try { renderBanners(await api('/banners')); } catch (e) {}
  updateBadge();
  const sp = el('splash'); sp.style.opacity = '0'; setTimeout(() => sp.style.display = 'none', 300);
}

function bindEvents() {
  document.querySelectorAll('.nav-item').forEach(n => n.onclick = () => switchView(n.dataset.nav));
  document.querySelectorAll('[data-close]').forEach(b => b.onclick = closeSheets);
  el('tbCart').onclick = () => switchView('cart');
  const goShop = el('emptyGoShop'); if (goShop) goShop.onclick = () => switchView('home');
  let searchTimer;
  el('searchInput').oninput = (e) => { State.search = e.target.value.trim(); el('searchClear').hidden = !State.search; clearTimeout(searchTimer); searchTimer = setTimeout(loadProducts, 350); };
  el('searchClear').onclick = () => { el('searchInput').value = ''; State.search = ''; el('searchClear').hidden = true; loadProducts(); };
  if (tg && tg.BackButton) tg.BackButton.onClick(closeSheets);
}

bindEvents();
init();
