/* Maxsulot Zakaz — Mini App (vanilla JS, Telegram WebApp) */
'use strict';

const tg = window.Telegram ? window.Telegram.WebApp : null;
if (tg) { tg.ready(); tg.expand(); }

// ── Holat ──
const State = {
  config: null,
  categories: [],
  products: [],
  cart: loadCart(),
  currentCategory: null,
  search: '',
  lang: (tg && tg.initDataUnsafe && tg.initDataUnsafe.user && tg.initDataUnsafe.user.language_code) || 'uz',
  view: 'home',
};
if (!['uz', 'ru', 'en'].includes(State.lang)) State.lang = 'uz';

// ── i18n (UI matnlari) ──
const I18N = {
  search: { uz: 'Qidirish...', ru: 'Поиск...', en: 'Search...' },
  products: { uz: 'Mahsulotlar', ru: 'Товары', en: 'Products' },
  all: { uz: 'Hammasi', ru: 'Все', en: 'All' },
  add: { uz: 'Savatga', ru: 'В корзину', en: 'Add' },
  cart: { uz: 'Savat', ru: 'Корзина', en: 'Cart' },
  cart_empty: { uz: 'Savat bo\'sh', ru: 'Корзина пуста', en: 'Cart is empty' },
  checkout: { uz: 'Rasmiylashtirish', ru: 'Оформить', en: 'Checkout' },
  order_btn: { uz: 'Buyurtma berish', ru: 'Заказать', en: 'Order' },
  items_total: { uz: 'Mahsulotlar', ru: 'Товары', en: 'Items' },
  delivery: { uz: 'Yetkazib berish', ru: 'Доставка', en: 'Delivery' },
  pickup: { uz: 'Olib ketish', ru: 'Самовывоз', en: 'Pickup' },
  total: { uz: 'Jami', ru: 'Итого', en: 'Total' },
  free: { uz: 'Bepul', ru: 'Бесплатно', en: 'Free' },
  out_of_stock: { uz: 'Tugadi', ru: 'Нет', en: 'Out' },
  min_order: { uz: 'Minimal buyurtma', ru: 'Мин. заказ', en: 'Min order' },
  name: { uz: 'Ismingiz', ru: 'Ваше имя', en: 'Your name' },
  phone: { uz: 'Telefon', ru: 'Телефон', en: 'Phone' },
  address: { uz: 'Manzil', ru: 'Адрес', en: 'Address' },
  note: { uz: 'Izoh (ixtiyoriy)', ru: 'Комментарий', en: 'Note' },
  payment: { uz: 'To\'lov', ru: 'Оплата', en: 'Payment' },
  cash: { uz: 'Naqd', ru: 'Наличные', en: 'Cash' },
  card: { uz: 'Karta', ru: 'Карта', en: 'Card' },
  no_orders: { uz: 'Buyurtmalar yo\'q 📦', ru: 'Нет заказов 📦', en: 'No orders 📦' },
  order_ok: { uz: '✅ Buyurtmangiz qabul qilindi!', ru: '✅ Заказ принят!', en: '✅ Order placed!' },
  closed: { uz: '⏰ Do\'kon hozir yopiq', ru: '⏰ Магазин закрыт', en: '⏰ Shop is closed' },
  delivery_fee: { uz: 'Yetkazib berish', ru: 'Доставка', en: 'Delivery' },
};
const ST = {
  created: { uz: 'Yangi', ru: 'Новый', en: 'New' },
  confirmed: { uz: 'Tasdiqlandi', ru: 'Подтверждён', en: 'Confirmed' },
  preparing: { uz: 'Tayyorlanmoqda', ru: 'Готовится', en: 'Preparing' },
  on_way: { uz: 'Yo\'lda', ru: 'В пути', en: 'On the way' },
  delivered: { uz: 'Yetkazildi', ru: 'Доставлен', en: 'Delivered' },
  completed: { uz: 'Yakunlandi', ru: 'Завершён', en: 'Completed' },
  canceled: { uz: 'Bekor qilindi', ru: 'Отменён', en: 'Canceled' },
  rejected: { uz: 'Rad etildi', ru: 'Отклонён', en: 'Rejected' },
};
const L = (k) => (I18N[k] && I18N[k][State.lang]) || (I18N[k] && I18N[k].uz) || k;

// ── DOM yordamchilari ──
const $ = (s) => document.querySelector(s);
const el = (id) => document.getElementById(id);

function money(n) {
  const cur = State.config ? State.config.currency : "so'm";
  return (Number(n) || 0).toLocaleString('ru-RU').replace(/,/g, ' ') + ' ' + cur;
}
function haptic(type) { try { tg && tg.HapticFeedback && tg.HapticFeedback.impactOccurred(type || 'light'); } catch (e) {} }

function toast(msg) {
  const t = el('toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(toast._t);
  toast._t = setTimeout(() => t.classList.remove('show'), 2200);
}

// ── API ──
async function api(path, options = {}) {
  const headers = Object.assign({ 'Content-Type': 'application/json' }, options.headers || {});
  if (tg && tg.initData) headers['X-Telegram-Init-Data'] = tg.initData;
  const res = await fetch('/api' + path, Object.assign({}, options, { headers }));
  if (!res.ok) {
    let detail = 'Xatolik';
    try { detail = (await res.json()).detail || detail; } catch (e) {}
    throw new Error(detail);
  }
  return res.json();
}

// ── Cart (localStorage) ──
function loadCart() {
  try { return JSON.parse(localStorage.getItem('cart') || '[]'); } catch (e) { return []; }
}
function saveCart() {
  localStorage.setItem('cart', JSON.stringify(State.cart));
  updateCartBadge();
}
function cartQty(id) { const it = State.cart.find(x => x.id === id); return it ? it.qty : 0; }
function cartCount() { return State.cart.reduce((s, x) => s + x.qty, 0); }
function cartItemsTotal() { return State.cart.reduce((s, x) => s + x.price * x.qty, 0); }

function addToCart(p) {
  const it = State.cart.find(x => x.id === p.id);
  if (it) it.qty += 1;
  else State.cart.push({ id: p.id, name: p.name, price: p.price, image: p.image, qty: 1 });
  saveCart(); haptic('light');
}
function changeQty(id, delta) {
  const it = State.cart.find(x => x.id === id);
  if (!it) return;
  it.qty += delta;
  if (it.qty <= 0) State.cart = State.cart.filter(x => x.id !== id);
  saveCart(); haptic('light');
}
function updateCartBadge() {
  const c = cartCount();
  const b = el('cartBadge');
  if (c > 0) { b.textContent = c; b.hidden = false; } else { b.hidden = true; }
}

// ── Render: bannerlar ──
function renderBanners(banners) {
  const wrap = el('banners');
  if (!banners || !banners.length) { wrap.style.display = 'none'; return; }
  wrap.style.display = 'flex';
  wrap.innerHTML = banners.map(b =>
    `<div class="banner" style="${b.image ? `background-image:url('${b.image}')` : ''}"></div>`
  ).join('');
}

// ── Render: kategoriyalar ──
function renderCategories() {
  const wrap = el('categories');
  let html = `<div class="cat-chip ${State.currentCategory === null ? 'active' : ''}" data-cat="all">
    <span class="emoji">🛒</span><span>${L('all')}</span></div>`;
  html += State.categories.map(c =>
    `<div class="cat-chip ${State.currentCategory === c.id ? 'active' : ''}" data-cat="${c.id}">
      <span class="emoji">${c.emoji || '🛍'}</span><span>${escapeHtml(c.name)}</span></div>`
  ).join('');
  wrap.innerHTML = html;
  wrap.querySelectorAll('.cat-chip').forEach(chip => {
    chip.onclick = () => {
      const v = chip.dataset.cat;
      State.currentCategory = v === 'all' ? null : Number(v);
      renderCategories();
      loadProducts();
    };
  });
}

// ── Render: mahsulotlar ──
function renderProducts() {
  const wrap = el('products');
  const empty = el('emptyProducts');
  if (!State.products.length) { wrap.innerHTML = ''; empty.hidden = false; return; }
  empty.hidden = true;
  wrap.innerHTML = State.products.map(p => productCard(p)).join('');
  bindProductCards();
}

function productCard(p) {
  const disc = p.old_price && p.old_price > p.price
    ? `<div class="discount-badge">-${Math.round((1 - p.price / p.old_price) * 100)}%</div>` : '';
  const out = !p.in_stock ? `<div class="out-badge">${L('out_of_stock')}</div>` : '';
  const img = p.image
    ? `<div class="img" style="background-image:url('${p.image}')"></div>`
    : `<div class="img">🛍</div>`;
  const qty = cartQty(p.id);
  let action;
  if (!p.in_stock) {
    action = `<button class="add" disabled style="opacity:.5">${L('out_of_stock')}</button>`;
  } else if (qty > 0) {
    action = `<div class="qty-mini" data-id="${p.id}">
      <button data-act="dec">−</button><span>${qty}</span><button data-act="inc">+</button></div>`;
  } else {
    action = `<button class="add" data-add="${p.id}">${L('add')}</button>`;
  }
  const old = p.old_price && p.old_price > p.price ? `<span class="old">${money(p.old_price)}</span>` : '';
  return `<div class="card" data-open="${p.id}">
    ${disc}${out}${img}
    <div class="info">
      <div class="price">${money(p.price)} ${old}</div>
      <div class="pname">${escapeHtml(p.name)}</div>
      ${action}
    </div></div>`;
}

function bindProductCards() {
  el('products').querySelectorAll('.card').forEach(card => {
    card.onclick = (e) => {
      if (e.target.closest('[data-add]') || e.target.closest('.qty-mini')) return;
      openProduct(Number(card.dataset.open));
    };
  });
  el('products').querySelectorAll('[data-add]').forEach(btn => {
    btn.onclick = (e) => { e.stopPropagation(); const p = State.products.find(x => x.id === Number(btn.dataset.add)); addToCart(p); renderProducts(); };
  });
  el('products').querySelectorAll('.qty-mini').forEach(q => {
    const id = Number(q.dataset.id);
    q.querySelector('[data-act="inc"]').onclick = (e) => { e.stopPropagation(); changeQty(id, 1); renderProducts(); };
    q.querySelector('[data-act="dec"]').onclick = (e) => { e.stopPropagation(); changeQty(id, -1); renderProducts(); };
  });
}

// ── Mahsulot detali (sheet) ──
async function openProduct(id) {
  let p = State.products.find(x => x.id === id);
  try { p = await api('/products/' + id); } catch (e) {}
  if (!p) return;
  const old = p.old_price && p.old_price > p.price ? `<span class="pd-old">${money(p.old_price)}</span>` : '';
  const img = p.image ? `<div class="pd-img" style="background-image:url('${p.image}')"></div>` : `<div class="pd-img">🛍</div>`;
  el('productContent').innerHTML = `
    ${img}
    <div class="pd-name">${escapeHtml(p.name)}</div>
    <div><span class="pd-price">${money(p.price)}</span>${old}</div>
    ${p.description ? `<div class="pd-desc">${escapeHtml(p.description)}</div>` : ''}
    <div class="pd-meta">${p.in_stock ? '✅ Mavjud' : '❌ ' + L('out_of_stock')}</div>
    <button class="btn" id="pdAdd" ${p.in_stock ? '' : 'disabled'}>${L('add')} • ${money(p.price)}</button>`;
  if (p.in_stock) el('pdAdd').onclick = () => { addToCart(p); closeSheets(); renderProducts(); toast('🛒 ' + L('add')); };
  openSheet('sheetProduct');
}

// ── Savat (sheet) ──
function renderCart() {
  const wrap = el('cartItems');
  const empty = el('cartEmpty');
  const footer = el('cartFooter');
  if (!State.cart.length) {
    wrap.innerHTML = ''; empty.hidden = false; footer.innerHTML = ''; return;
  }
  empty.hidden = true;
  wrap.innerHTML = State.cart.map(it => `
    <div class="cart-item">
      <div class="ci-img" style="${it.image ? `background-image:url('${it.image}')` : ''}"></div>
      <div class="ci-info"><div class="ci-name">${escapeHtml(it.name)}</div>
        <div class="ci-price">${money(it.price)}</div></div>
      <div class="qty">
        <button data-dec="${it.id}">−</button><span>${it.qty}</span><button data-inc="${it.id}">+</button>
      </div>
    </div>`).join('');
  wrap.querySelectorAll('[data-inc]').forEach(b => b.onclick = () => { changeQty(Number(b.dataset.inc), 1); renderCart(); renderProducts(); });
  wrap.querySelectorAll('[data-dec]').forEach(b => b.onclick = () => { changeQty(Number(b.dataset.dec), -1); renderCart(); renderProducts(); });

  const itemsTotal = cartItemsTotal();
  const min = State.config.min_order_amount || 0;
  const belowMin = min > 0 && itemsTotal < min;
  footer.innerHTML = `
    <div class="sum-row"><span>${L('items_total')}</span><span>${money(itemsTotal)}</span></div>
    <div class="sum-row total"><span>${L('total')}</span><span>${money(itemsTotal)}</span></div>
    ${belowMin ? `<div class="min-warn">${L('min_order')}: ${money(min)}</div>` : ''}
    <button class="btn" id="goCheckout" ${belowMin ? 'disabled' : ''}>${L('checkout')}</button>`;
  if (!belowMin) el('goCheckout').onclick = openCheckout;
}

// ── Checkout (sheet) ──
function openCheckout() {
  const user = (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) || {};
  const name = [user.first_name, user.last_name].filter(Boolean).join(' ');
  el('checkoutContent').innerHTML = `
    <div class="field"><label>${L('delivery')}</label>
      <div class="seg" id="segDelivery">
        <button class="active" data-v="delivery">🚚 ${L('delivery')}</button>
        <button data-v="pickup">🏃 ${L('pickup')}</button>
      </div></div>
    <div class="field"><label>${L('name')}</label><input id="ckName" value="${escapeAttr(name)}" /></div>
    <div class="field"><label>${L('phone')}</label><input id="ckPhone" type="tel" inputmode="tel" placeholder="+998 90 123 45 67" /></div>
    <div class="field" id="addrField"><label>${L('address')}</label><input id="ckAddr" placeholder="${L('address')}" /></div>
    <div class="field"><label>${L('payment')}</label>
      <div class="seg" id="segPay">
        <button class="active" data-v="cash">💵 ${L('cash')}</button>
        <button data-v="card">💳 ${L('card')}</button>
      </div></div>
    <div class="field"><label>${L('note')}</label><textarea id="ckNote" placeholder="${L('note')}"></textarea></div>
    <div id="ckSummary"></div>
    <button class="btn" id="submitOrder">${L('order_btn')}</button>`;

  let deliveryType = 'delivery';
  let payment = 'cash';
  const segD = el('segDelivery'), segP = el('segPay');
  segD.querySelectorAll('button').forEach(b => b.onclick = () => {
    segD.querySelectorAll('button').forEach(x => x.classList.remove('active'));
    b.classList.add('active'); deliveryType = b.dataset.v;
    el('addrField').style.display = deliveryType === 'pickup' ? 'none' : 'block';
    renderCkSummary(deliveryType);
  });
  segP.querySelectorAll('button').forEach(b => b.onclick = () => {
    segP.querySelectorAll('button').forEach(x => x.classList.remove('active'));
    b.classList.add('active'); payment = b.dataset.v;
  });

  renderCkSummary(deliveryType);
  closeSheet('sheetCart');
  openSheet('sheetCheckout');

  el('submitOrder').onclick = () => submitOrder(() => ({
    delivery_type: deliveryType,
    payment_method: payment,
    name: el('ckName').value.trim(),
    phone: el('ckPhone').value.trim(),
    address: el('ckAddr') ? el('ckAddr').value.trim() : '',
    note: el('ckNote').value.trim(),
  }));
}

function deliveryFeeFor(itemsTotal) {
  const c = State.config;
  if (!c) return 0;
  let fee = c.delivery_fee || 0;
  if (c.free_delivery_from && itemsTotal >= c.free_delivery_from) fee = 0;
  return fee;
}

function renderCkSummary(deliveryType) {
  const itemsTotal = cartItemsTotal();
  const fee = deliveryType === 'delivery' ? deliveryFeeFor(itemsTotal) : 0;
  el('ckSummary').innerHTML = `
    <div class="sum-row"><span>${L('items_total')}</span><span>${money(itemsTotal)}</span></div>
    ${deliveryType === 'delivery' ? `<div class="sum-row"><span>${L('delivery_fee')}</span><span>${fee ? money(fee) : L('free')}</span></div>` : ''}
    <div class="sum-row total"><span>${L('total')}</span><span>${money(itemsTotal + fee)}</span></div>`;
}

async function submitOrder(getData) {
  const d = getData();
  if (!d.phone || d.phone.length < 7) { toast('☎️ ' + L('phone')); return; }
  if (d.delivery_type === 'delivery' && !d.address) { toast('📍 ' + L('address')); return; }
  const btn = el('submitOrder');
  btn.disabled = true; btn.textContent = '...';
  try {
    const body = {
      items: State.cart.map(x => ({ product_id: x.id, qty: x.qty })),
      delivery_type: d.delivery_type,
      payment_method: d.payment_method,
      phone: d.phone,
      address: d.address,
      note: d.note,
    };
    await api('/orders', { method: 'POST', body: JSON.stringify(body) });
    State.cart = []; saveCart();
    closeSheets();
    haptic('medium');
    toast(L('order_ok'));
    switchView('orders');
    loadOrders();
  } catch (e) {
    toast('❌ ' + e.message);
    btn.disabled = false; btn.textContent = L('order_btn');
  }
}

// ── Buyurtmalar ──
async function loadOrders() {
  try {
    const orders = await api('/orders');
    const wrap = el('ordersList'), empty = el('emptyOrders');
    if (!orders.length) { wrap.innerHTML = ''; empty.hidden = false; empty.textContent = L('no_orders'); return; }
    empty.hidden = true;
    wrap.innerHTML = orders.map(o => {
      const stTxt = (ST[o.status] && ST[o.status][State.lang]) || o.status;
      const items = o.items.map(i => `${escapeHtml(i.name)}×${i.qty}`).join(', ');
      return `<div class="order-card">
        <div class="order-head"><span class="order-num">#${o.order_number}</span>
          <span class="order-status st-${o.status}">${stTxt}</span></div>
        <div class="order-items-mini">${items}</div>
        <div class="order-total">${money(o.grand_total)}</div></div>`;
    }).join('');
  } catch (e) { toast(e.message); }
}

// ── Sheets boshqaruvi ──
function openSheet(id) { el(id).classList.add('open'); if (tg && tg.BackButton) tg.BackButton.show(); }
function closeSheet(id) { el(id).classList.remove('open'); maybeHideBack(); }
function closeSheets() { document.querySelectorAll('.sheet').forEach(s => s.classList.remove('open')); maybeHideBack(); }
function maybeHideBack() {
  const anyOpen = document.querySelector('.sheet.open');
  if (!anyOpen && tg && tg.BackButton) tg.BackButton.hide();
}

// ── Navigatsiya ──
function switchView(view) {
  State.view = view;
  document.querySelectorAll('.nav-item').forEach(n => n.classList.toggle('active', n.dataset.nav === view));
  if (view === 'cart') { renderCart(); openSheet('sheetCart'); return; }
  if (view === 'search') { el('searchInput').focus(); view = 'home'; }
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  el('view-' + (view === 'search' ? 'home' : view)).classList.add('active');
  if (view === 'orders') loadOrders();
  window.scrollTo(0, 0);
}

// ── Yuklash ──
async function loadProducts() {
  try {
    const params = new URLSearchParams();
    if (State.currentCategory) params.set('category_id', State.currentCategory);
    if (State.search) params.set('q', State.search);
    State.products = await api('/products?' + params.toString());
    renderProducts();
  } catch (e) { toast(e.message); }
}

function applyTheme() {
  const color = (State.config && State.config.primary_color) || '#7000FF';
  document.documentElement.style.setProperty('--primary', color);
  if (tg) {
    try { tg.setHeaderColor && tg.setHeaderColor('#ffffff'); tg.setBackgroundColor && tg.setBackgroundColor('#f3f4f6'); } catch (e) {}
  }
}

async function init() {
  try {
    State.config = await api('/config');
  } catch (e) {
    State.config = { shop_name: "Do'kon", currency: "so'm", primary_color: '#7000FF', min_order_amount: 0, delivery_fee: 0, free_delivery_from: 0, is_open: true };
  }
  el('shopTitle').textContent = State.config.shop_name || "Do'kon";
  el('langBtn').textContent = State.lang.toUpperCase();
  el('searchInput').placeholder = L('search');
  el('productsTitle').textContent = L('products');
  applyTheme();
  if (State.config.is_open === false) el('closedBanner').hidden = false;

  try { State.categories = await api('/categories'); } catch (e) { State.categories = []; }
  renderCategories();
  await loadProducts();

  try { renderBanners(await api('/banners')); } catch (e) {}

  updateCartBadge();
  el('splash').style.display = 'none';
}

// ── Hodisalar ──
function bindEvents() {
  document.querySelectorAll('.nav-item').forEach(n => n.onclick = () => switchView(n.dataset.nav));
  document.querySelectorAll('[data-close]').forEach(b => b.onclick = closeSheets);

  // Qidiruv (debounce)
  let searchTimer;
  el('searchInput').oninput = (e) => {
    State.search = e.target.value.trim();
    el('searchClear').hidden = !State.search;
    clearTimeout(searchTimer);
    searchTimer = setTimeout(loadProducts, 350);
  };
  el('searchClear').onclick = () => { el('searchInput').value = ''; State.search = ''; el('searchClear').hidden = true; loadProducts(); };

  // Til almashtirish (uz -> ru -> en)
  el('langBtn').onclick = () => {
    const order = ['uz', 'ru', 'en'];
    State.lang = order[(order.indexOf(State.lang) + 1) % 3];
    el('langBtn').textContent = State.lang.toUpperCase();
    el('searchInput').placeholder = L('search');
    el('productsTitle').textContent = L('products');
    renderCategories(); renderProducts();
  };

  if (tg && tg.BackButton) tg.BackButton.onClick(closeSheets);
}

bindEvents();
init();

// ── Xavfsiz HTML ──
function escapeHtml(s) {
  return String(s || '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
function escapeAttr(s) { return escapeHtml(s).replace(/"/g, '&quot;'); }
