/* Maxsulot Zakaz — Mini App (Yandex Eats / Uzum Tezkor uslubi). Vanilla JS + Telegram WebApp + Leaflet */
'use strict';

const tg = window.Telegram ? window.Telegram.WebApp : null;
if (tg) { tg.ready(); tg.expand(); try { tg.enableClosingConfirmation(); } catch (e) {} }

const TASHKENT = { lat: 41.311081, lng: 69.279729 };

const State = {
  config: null, categories: [], products: [], cart: loadCart(),
  addresses: [], currentAddress: null, currentCategory: null, search: '',
  lang: localStorage.getItem('lang') || ((tg && tg.initDataUnsafe && tg.initDataUnsafe.user && tg.initDataUnsafe.user.language_code) || 'uz'),
  view: 'home', _map: null, _pickLat: null, _pickLng: null, _pickStreet: '',
};
if (!['uz', 'ru', 'en'].includes(State.lang)) State.lang = 'uz';

/* SVG ikonkalar (toza, professional) */
const IC = {
  chev: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>',
  pin: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="2.6"/></svg>',
  locate: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3.4"/><path d="M12 2v3.2M12 18.8V22M2 12h3.2M18.8 12H22"/></svg>',
  trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h16M9 7V5.5A1.5 1.5 0 0 1 10.5 4h3A1.5 1.5 0 0 1 15 5.5V7M7 7l.8 12.2A1.8 1.8 0 0 0 9.6 21h4.8a1.8 1.8 0 0 0 1.8-1.8L17 7"/></svg>',
  phone: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 4h3l2 5-2 1a11 11 0 0 0 5 5l1-2 5 2v3a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2Z"/></svg>',
  clock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
  shop: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 9 5 4h14l1 5M5 9v10h14V9M5 9h14"/></svg>',
  mapPin: '<svg viewBox="0 0 24 24" fill="currentColor" stroke="#fff" stroke-width="1.4"><path d="M12 23s8-7 8-13a8 8 0 1 0-16 0c0 6 8 13 8 13Z"/><circle cx="12" cy="10" r="3" fill="#fff" stroke="none"/></svg>',
};

const I18N = {
  search: { uz: 'Qidirish...', ru: 'Поиск...', en: 'Search...' },
  products: { uz: 'Mahsulotlar', ru: 'Товары', en: 'Products' },
  all: { uz: 'Hammasi', ru: 'Все', en: 'All' },
  add: { uz: 'Savatga', ru: 'В корзину', en: 'Add' },
  cart_empty: { uz: "Savat bo'sh", ru: 'Корзина пуста', en: 'Cart is empty' },
  checkout: { uz: 'Rasmiylashtirish', ru: 'Оформить', en: 'Checkout' },
  order_btn: { uz: 'Buyurtma berish', ru: 'Заказать', en: 'Order' },
  items_total: { uz: 'Mahsulotlar', ru: 'Товары', en: 'Items' },
  delivery: { uz: 'Yetkazib berish', ru: 'Доставка', en: 'Delivery' },
  pickup: { uz: 'Olib ketish', ru: 'Самовывоз', en: 'Pickup' },
  total: { uz: 'Jami', ru: 'Итого', en: 'Total' },
  free: { uz: 'Bepul', ru: 'Бесплатно', en: 'Free' },
  out_of_stock: { uz: 'Tugagan', ru: 'Нет', en: 'Out' },
  in_stock: { uz: 'Mavjud', ru: 'В наличии', en: 'In stock' },
  min_order: { uz: 'Minimal buyurtma', ru: 'Мин. заказ', en: 'Min order' },
  name: { uz: 'Ismingiz', ru: 'Ваше имя', en: 'Your name' },
  phone: { uz: 'Telefon', ru: 'Телефон', en: 'Phone' },
  note: { uz: 'Izoh (ixtiyoriy)', ru: 'Комментарий', en: 'Note' },
  payment: { uz: "To'lov", ru: 'Оплата', en: 'Payment' },
  cash: { uz: 'Naqd', ru: 'Наличные', en: 'Cash' },
  card: { uz: 'Karta', ru: 'Карта', en: 'Card' },
  no_orders: { uz: "Sizda hali buyurtmalar yo'q", ru: 'Заказов пока нет', en: 'No orders yet' },
  order_ok: { uz: '✅ Buyurtmangiz qabul qilindi!', ru: '✅ Заказ принят!', en: '✅ Order placed!' },
  delivery_fee: { uz: 'Yetkazib berish', ru: 'Доставка', en: 'Delivery' },
  add_address: { uz: 'Yangi manzil qo\'shish', ru: 'Добавить адрес', en: 'Add address' },
  add_address_title: { uz: 'Manzil qo\'shing', ru: 'Добавьте адрес', en: 'Add address' },
  add_address_hint: { uz: 'Yetkazib berish uchun manzil tanlang', ru: 'Выберите адрес доставки', en: 'Choose delivery address' },
  delivery_addr: { uz: 'Yetkazib berish manzili', ru: 'Адрес доставки', en: 'Delivery address' },
  my_addresses: { uz: 'Manzillarim', ru: 'Мои адреса', en: 'My addresses' },
  map_hint: { uz: 'Xaritani suring — belgi kerakli joyga to\'g\'rilansin', ru: 'Двигайте карту, чтобы указать точку', en: 'Move the map to set the point' },
  continue: { uz: 'Davom etish', ru: 'Продолжить', en: 'Continue' },
  save: { uz: 'Saqlash', ru: 'Сохранить', en: 'Save' },
  street: { uz: 'Ko\'cha / orientir', ru: 'Улица / ориентир', en: 'Street / landmark' },
  house: { uz: 'Uy', ru: 'Дом', en: 'House' },
  apartment: { uz: 'Kvartira', ru: 'Квартира', en: 'Apt.' },
  entrance: { uz: 'Podyezd', ru: 'Подъезд', en: 'Entrance' },
  floor: { uz: 'Etaj', ru: 'Этаж', en: 'Floor' },
  addr_comment: { uz: 'Kuryerga izoh', ru: 'Комментарий курьеру', en: 'Courier note' },
  label_home: { uz: 'Uy', ru: 'Дом', en: 'Home' },
  label_work: { uz: 'Ish', ru: 'Работа', en: 'Work' },
  label_other: { uz: 'Boshqa', ru: 'Другое', en: 'Other' },
  change: { uz: 'O\'zgartirish', ru: 'Изменить', en: 'Change' },
  need_phone: { uz: 'Telefon raqamni kiriting', ru: 'Введите номер', en: 'Enter phone' },
  need_address: { uz: 'Yetkazib berish manzilini qo\'shing', ru: 'Добавьте адрес', en: 'Add delivery address' },
  loc_fail: { uz: "Joylashuvni aniqlab bo'lmadi", ru: 'Не удалось определить локацию', en: 'Could not detect location' },
  map_unavailable: { uz: 'Xarita yuklanmadi. Manzilni qo\'lda kiriting:', ru: 'Карта не загрузилась. Введите адрес вручную:', en: 'Map unavailable. Enter address manually:' },
  language: { uz: 'Til', ru: 'Язык', en: 'Language' },
  contacts: { uz: 'Aloqa', ru: 'Контакты', en: 'Contacts' },
  type: { uz: 'Turi', ru: 'Тип', en: 'Type' },
};
const ST = {
  created: { uz: 'Yangi', ru: 'Новый', en: 'New' }, confirmed: { uz: 'Tasdiqlandi', ru: 'Подтверждён', en: 'Confirmed' },
  preparing: { uz: 'Tayyorlanmoqda', ru: 'Готовится', en: 'Preparing' }, on_way: { uz: "Yo'lda", ru: 'В пути', en: 'On the way' },
  delivered: { uz: 'Yetkazildi', ru: 'Доставлен', en: 'Delivered' }, completed: { uz: 'Yakunlandi', ru: 'Завершён', en: 'Completed' },
  canceled: { uz: 'Bekor qilindi', ru: 'Отменён', en: 'Canceled' }, rejected: { uz: 'Rad etildi', ru: 'Отклонён', en: 'Rejected' },
};
const L = (k) => (I18N[k] && I18N[k][State.lang]) || (I18N[k] && I18N[k].uz) || k;
const el = (id) => document.getElementById(id);

window.__imgErr = function (img) { const ph = img.getAttribute('data-ph') || '🛍'; const w = img.parentNode; if (w) w.innerHTML = '<div class="ph">' + ph + '</div>'; };
function imgHtml(src, ph) { if (src) return `<img src="${src}" alt="" loading="lazy" data-ph="${ph}" onerror="window.__imgErr(this)">`; return `<div class="ph">${ph}</div>`; }
function money(n) { const cur = State.config ? State.config.currency : "so'm"; return (Number(n) || 0).toLocaleString('ru-RU').replace(/,/g, ' ') + ' ' + cur; }
function haptic(t) { try { tg && tg.HapticFeedback && tg.HapticFeedback.impactOccurred(t || 'light'); } catch (e) {} }
function toast(msg) { const t = el('toast'); t.textContent = msg; t.classList.add('show'); clearTimeout(toast._t); toast._t = setTimeout(() => t.classList.remove('show'), 2400); }
function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }
function escAttr(s) { return esc(s).replace(/"/g, '&quot;'); }

async function api(path, options = {}) {
  const headers = Object.assign({ 'Content-Type': 'application/json' }, options.headers || {});
  if (tg && tg.initData) headers['X-Telegram-Init-Data'] = tg.initData;
  const res = await fetch('/api' + path, Object.assign({}, options, { headers }));
  if (!res.ok) { let d = 'Xatolik yuz berdi'; try { d = (await res.json()).detail || d; } catch (e) {} throw new Error(d); }
  return res.json();
}

/* Cart */
function loadCart() { try { return JSON.parse(localStorage.getItem('cart') || '[]'); } catch (e) { return []; } }
function saveCart() { localStorage.setItem('cart', JSON.stringify(State.cart)); updateBadge(); }
function cartQty(id) { const it = State.cart.find(x => x.id === id); return it ? it.qty : 0; }
function cartCount() { return State.cart.reduce((s, x) => s + x.qty, 0); }
function cartItemsTotal() { return State.cart.reduce((s, x) => s + x.price * x.qty, 0); }
function addToCart(p) { const it = State.cart.find(x => x.id === p.id); if (it) it.qty += 1; else State.cart.push({ id: p.id, name: p.name, price: p.price, image: p.image, qty: 1 }); saveCart(); haptic('light'); }
function changeQty(id, d) { const it = State.cart.find(x => x.id === id); if (!it) return; it.qty += d; if (it.qty <= 0) State.cart = State.cart.filter(x => x.id !== id); saveCart(); haptic('light'); }
function updateBadge() { const c = cartCount(); const b = el('cartBadge'); if (c > 0) { b.textContent = c; b.hidden = false; } else { b.hidden = true; } }

/* Address bar */
function renderAddressBar() {
  const a = State.currentAddress;
  if (a) { el('abLabel').textContent = a.label || L('delivery_addr'); el('abTitle').innerHTML = esc(a.text) + IC.chev; }
  else { el('abLabel').textContent = L('delivery_addr'); el('abTitle').innerHTML = L('add_address_title') + IC.chev; }
}

/* Banners / Categories / Products */
function renderBanners(banners) {
  const wrap = el('banners');
  if (!banners || !banners.length) { wrap.style.display = 'none'; return; }
  wrap.style.display = 'flex';
  wrap.innerHTML = banners.map(b => `<div class="banner">${b.image ? imgHtml(b.image, '') : ''}</div>`).join('');
}
function renderCategories() {
  const wrap = el('categories');
  let html = `<div class="cat-chip ${State.currentCategory === null ? 'active' : ''}" data-cat="all"><span class="cc-ic">🛍️</span><span class="lbl">${L('all')}</span></div>`;
  html += State.categories.map(c => `<div class="cat-chip ${State.currentCategory === c.id ? 'active' : ''}" data-cat="${c.id}"><span class="cc-ic">${c.emoji || '🛍'}</span><span class="lbl">${esc(c.name)}</span></div>`).join('');
  wrap.innerHTML = html;
  wrap.querySelectorAll('.cat-chip').forEach(chip => chip.onclick = () => { const v = chip.dataset.cat; State.currentCategory = v === 'all' ? null : Number(v); renderCategories(); loadProducts(); });
}
function skeletonGrid() { el('products').innerHTML = Array.from({ length: 6 }).map(() => `<div class="skeleton"><div class="sk-img"></div><div class="sk-line" style="width:55%"></div><div class="sk-line" style="width:85%"></div></div>`).join(''); }
function renderProducts() {
  const wrap = el('products'), empty = el('emptyProducts');
  if (!State.products.length) { wrap.innerHTML = ''; empty.hidden = false; return; }
  empty.hidden = true; wrap.innerHTML = State.products.map(productCard).join(''); bindCards();
}
function productCard(p) {
  const disc = p.old_price && p.old_price > p.price ? `<div class="discount-badge">-${Math.round((1 - p.price / p.old_price) * 100)}%</div>` : '';
  const out = !p.in_stock ? `<div class="out-badge">${L('out_of_stock')}</div>` : '';
  const qty = cartQty(p.id); let action;
  if (!p.in_stock) action = `<button class="add" disabled style="opacity:.5">${L('out_of_stock')}</button>`;
  else if (qty > 0) action = `<div class="qty-mini" data-id="${p.id}"><button data-act="dec">−</button><span>${qty}</span><button data-act="inc">+</button></div>`;
  else action = `<button class="add" data-add="${p.id}">${L('add')}</button>`;
  const old = p.old_price && p.old_price > p.price ? `<span class="old">${money(p.old_price)}</span>` : '';
  return `<div class="card" data-open="${p.id}"><div class="imgwrap">${disc}${imgHtml(p.image, '🛍')}${out}</div><div class="info"><div class="price">${money(p.price)} ${old}</div><div class="pname">${esc(p.name)}</div>${action}</div></div>`;
}
function bindCards() {
  const wrap = el('products');
  wrap.querySelectorAll('.card').forEach(c => c.onclick = (e) => { if (e.target.closest('[data-add]') || e.target.closest('.qty-mini')) return; openProduct(Number(c.dataset.open)); });
  wrap.querySelectorAll('[data-add]').forEach(b => b.onclick = (e) => { e.stopPropagation(); addToCart(State.products.find(x => x.id === Number(b.dataset.add))); renderProducts(); });
  wrap.querySelectorAll('.qty-mini').forEach(q => { const id = Number(q.dataset.id); q.querySelector('[data-act="inc"]').onclick = (e) => { e.stopPropagation(); changeQty(id, 1); renderProducts(); }; q.querySelector('[data-act="dec"]').onclick = (e) => { e.stopPropagation(); changeQty(id, -1); renderProducts(); }; });
}
async function openProduct(id) {
  let p = State.products.find(x => x.id === id);
  try { p = await api('/products/' + id); } catch (e) {}
  if (!p) return;
  const old = p.old_price && p.old_price > p.price ? `<span class="pd-old">${money(p.old_price)}</span>` : '';
  el('productContent').innerHTML = `<div class="pd-img">${imgHtml(p.image, '🛍')}</div><div class="pd-name">${esc(p.name)}</div><div><span class="pd-price">${money(p.price)}</span>${old}</div>${p.description ? `<div class="pd-desc">${esc(p.description)}</div>` : ''}<div class="pd-meta">${p.in_stock ? '✓ ' + L('in_stock') : '✕ ' + L('out_of_stock')}</div><button class="btn" id="pdAdd" ${p.in_stock ? '' : 'disabled'}>${L('add')} • ${money(p.price)}</button>`;
  if (p.in_stock) el('pdAdd').onclick = () => { addToCart(p); closeSheets(); renderProducts(); toast('🛒 ' + L('add')); };
  openSheet('sheetProduct');
}

/* Cart view */
function renderCart() {
  const wrap = el('cartItems'), empty = el('cartEmpty'), footer = el('cartFooter');
  if (!State.cart.length) { wrap.innerHTML = ''; empty.hidden = false; empty.textContent = L('cart_empty'); footer.innerHTML = ''; return; }
  empty.hidden = true;
  wrap.innerHTML = State.cart.map(it => `<div class="cart-item"><div class="ci-img">${imgHtml(it.image, '🛍')}</div><div class="ci-info"><div class="ci-name">${esc(it.name)}</div><div class="ci-price">${money(it.price)}</div></div><div class="qty"><button data-dec="${it.id}">−</button><span>${it.qty}</span><button data-inc="${it.id}">+</button></div></div>`).join('');
  wrap.querySelectorAll('[data-inc]').forEach(b => b.onclick = () => { changeQty(Number(b.dataset.inc), 1); renderCart(); renderProducts(); });
  wrap.querySelectorAll('[data-dec]').forEach(b => b.onclick = () => { changeQty(Number(b.dataset.dec), -1); renderCart(); renderProducts(); });
  const itemsTotal = cartItemsTotal(), min = State.config.min_order_amount || 0, belowMin = min > 0 && itemsTotal < min;
  footer.innerHTML = `<div class="cf-inner"><div class="sum-row"><span>${L('items_total')}</span><span>${money(itemsTotal)}</span></div><div class="sum-row total"><span>${L('total')}</span><span>${money(itemsTotal)}</span></div>${belowMin ? `<div class="min-warn">${L('min_order')}: ${money(min)}</div>` : ''}<button class="btn" id="goCheckout" ${belowMin ? 'disabled' : ''}>${L('checkout')}</button></div>`;
  if (!belowMin) el('goCheckout').onclick = openCheckout;
}

/* Checkout */
function openCheckout() {
  const user = (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) || {};
  const name = [user.first_name, user.last_name].filter(Boolean).join(' ');
  el('checkoutContent').innerHTML = `
    <div class="field"><label>${L('delivery')}</label><div class="seg" id="segDelivery"><button class="active" data-v="delivery">🚚 ${L('delivery')}</button><button data-v="pickup">🏃 ${L('pickup')}</button></div></div>
    <div id="coAddrBox"></div>
    <div class="field"><label>${L('name')}</label><input id="ckName" value="${escAttr(name)}" /></div>
    <div class="field"><label>${L('phone')}</label><input id="ckPhone" type="tel" inputmode="tel" placeholder="+998 90 123 45 67" /></div>
    <div class="field"><label>${L('payment')}</label><div class="seg" id="segPay"><button class="active" data-v="cash">💵 ${L('cash')}</button><button data-v="card">💳 ${L('card')}</button></div></div>
    <div class="field"><label>${L('note')}</label><textarea id="ckNote" placeholder="${L('note')}"></textarea></div>
    <div id="ckSummary"></div>
    <button class="btn" id="submitOrder">${L('order_btn')}</button>`;
  let deliveryType = 'delivery', payment = 'cash';
  const segD = el('segDelivery'), segP = el('segPay');
  const renderAddr = () => {
    const box = el('coAddrBox');
    if (deliveryType !== 'delivery') { box.innerHTML = ''; return; }
    const a = State.currentAddress;
    box.innerHTML = a
      ? `<div class="co-address"><span class="ca-ic">${IC.pin}</span><div class="ca-text"><b>${esc(a.label)}</b><small>${esc(a.text)}</small></div><span class="ca-change" id="coChange">${L('change')}</span></div>`
      : `<button class="btn btn-soft" id="coAddBtn" style="margin-bottom:16px">📍 ${L('need_address')}</button>`;
    const ch = el('coChange'); if (ch) ch.onclick = openAddressSheet;
    const ab = el('coAddBtn'); if (ab) ab.onclick = openAddressSheet;
  };
  segD.querySelectorAll('button').forEach(b => b.onclick = () => { segD.querySelectorAll('button').forEach(x => x.classList.remove('active')); b.classList.add('active'); deliveryType = b.dataset.v; renderAddr(); renderSummary(deliveryType); });
  segP.querySelectorAll('button').forEach(b => b.onclick = () => { segP.querySelectorAll('button').forEach(x => x.classList.remove('active')); b.classList.add('active'); payment = b.dataset.v; });
  renderAddr(); renderSummary(deliveryType);
  openSheet('sheetCheckout');
  el('submitOrder').onclick = () => submitOrder(() => ({ delivery_type: deliveryType, payment_method: payment, name: el('ckName').value.trim(), phone: el('ckPhone').value.trim(), note: el('ckNote').value.trim() }));
}
function deliveryFeeFor(t) { const c = State.config; if (!c) return 0; let f = c.delivery_fee || 0; if (c.free_delivery_from && t >= c.free_delivery_from) f = 0; return f; }
function renderSummary(deliveryType) {
  const itemsTotal = cartItemsTotal(), fee = deliveryType === 'delivery' ? deliveryFeeFor(itemsTotal) : 0;
  el('ckSummary').innerHTML = `<div class="sum-row"><span>${L('items_total')}</span><span>${money(itemsTotal)}</span></div>${deliveryType === 'delivery' ? `<div class="sum-row"><span>${L('delivery_fee')}</span><span>${fee ? money(fee) : L('free')}</span></div>` : ''}<div class="sum-row total"><span>${L('total')}</span><span>${money(itemsTotal + fee)}</span></div>`;
}
async function submitOrder(getData) {
  const d = getData();
  if (!d.phone || d.phone.replace(/\D/g, '').length < 7) { toast('☎️ ' + L('need_phone')); return; }
  if (d.delivery_type === 'delivery' && !State.currentAddress) { toast('📍 ' + L('need_address')); openAddressSheet(); return; }
  const btn = el('submitOrder'); btn.disabled = true; btn.textContent = '⏳...';
  try {
    const body = { items: State.cart.map(x => ({ product_id: x.id, qty: x.qty })), delivery_type: d.delivery_type, payment_method: d.payment_method, phone: d.phone, note: d.note };
    if (d.delivery_type === 'delivery' && State.currentAddress) body.address_id = State.currentAddress.id;
    await api('/orders', { method: 'POST', body: JSON.stringify(body) });
    State.cart = []; saveCart(); closeSheets(); haptic('medium'); toast(L('order_ok'));
    switchView('orders');
  } catch (e) { toast('❌ ' + e.message); btn.disabled = false; btn.textContent = L('order_btn'); }
}

/* Orders */
async function loadOrders() {
  try {
    const orders = await api('/orders');
    const wrap = el('ordersList'), empty = el('emptyOrders');
    if (!orders.length) { wrap.innerHTML = ''; empty.hidden = false; empty.textContent = L('no_orders'); return; }
    empty.hidden = true;
    wrap.innerHTML = orders.map(o => { const stTxt = (ST[o.status] && ST[o.status][State.lang]) || o.status; const items = o.items.map(i => `${esc(i.name)} ×${i.qty}`).join(', '); return `<div class="order-card"><div class="order-head"><span class="order-num">#${o.order_number}</span><span class="order-status st-${o.status}">${stTxt}</span></div><div class="order-items-mini">${items}</div><div class="order-total">${money(o.grand_total)}</div></div>`; }).join('');
  } catch (e) { toast(e.message); }
}

/* Addresses */
async function loadAddresses() {
  try { State.addresses = await api('/addresses'); } catch (e) { State.addresses = []; }
  State.currentAddress = State.addresses.find(a => a.is_default) || State.addresses[0] || null;
  renderAddressBar();
}
function openAddressSheet() {
  const list = State.addresses.map(a => `
    <div class="addr-item ${State.currentAddress && State.currentAddress.id === a.id ? 'active' : ''}" data-pick="${a.id}">
      <span class="ai-ic">${IC.pin}</span>
      <div class="ai-text"><b>${esc(a.label)}</b><small>${esc(a.text)}</small></div>
      <button class="ai-del" data-del="${a.id}">${IC.trash}</button>
    </div>`).join('');
  el('addressContent').innerHTML = `
    <h2 class="sheet-title">${L('my_addresses')}</h2>
    <div class="addr-list">${list || `<div class="empty" style="padding:24px 0">${L('add_address_hint')}</div>`}</div>
    <button class="btn" id="newAddrBtn">+ ${L('add_address')}</button>`;
  el('addressContent').querySelectorAll('[data-pick]').forEach(it => it.onclick = async (e) => {
    if (e.target.closest('[data-del]')) return;
    const id = Number(it.dataset.pick);
    try { await api(`/addresses/${id}/default`, { method: 'POST' }); } catch (e2) {}
    await loadAddresses(); closeSheets();
  });
  el('addressContent').querySelectorAll('[data-del]').forEach(b => b.onclick = async (e) => {
    e.stopPropagation();
    try { await api(`/addresses/${Number(b.dataset.del)}`, { method: 'DELETE' }); } catch (e2) {}
    await loadAddresses(); openAddressSheet();
  });
  el('newAddrBtn').onclick = openMapStep;
  openSheet('sheetAddress');
}
function openMapStep() {
  // Leaflet yuklanmagan bo'lsa — manual forma
  if (!window.L) {
    State._pickLat = null; State._pickLng = null; State._pickStreet = '';
    openAddressForm(true);
    return;
  }
  el('addressContent').innerHTML = `
    <div class="map-step">
      <h2 class="sheet-title">${L('add_address_title')}</h2>
      <div class="map-wrap" id="mapWrap"><div id="mapEl"></div><div class="map-pin" style="color:var(--primary)">${IC.mapPin}</div><button class="map-locate" id="locBtn" type="button">${IC.locate}</button></div>
      <div class="map-hint">${L('map_hint')}</div>
      <button class="btn" id="mapContinue">${L('continue')}</button>
    </div>`;
  openSheet('sheetAddress');
  el('locBtn').onclick = locateMe;
  el('mapContinue').onclick = () => {
    let lat = TASHKENT.lat, lng = TASHKENT.lng;
    if (State._map) { const c = State._map.getCenter(); lat = +c.lat.toFixed(7); lng = +c.lng.toFixed(7); }
    State._pickLat = lat; State._pickLng = lng; State._pickStreet = '';
    openAddressForm(false);
    reverseGeocode(lat, lng).then(s => { const inp = el('afStreet'); if (s && inp && !inp.value) inp.value = s; });
  };
  // Sheet animatsiyasi tugagandan keyin xaritani ishga tushiramiz
  // MutationObserver + fallback timeout orqali DOM tayyor bo'lishini kutamiz
  _initMapWhenReady();
}
function _initMapWhenReady() {
  // Eski xaritani tozalash
  try { if (State._map) { State._map.remove(); State._map = null; } } catch (e) {}

  let attempts = 0;
  const MAX_ATTEMPTS = 40; // 40 × 50ms = 2 soniya

  function tryInit() {
    attempts++;
    const node = el('mapEl');
    const wrap = el('mapWrap');
    if (!node || !wrap || !window.L) {
      if (attempts < MAX_ATTEMPTS) { setTimeout(tryInit, 50); }
      else { openAddressForm(true); } // fallback: manual forma
      return;
    }
    // Container o'lchami nol bo'lsa — kutamiz
    const rect = wrap.getBoundingClientRect();
    if (rect.width < 10 || rect.height < 10) {
      if (attempts < MAX_ATTEMPTS) { setTimeout(tryInit, 50); }
      else { openAddressForm(true); }
      return;
    }
    initMap(node);
  }
  setTimeout(tryInit, 80);
}

function initMap(node) {
  if (!node) node = el('mapEl');
  if (!node || !window.L) return;
  try { if (State._map) { State._map.remove(); State._map = null; } } catch (e) {}
  const start = (State.currentAddress && State.currentAddress.lat)
    ? { lat: State.currentAddress.lat, lng: State.currentAddress.lng }
    : TASHKENT;
  try {
    State._map = L.map(node, {
      zoomControl: true,
      attributionControl: false,
      tap: true,
      dragging: true,
    }).setView([start.lat, start.lng], 15);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      subdomains: 'abc',
      crossOrigin: true,
    }).addTo(State._map);

    // Hajmni bir necha marta qayta hisoblash (sheet animatsiyasi davomida)
    [100, 300, 600, 1000].forEach(ms =>
      setTimeout(() => { try { State._map && State._map.invalidateSize(true); } catch (e) {} }, ms)
    );
  } catch (e) {
    console.error('Map init error:', e);
    State._map = null;
    openAddressForm(true);
  }
}
function locateMe() {
  if (!navigator.geolocation) { toast(L('loc_fail')); return; }
  const btn = el('locBtn'); const orig = btn.innerHTML; btn.innerHTML = '⏳';
  navigator.geolocation.getCurrentPosition(
    (pos) => { if (State._map) State._map.setView([pos.coords.latitude, pos.coords.longitude], 17); btn.innerHTML = orig; haptic('medium'); },
    () => { btn.innerHTML = orig; toast(L('loc_fail')); },
    { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
  );
}
async function reverseGeocode(lat, lng) {
  try {
    const url = `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&accept-language=${State.lang}&zoom=18`;
    const r = await fetch(url, {
      headers: { 'Accept': 'application/json' },
    });
    if (!r.ok) return '';
    const j = await r.json();
    const a = j.address || {};
    return [a.road, a.house_number, a.neighbourhood || a.suburb || a.city_district]
      .filter(Boolean).join(', ') || '';
  } catch (e) {
    return '';
  }
}
function openAddressForm(manual) {
  const labels = [['Uy', L('label_home')], ['Ish', L('label_work')], ['Boshqa', L('label_other')]];
  el('addressContent').innerHTML = `
    <h2 class="sheet-title">${L('add_address_title')}</h2>
    ${manual ? `<div class="map-fallback">${L('map_unavailable')}</div>` : ''}
    <div class="field"><label>${L('type')}</label><div class="chips" id="labelChips">${labels.map((l, i) => `<button class="chip ${i === 0 ? 'active' : ''}" data-l="${l[0]}">${l[1]}</button>`).join('')}</div></div>
    <div class="field"><label>${L('street')}</label><input id="afStreet" value="${escAttr(State._pickStreet)}" placeholder="${L('street')}" /></div>
    <div class="field-row"><div class="field"><label>${L('house')}</label><input id="afHouse" /></div><div class="field"><label>${L('apartment')}</label><input id="afApt" inputmode="numeric" /></div></div>
    <div class="field-row"><div class="field"><label>${L('entrance')}</label><input id="afEnt" inputmode="numeric" /></div><div class="field"><label>${L('floor')}</label><input id="afFloor" inputmode="numeric" /></div></div>
    <div class="field"><label>${L('addr_comment')}</label><textarea id="afComment" placeholder="${L('addr_comment')}"></textarea></div>
    <button class="btn" id="afSave">${L('save')}</button>`;
  let label = 'Uy';
  el('labelChips').querySelectorAll('.chip').forEach(c => c.onclick = () => { el('labelChips').querySelectorAll('.chip').forEach(x => x.classList.remove('active')); c.classList.add('active'); label = c.dataset.l; });
  el('afSave').onclick = async () => {
    const street = el('afStreet').value.trim(), house = el('afHouse').value.trim();
    if (!street && !house) { toast(L('street')); return; }
    const btn = el('afSave'); btn.disabled = true; btn.textContent = '⏳...';
    try {
      await api('/addresses', { method: 'POST', body: JSON.stringify({
        label, lat: State._pickLat, lng: State._pickLng, street, house,
        apartment: el('afApt').value.trim(), entrance: el('afEnt').value.trim(),
        floor: el('afFloor').value.trim(), comment: el('afComment').value.trim(), make_default: true,
      }) });
      await loadAddresses(); closeSheets(); haptic('medium'); toast('✅ ' + L('save'));
    } catch (e) { toast('❌ ' + e.message); btn.disabled = false; btn.textContent = L('save'); }
  };
}

/* Profile */
function renderProfile() {
  const user = (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) || {};
  const name = [user.first_name, user.last_name].filter(Boolean).join(' ') || 'Mijoz';
  const initial = (name.trim()[0] || 'M').toUpperCase();
  const c = State.config || {};
  const langs = [['uz', "O'zbek"], ['ru', 'Русский'], ['en', 'English']];
  const addrRows = State.addresses.map(a => `<div class="prof-row"><span class="pr-ic">${IC.pin}</span><div class="pr-text"><b>${esc(a.label)}</b><br><small>${esc(a.text)}</small></div><button class="ai-del" data-del="${a.id}">${IC.trash}</button></div>`).join('');
  el('profileContent').innerHTML = `
    <div class="profile">
      <div class="prof-card"><div class="prof-head"><div class="prof-avatar">${initial}</div><div><div class="prof-name">${esc(name)}</div><div class="prof-phone">${user.username ? '@' + esc(user.username) : ''}</div></div></div></div>
      <div class="prof-card"><div class="prof-section-title">${L('language')}</div><div class="lang-row">${langs.map(l => `<button class="lang-pick ${State.lang === l[0] ? 'active' : ''}" data-lang="${l[0]}">${l[1]}</button>`).join('')}</div></div>
      <div class="prof-card"><div class="prof-section-title">${L('my_addresses')}</div>${addrRows || `<div style="color:var(--muted);font-size:14px;padding:4px 2px">${L('add_address_hint')}</div>`}<button class="btn-add-addr" id="profAddAddr">+ ${L('add_address')}</button></div>
      <div class="prof-card"><div class="prof-section-title">${L('contacts')}</div>
        <div class="prof-row"><span class="pr-ic">${IC.shop}</span><div class="pr-text">${esc(c.shop_name || '')}</div></div>
        ${c.phone ? `<div class="prof-row"><span class="pr-ic">${IC.phone}</span><div class="pr-text">${esc(c.phone)}</div></div>` : ''}
        ${c.working_hours ? `<div class="prof-row"><span class="pr-ic">${IC.clock}</span><div class="pr-text">${esc(c.working_hours)}</div></div>` : ''}
      </div>
    </div>`;
  el('profileContent').querySelectorAll('[data-lang]').forEach(b => b.onclick = () => { setLang(b.dataset.lang); renderProfile(); });
  el('profileContent').querySelectorAll('[data-del]').forEach(b => b.onclick = async () => { try { await api(`/addresses/${Number(b.dataset.del)}`, { method: 'DELETE' }); } catch (e) {} await loadAddresses(); renderProfile(); });
  const add = el('profAddAddr'); if (add) add.onclick = openMapStep;
}

function openSheet(id) {
  el(id).classList.add('open');
  if (tg && tg.BackButton) tg.BackButton.show();
}
function closeSheets() {
  document.querySelectorAll('.sheet').forEach(s => s.classList.remove('open'));
  try { if (State._map) { State._map.remove(); State._map = null; } } catch (e) {}
  if (tg && tg.BackButton) tg.BackButton.hide();
}

/* Nav */
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

function setLang(lang) { State.lang = lang; localStorage.setItem('lang', lang); el('searchInput').placeholder = L('search'); el('productsTitle').textContent = L('products'); renderAddressBar(); renderCategories(); renderProducts(); }

function applyTheme() {
  const color = (State.config && State.config.primary_color) || '#7000FF';
  if (/^#([0-9a-f]{3}){1,2}$/i.test(color)) document.documentElement.style.setProperty('--primary', color);
  if (tg) { try { tg.setHeaderColor && tg.setHeaderColor('#ffffff'); tg.setBackgroundColor && tg.setBackgroundColor('#f6f7f9'); } catch (e) {} }
}

async function init() {
  try { State.config = await api('/config'); }
  catch (e) { State.config = { shop_name: "Do'kon", currency: "so'm", primary_color: '#7000FF', min_order_amount: 0, delivery_fee: 0, free_delivery_from: 0, is_open: true }; }
  el('searchInput').placeholder = L('search');
  el('productsTitle').textContent = L('products');
  applyTheme();
  if (State.config.is_open === false) el('closedBanner').hidden = false;
  skeletonGrid();
  try { State.categories = await api('/categories'); } catch (e) { State.categories = []; }
  renderCategories();
  await loadProducts();
  try { renderBanners(await api('/banners')); } catch (e) {}
  await loadAddresses();
  updateBadge();
  el('splash').style.display = 'none';
}

function bindEvents() {
  document.querySelectorAll('.nav-item').forEach(n => n.onclick = () => switchView(n.dataset.nav));
  document.querySelectorAll('[data-close]').forEach(b => b.onclick = closeSheets);
  el('addressBar').onclick = openAddressSheet;
  let searchTimer;
  el('searchInput').oninput = (e) => { State.search = e.target.value.trim(); el('searchClear').hidden = !State.search; clearTimeout(searchTimer); searchTimer = setTimeout(loadProducts, 350); };
  el('searchClear').onclick = () => { el('searchInput').value = ''; State.search = ''; el('searchClear').hidden = true; loadProducts(); };
  if (tg && tg.BackButton) tg.BackButton.onClick(closeSheets);
}

bindEvents();
init();
