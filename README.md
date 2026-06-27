# Telegram Commerce Platform (multi-tenant SaaS)

> Bitta kod bazasi orqali **cheksiz biznesni** Telegram'da sotuvga ulaydigan professional commerce platformasi.
> Restoran, fast food, market, kiyim-kechak, gul do'koni, elektronika, dorixona — har qanday biznesga moslashadi.

Bu repozitoriy hozircha **loyihalash (design) fazasida**. Kod yozishdan oldin butun mahsulot
Product Manager / CTO darajasida tahlil qilindi: barcha modullar, foydalanuvchi oqimlari,
buyurtma hayot sikli, real hayotdagi muammolar va ularning yechimlari, ma'lumotlar modeli
va implementatsiya yo'l xaritasi hujjatlashtirildi.

---

## Tarkibi (komponentlar)

Barchasi **bitta Railway serverida**, **bitta Node.js jarayonida** ishga tushadi:

| Komponent | Vazifasi |
|-----------|----------|
| **Sotuv Bot** (Customer Bot) | Mijoz uchun kirish nuqtasi. Mini App'ni ochadi, buyurtma statuslari haqida xabar yuboradi. |
| **Admin Bot** | Biznes egasi/operatori uchun. Buyurtmani qabul qiladi, tasdiqlaydi, statusni boshqaradi, mahsulot/ombor boshqaruvi. |
| **Super Admin Bot** | Platforma egasi uchun. Bizneslarni ulaydi, o'chiradi, obunani boshqaradi, global statistika. |
| **Telegram Mini Web App** | Uzum/Yandex Market darajasidagi xarid interfeysi. Katalog, savat, to'lov, buyurtma. |
| **API + Realtime** | Mini App va botlar uchun yagona backend. Realtime yangilanishlar (narx, qoldiq, status). |

---

## Hujjatlar (loyiha tahlili)

To'liq tahlilni `docs/` ichidan o'qing — ketma-ketlik bo'yicha:

1. [`docs/01-product-vision-and-scope.md`](docs/01-product-vision-and-scope.md) — Mahsulot vizyoni, qiymat taklifi, modullar.
2. [`docs/02-architecture-and-techstack.md`](docs/02-architecture-and-techstack.md) — Arxitektura, texnologiya tanlovi, Railway deploy.
3. [`docs/03-multi-tenancy-and-security.md`](docs/03-multi-tenancy-and-security.md) — Multi-tenancy, izolyatsiya, rollar, xavfsizlik.
4. [`docs/04-user-flows.md`](docs/04-user-flows.md) — Customer, Admin, Operator, Courier, Super Admin oqimlari.
5. [`docs/05-order-lifecycle.md`](docs/05-order-lifecycle.md) — Buyurtma hayot sikli (state machine) va bildirishnomalar.
6. [`docs/06-edge-cases-and-resilience.md`](docs/06-edge-cases-and-resilience.md) — Real muammolar va ularning yechimlari.
7. [`docs/07-data-model.md`](docs/07-data-model.md) — Ma'lumotlar bazasi modeli (PostgreSQL).
8. [`docs/08-feature-catalog.md`](docs/08-feature-catalog.md) — To'liq imkoniyatlar katalogi.
9. [`docs/09-implementation-roadmap.md`](docs/09-implementation-roadmap.md) — Fazalar va yo'l xaritasi.

---

## Texnologiya (qisqacha)

- **Backend:** Node.js 22 + TypeScript, Fastify
- **Telegram:** grammY (webhook rejimi, ko'p-bot routing)
- **DB:** PostgreSQL + Prisma ORM (multi-tenant, `tenant_id` scoping)
- **Mini App:** React + Vite + TypeScript + Tailwind CSS
- **Realtime:** WebSocket / SSE + Postgres LISTEN/NOTIFY
- **Deploy:** Railway (single service), GitHub orqali CI/CD

To'liq asoslash uchun [`docs/02-architecture-and-techstack.md`](docs/02-architecture-and-techstack.md) ga qarang.

---

## Holat

🟡 **Design faza** — hujjatlar tayyor. Implementatsiya `docs/09-implementation-roadmap.md` bo'yicha bosqichma-bosqich boshlanadi.
