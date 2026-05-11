# DIPLOMA_PLAN.md — План диплома по неделям

> Главный план работ. Идём по неделям, каждый день — конкретные файлы и задачи. План рассчитан на 6 недель + 1 буфер.

---

## 🎯 Главная фишка диплома

**AI-геолокационный поиск инвентаря по всей РФ.**

Пользователь пишет в свободной форме: «найди недорогие беговые лыжи в Казани на завтра».
Система:
1. LLM (OpenAI/Claude API) парсит запрос → извлекает категорию, ценовой диапазон, город, дату.
2. Yandex Geocoder → координаты Казани.
3. БД ищет инвентарь: по категории + городу + датам + (опционально) семантической близости через pgvector embeddings.
4. Фронт показывает результат на Yandex-карте + списком карточек.

Это даёт диплому: применение ИИ (LLM + embeddings), vector DB (pgvector), интеграцию с внешним API, реальную пользу для пользователя.

---

## 📅 План по неделям

| Неделя | Главная тема | Результат |
|--------|--------------|-----------|
| 1 | Docker + базовая инфраструктура + NDA | Всё запускается через `docker-compose up`. Регистрация с NDA для паспорта. |
| 2 | Расширение на РФ (города, точки выдачи) | У инвентаря есть город и точка выдачи. Фильтр по городу. |
| 3 | REST API на DRF + JWT | Все ключевые модели доступны через API. JWT в httpOnly cookie. |
| 4 | React фронт — каркас и каталог | Vite + TS + Tailwind. Главная, каталог, детали, логин/регистрация. |
| 5 | AI-геопоиск + карта Yandex | Естественно-языковой поиск работает. На карте показаны метки. |
| 6 | Полировка, паттерны, тесты, демо | Signals (Наблюдатель), декораторы, тесты, populate_db с РФ-данными. |
| 7 (буфер) | Доделки + ПЗ-обновление + защита | Резерв на непредвиденное. |

---

## 📌 Неделя 1 — Docker + инфраструктура + NDA

### День 1 — docker-compose.yml

**Цель:** все сервисы стартуют одной командой.

Файлы создать/изменить:
- `Dockerfile` (в корне)
- `docker-compose.yml` (в корне)
- `docker-compose.override.yml` (опционально, для dev)
- `.dockerignore`
- `sport_kursach/sportrent/config/settings.py` — читать переменные из `.env`, добавить hosts для Docker
- `.env.example` — добавить `REDIS_URL`, `MONGO_URL`

Сервисы в compose:
- `web` (Django+Daphne)
- `db` (PostgreSQL 16 с расширением pgvector — образ `pgvector/pgvector:pg16`)
- `redis` (`redis:7-alpine`) — для channel layer
- `mongo` (`mongo:7`) — для логов и чатов
- `nginx` (`nginx:alpine`) — reverse-proxy перед Daphne, отдаёт статику и медиа

**Проверка:** `docker-compose up -d` → `docker-compose exec web python manage.py migrate` → открыть `http://localhost/` → каталог открывается.

**Коммит:** `feat(infra): add docker-compose with postgres, redis, mongo, nginx`

### День 2 — Channels на Redis + Mongo для логов

Файлы:
- `sport_kursach/sportrent/config/settings.py` — `CHANNEL_LAYERS` через `channels_redis.core.RedisChannelLayer`, добавить кастомный logging handler для Mongo
- `sport_kursach/requirements.txt` — добавить `channels-redis`, `pymongo`
- `sport_kursach/sportrent/core/mongo_logger.py` — handler, который пишет в MongoDB
- `sport_kursach/sportrent/chat/` — настроить чтобы сообщения дублировались в Mongo (или сохранялись только туда, обсудить)

**Тесты:**
- Открыть чат в двух вкладках, отправить сообщение — должно дойти через Redis pubsub
- Проверить в Mongo через `docker-compose exec mongo mongosh` что логи и сообщения пишутся

**Коммит:** `feat(infra): redis channel layer + mongodb logging`

### День 3 — NDA-соглашение на паспорт

Файлы:
- `sport_kursach/sportrent/users/models.py` — новая модель `PassportNDA(user, version, accepted_at, ip_address)`
- `sport_kursach/sportrent/users/forms.py` — в `UserRegistrationForm` добавить поле `passport_nda_accepted` (отдельно от существующего `agreement_accepted` для владельцев 70/30)
- `sport_kursach/sportrent/users/views.py` — в `register` сохранять `PassportNDA` при создании клиента
- `sport_kursach/sportrent/templates/users/register.html` — добавить чекбокс с раскрывающимся текстом соглашения
- `sport_kursach/sportrent/users/templates/users/passport_nda.txt` или `.html` — сам текст соглашения (152-ФЗ)
- Миграция

**Текст соглашения** должен включать:
- Согласие на обработку персональных данных по 152-ФЗ
- Цель обработки (исполнение договора аренды)
- Срок хранения
- Право отзыва согласия
- Версия документа (v1.0) и дата

**Проверка:** регистрация без галочки → ошибка валидации. С галочкой → создаётся запись в `PassportNDA`.

**Коммит:** `feat(users): NDA agreement for passport data processing (152-FZ)`

### День 4 — Декораторы и Signals (паттерн Наблюдатель)

Файлы:
- `sport_kursach/sportrent/users/decorators.py` — `role_required(*roles)` (в ПЗ упоминается, в коде нет)
- Заменить `@user_passes_test(is_staff)` и ручные проверки `if request.user.role != 'owner'` на `@role_required('owner')`
- `sport_kursach/sportrent/reviews/signals.py` — `post_save` на `Review` пересчитывает рейтинги инвентаря и пользователя
- `sport_kursach/sportrent/reviews/apps.py` — `ready()` подключает signals
- Убрать ручной пересчёт рейтингов из views

**Это даёт:**
- Чистый код (DRY)
- Явный паттерн «Наблюдатель» для защиты

**Коммит:** `refactor: role_required decorator + signals for rating updates`

### День 5 — Подключаем Postgres MCP

После того как БД работает через Docker:

```bash
claude mcp add --scope project --transport stdio postgres \
  -- npx -y @modelcontextprotocol/server-postgres \
  postgresql://sportrent:sportrent@localhost:5432/sportrent
```

(подставь свои креды из `.env`)

Теперь Claude может проверять данные напрямую: «покажи 5 последних инвентарей со статусом available».

**Проверка:** `claude mcp list` → 4 connected MCP.

### Чек-лист Недели 1

- [ ] `docker-compose up -d` поднимает все 5 сервисов без ошибок
- [ ] Каталог открывается на `http://localhost/`
- [ ] Чат работает через Redis channel layer (две вкладки получают сообщения)
- [ ] Логи приложения уходят в MongoDB
- [ ] Регистрация требует галочку NDA
- [ ] Модель `PassportNDA` создаётся при регистрации
- [ ] `@role_required` декоратор используется минимум в 5 views
- [ ] Signals пересчитывают рейтинги при создании отзыва
- [ ] Postgres MCP подключен
- [ ] Минимум 5 коммитов в ветке `diploma`

---

## 📌 Неделя 2 — Расширение на всю РФ

### День 1 — Модели города и точки выдачи

Файлы:
- `sport_kursach/sportrent/inventory/models.py` — добавить:
  ```
  class City(models.Model):
      city_id = UUIDField(pk)
      name = CharField(100)
      region = CharField(100)         # область/край/республика
      federal_district = CharField(50) # ЦФО, ПФО, СФО, ...
      latitude = DecimalField(9, 6)
      longitude = DecimalField(9, 6)
      timezone = CharField(50)
      
  class PickupPoint(models.Model):
      point_id = UUIDField(pk)
      city = ForeignKey(City)
      owner = ForeignKey(Owner, null=True)   # точка владельца
      manager = ForeignKey(Manager, null=True) # или точка магазина
      address = CharField(500)
      latitude = DecimalField(9, 6)
      longitude = DecimalField(9, 6)
      working_hours = JSONField()       # {mon: "9:00-18:00", ...}
      is_active = BooleanField(default=True)
  ```
- В `Inventory` добавить FK `pickup_point = ForeignKey(PickupPoint, on_delete=PROTECT)`
- Миграция (data migration: создать дефолтную точку «Альметьевск, главный офис» и привязать к ней весь существующий инвентарь, чтобы старые записи не сломались)

**Коммит:** `feat(inventory): add City and PickupPoint models for RF coverage`

### День 2 — Заполнение справочника городов

Файлы:
- `sport_kursach/sportrent/inventory/management/commands/populate_cities.py` — загружает топ-100 городов РФ из CSV или хардкодом
- CSV-файл `sport_kursach/sportrent/inventory/fixtures/cities_russia.csv` с колонками: `name, region, federal_district, latitude, longitude, timezone`

**Источник данных:** список крупнейших городов РФ с координатами есть на Wikipedia / в открытых датасетах. Можно попросить Claude сгенерировать топ-50 с координатами центра города.

**Проверка:** `python manage.py populate_cities` → в БД появилось 50-100 городов.

**Коммит:** `feat(inventory): seed top-100 Russian cities with coordinates`

### День 3 — Обновление UI инвентаря под точку выдачи

Файлы:
- `sport_kursach/sportrent/inventory/forms.py` — `InventoryForm` обновить, чтобы владелец выбирал точку выдачи из своих
- Добавить форму `PickupPointForm` для создания/редактирования точек
- `sport_kursach/sportrent/inventory/views.py` — CRUD для точек владельца
- `sport_kursach/sportrent/inventory/urls.py` — маршруты `pickup-points/`
- `sport_kursach/sportrent/templates/inventory/pickup_point_form.html`
- `sport_kursach/sportrent/templates/inventory/pickup_points_list.html`

**Логика:** перед добавлением инвентаря владелец должен создать хотя бы одну точку выдачи. Без точек кнопка «Добавить инвентарь» неактивна с подсказкой.

**Коммит:** `feat(inventory): pickup points CRUD for owners`

### День 4 — Фильтр каталога по городу

Файлы:
- `sport_kursach/sportrent/inventory/views.py` — `inventory_list` принимает GET-параметр `city` и `radius_km`
- `sport_kursach/sportrent/inventory/forms.py` — `InventoryFilterForm` с полем «город»
- `sport_kursach/sportrent/templates/inventory/inventory_list.html` — селектор города с поиском (datalist)

**SQL для фильтра по радиусу:** формула Haversine через `RawSQL` или функция `earthdistance` Postgres (включена в `cube` extension). Для MVP — простой фильтр по `city_id`.

**Коммит:** `feat(inventory): filter catalog by city`

### День 5 — Обновить populate_db

Файл:
- `sport_kursach/sportrent/core/management/commands/populate_db.py` — обновить:
  - Создавать инвентарь в 5-10 разных городах
  - У каждого владельца 1-3 точки выдачи в разных городах
  - Аренды между клиентами и точками в разных городах

**Цель:** на защите видно, что система работает не только в Альметьевске.

**Коммит:** `chore: enrich populate_db with multi-city data`

### Чек-лист Недели 2

- [ ] Модель `City` со справочником 50+ городов
- [ ] Модель `PickupPoint` для точек выдачи
- [ ] У `Inventory` обязательная связь с `PickupPoint`
- [ ] Существующие записи перенесены через data migration
- [ ] Владелец может создавать/редактировать свои точки выдачи
- [ ] Каталог фильтруется по городу
- [ ] `populate_db` создаёт данные в 5+ городах
- [ ] 5+ коммитов

---

## 📌 Неделя 3 — REST API на DRF

### День 1 — Установка и настройка DRF

Файлы:
- `requirements.txt` — добавить `djangorestframework`, `djangorestframework-simplejwt`, `django-cors-headers`, `drf-spectacular` (Swagger)
- `sport_kursach/sportrent/config/settings.py` — `INSTALLED_APPS`, `REST_FRAMEWORK`, `SIMPLE_JWT`, `CORS_ALLOWED_ORIGINS`
- `sport_kursach/sportrent/config/urls.py` — подключить `api/v1/` + Swagger UI

Настроить JWT в **httpOnly cookie**, не в Authorization header:
- Кастомный middleware или view, который при логине ставит cookie `access_token` с `HttpOnly=True, Secure=False (dev), SameSite=Lax`
- Кастомный authentication class который читает токен из cookie

**Коммит:** `feat(api): install DRF, SimpleJWT in httpOnly cookies, CORS, drf-spectacular`

### День 2 — Сериализаторы и эндпоинты пользователей

Файлы:
- `sport_kursach/sportrent/users/serializers.py` — `UserSerializer`, `ClientSerializer`, `OwnerSerializer`, `RegisterSerializer`, `LoginSerializer`
- `sport_kursach/sportrent/users/api_views.py` — `RegisterView`, `LoginView` (ставит cookie), `LogoutView` (стирает cookie), `MeView` (текущий пользователь)
- `sport_kursach/sportrent/users/api_urls.py` — маршруты `/api/v1/auth/`

**Коммит:** `feat(api): auth endpoints (register, login, logout, me) with JWT cookies`

### День 3 — API инвентаря и каталога

Файлы:
- `sport_kursach/sportrent/inventory/serializers.py` — `InventorySerializer`, `InventoryListSerializer` (lite), `CitySerializer`, `PickupPointSerializer`, `SportCategorySerializer`, `FavoriteSerializer`
- `sport_kursach/sportrent/inventory/api_views.py` — `InventoryViewSet` (list/retrieve/create/update/delete), `CityViewSet` (read-only), `PickupPointViewSet`, `CategoryViewSet` (read-only)
- Permissions: `IsOwnerOrReadOnly`, `IsManagerOrAdmin`
- Filters: `django-filter` для query-параметров (city, category, price_min/max, condition)
- Пагинация (стандартная DRF на 12-20 items)

**Коммит:** `feat(api): inventory, cities, pickup-points endpoints`

### День 4 — API аренд и отзывов

Файлы:
- `sport_kursach/sportrent/rentals/serializers.py` + `api_views.py` — `RentalSerializer`, `RentalViewSet`, action для confirm/reject/complete
- `sport_kursach/sportrent/reviews/serializers.py` + `api_views.py` — `ReviewSerializer`, `ReviewViewSet`

**Коммит:** `feat(api): rentals and reviews endpoints`

### День 5 — API чата и админ-эндпоинты

Файлы:
- `sport_kursach/sportrent/chat/serializers.py` + `api_views.py` — список чатов, история сообщений (WebSocket остаётся для real-time)
- `sport_kursach/sportrent/custom_admin/api_views.py` — статистика, экспорт XLSX/PDF, модерация

**Проверка через Swagger:** открыть `http://localhost/api/schema/swagger-ui/`, проверить что все эндпоинты задокументированы и работают через UI.

**Коммит:** `feat(api): chat and admin endpoints + Swagger UI`

### Чек-лист Недели 3

- [ ] DRF + SimpleJWT настроены, JWT в httpOnly cookie
- [ ] CORS разрешён только для домена фронта (`http://localhost:3000`)
- [ ] Все ключевые модели имеют CRUD-эндпоинты
- [ ] Swagger UI работает на `/api/schema/swagger-ui/`
- [ ] Permissions проверяют роли
- [ ] Старые Django views продолжают работать (не сломаны)
- [ ] 5+ коммитов

---

## 📌 Неделя 4 — React фронт (каркас + основные страницы)

### День 1 — Создание React-проекта

В корне репо рядом с `sportrent/`:
```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npm install react-router-dom @tanstack/react-query axios
npm install -D @types/react-router-dom
```

Файлы:
- `frontend/vite.config.ts` — настроить proxy `/api/*` на `http://localhost/api/*`
- `frontend/tailwind.config.js` — content paths
- `frontend/src/index.css` — Tailwind directives
- `frontend/src/api/client.ts` — axios instance с `withCredentials: true` (для cookies)
- `frontend/src/api/auth.ts`, `frontend/src/api/inventory.ts` — API-клиенты
- `frontend/src/App.tsx` — React Router с базовыми маршрутами
- `Dockerfile.frontend` + сервис `frontend` в `docker-compose.yml`

**Коммит:** `feat(frontend): scaffold React + Vite + TS + Tailwind + Router`

### День 2 — Layout и аутентификация

Файлы:
- `frontend/src/components/Layout.tsx` — общий лейаут с навбаром и футером
- `frontend/src/components/Navbar.tsx`
- `frontend/src/pages/LoginPage.tsx`
- `frontend/src/pages/RegisterPage.tsx`
- `frontend/src/hooks/useAuth.ts` — TanStack Query hooks для логина/регистрации/me
- `frontend/src/contexts/AuthContext.tsx`

**Коммит:** `feat(frontend): layout, navbar, login/register pages`

### День 3 — Каталог инвентаря

Файлы:
- `frontend/src/pages/CatalogPage.tsx` — список + фильтры
- `frontend/src/components/InventoryCard.tsx`
- `frontend/src/components/CatalogFilters.tsx` — категория, цена, состояние, город
- `frontend/src/hooks/useInventory.ts`
- Пагинация (TanStack Query infinite query или классические страницы)

**Коммит:** `feat(frontend): catalog page with filters and pagination`

### День 4 — Детали инвентаря + форма аренды

Файлы:
- `frontend/src/pages/InventoryDetailPage.tsx` — фото, описание, рейтинг, отзывы, форма аренды
- `frontend/src/components/PhotoGallery.tsx`
- `frontend/src/components/ReviewList.tsx`
- `frontend/src/components/RentalForm.tsx` — выбор дат + расчёт стоимости
- `frontend/src/pages/RentalsListPage.tsx` — мои аренды

**Коммит:** `feat(frontend): inventory details, rental form, my rentals`

### День 5 — Профиль и чат

Файлы:
- `frontend/src/pages/ProfilePage.tsx` — данные пользователя, редактирование
- `frontend/src/pages/ChatListPage.tsx` — список чатов
- `frontend/src/pages/ChatDetailPage.tsx` — WebSocket-чат через нативный `WebSocket` API
- `frontend/src/hooks/useWebSocket.ts`

**Коммит:** `feat(frontend): profile and websocket chat`

### Чек-лист Недели 4

- [ ] React проект работает, открывается на `http://localhost:3000`
- [ ] Логин/регистрация работают, JWT в cookie ставится
- [ ] После перезагрузки страницы пользователь остаётся залогинен
- [ ] Каталог отображает инвентарь, фильтры работают, пагинация работает
- [ ] Можно открыть детали инвентаря, оформить аренду
- [ ] Чат через WebSocket работает в обе стороны
- [ ] Frontend в Docker
- [ ] 5+ коммитов

---

## 📌 Неделя 5 — AI-геопоиск (главная фишка диплома)

### День 1 — Установка LangChain + OpenAI

Файлы:
- `requirements.txt` — добавить `langchain`, `langchain-openai`, `tiktoken`, `pgvector`
- `.env.example` — добавить `OPENAI_API_KEY=`
- `sport_kursach/sportrent/ai/__init__.py` (новое приложение)
- `sport_kursach/sportrent/ai/apps.py`
- `sport_kursach/sportrent/config/settings.py` — добавить в `INSTALLED_APPS`

**Получи OpenAI API key:** https://platform.openai.com/api-keys — положи $5 на счёт. На геопоиск хватит надолго (gpt-4o-mini ~$0.15 за 1M входных токенов).

**Альтернатива:** YandexGPT API (бесплатный лимит) или GigaChat (Сбер, бесплатный лимит). Под РФ-фокус смотрится лучше, но интеграция чуть сложнее. Рекомендую начать с OpenAI, если хватит времени — переключить на YandexGPT.

**Коммит:** `chore(ai): install langchain and openai SDK`

### День 2 — Парсер запросов (LLM)

Файлы:
- `sport_kursach/sportrent/ai/services/query_parser.py`:
  ```
  class SearchQueryParser:
      """Парсит естественно-языковой запрос в структурированный фильтр."""
      
      def parse(self, query: str) -> SearchFilters:
          """
          Вход: "недорогие беговые лыжи в Казани на завтра"
          Выход: SearchFilters(
              category="беговые лыжи",
              price_max=2000,  # "недорогие" → эвристика
              city="Казань",
              date_from=tomorrow,
              date_to=tomorrow + 1day,
          )
          """
  ```
- Использовать LangChain с function calling / structured output (Pydantic-схема `SearchFilters`)
- Промпт на русском с примерами few-shot
- Тесты: 10-15 примеров с ожидаемым результатом

**Коммит:** `feat(ai): natural language search query parser via LLM`

### День 3 — Геокодирование + Yandex API

Файлы:
- `.env.example` — `YANDEX_GEOCODER_KEY=`, `YANDEX_MAPS_API_KEY=`
- `sport_kursach/sportrent/ai/services/geocoder.py` — обёртка над Yandex Geocoder API + Redis-кэш на 24ч (одинаковые запросы не дёргают API)
- `sport_kursach/sportrent/ai/services/search.py` — финальный сервис:
  ```
  def smart_search(query: str) -> SearchResult:
      filters = parser.parse(query)
      city_coords = geocoder.get_coords(filters.city)
      results = (
          Inventory.objects
          .filter(status='available')
          .filter(pickup_point__city__name=filters.city)
          .filter(category__name__icontains=filters.category)
          .filter(price_per_day__lte=filters.price_max or 999999)
      )
      return SearchResult(items=results, center=city_coords)
  ```
- API endpoint `POST /api/v1/ai/search` принимает `{"query": "..."}`, возвращает JSON

**Получи Yandex API keys:** https://developer.tech.yandex.ru/services/ — бесплатно 1000 геокодинг-запросов/день и Maps JS API без жёстких лимитов.

**Коммит:** `feat(ai): geocoding service with Yandex API + smart search endpoint`

### День 4 — Embeddings + pgvector

Файлы:
- Миграция: установить расширение pgvector в БД, добавить колонку `description_embedding vector(1536)` в `Inventory`
- `sport_kursach/sportrent/ai/services/embeddings.py` — генерация эмбеддинга через OpenAI `text-embedding-3-small`
- `sport_kursach/sportrent/ai/management/commands/embed_inventory.py` — пересчёт эмбеддингов для всего инвентаря
- Signal `post_save` на `Inventory` — при создании/изменении description пересчитать эмбеддинг
- В `smart_search` добавить опциональную semantic search: если LLM не уверен в категории, ищем по cosine similarity между запросом и описаниями

**Коммит:** `feat(ai): pgvector embeddings for semantic search`

### День 5 — Карта на фронте + UI поиска

Файлы:
- `frontend/index.html` — подключить Yandex Maps API скрипт
- `frontend/src/components/MapView.tsx` — React-обёртка над Yandex Maps, отображает метки по координатам
- `frontend/src/components/SmartSearchBar.tsx` — большое поле «спроси про инвентарь...» + кнопка
- `frontend/src/pages/SmartSearchPage.tsx` — отдельная страница AI-поиска с картой и списком
- `frontend/src/api/aiSearch.ts` — клиент к `/api/v1/ai/search`
- На главной странице сделать smart search-bar главным элементом

**Проверка:** ввести «беговые лыжи в Казани» → карта центрируется на Казани, метки показывают точки выдачи, список снизу.

**Коммит:** `feat(frontend): AI search page with Yandex map`

### Чек-лист Недели 5

- [ ] LLM парсит запросы на естественном языке в структурированный фильтр
- [ ] Yandex Geocoder возвращает координаты по названию города
- [ ] Endpoint `POST /api/v1/ai/search` работает
- [ ] pgvector включён, эмбеддинги создаются автоматически
- [ ] Semantic search работает (поиск «лыжи для горки» находит «горные лыжи»)
- [ ] На фронте есть умная поисковая строка
- [ ] Yandex Map с метками отображается
- [ ] 5+ коммитов

---

## 📌 Неделя 6 — Полировка, тесты, демо

### День 1 — Дополнительная AI-функция (на выбор)

Что-то одно из:

**Вариант A:** AI-помощник для описания инвентаря.
- На странице создания инвентаря кнопка «Сгенерировать описание»
- Владелец вводит только название и категорию, остальное генерирует LLM

**Вариант B:** AI-модерация отзывов.
- При создании отзыва — асинхронная проверка через LLM на спам/мат/токсичность
- Если детектится — статус `pending` остаётся, идёт на ручную модерацию

**Вариант C:** Рекомендательная система.
- На странице каталога блок «Рекомендуем вам»
- Берём историю аренд клиента → embedding → ищем похожий инвентарь через pgvector

Рекомендую **Вариант A** — он самый «вау» на защите и проще всего реализуется.

**Коммит:** `feat(ai): description generator for inventory`

### День 2 — Тесты

Покрыть тестами:
- `sport_kursach/sportrent/ai/tests/test_query_parser.py` — мокать OpenAI, проверить разбор 10 запросов
- `sport_kursach/sportrent/ai/tests/test_geocoder.py` — мокать Yandex API, проверить кэш
- `sport_kursach/sportrent/inventory/tests.py` — расширение под city/pickup_point
- `sport_kursach/sportrent/users/tests.py` — расширение под NDA

**Цель:** `python manage.py test` → 20+ тестов, все зелёные.

**Коммит:** `test: cover AI search, NDA, multi-city scenarios`

### День 3 — Демо-данные и обновление populate_db

Финальная версия `populate_db`:
- 50+ городов из справочника
- 20+ владельцев в разных городах
- 30+ точек выдачи
- 100+ инвентарь в 10+ городах с эмбеддингами
- 50+ клиентов из разных городов
- 30+ аренд в разных статусах
- 20+ отзывов
- Несколько чатов

**Цель:** запуск `docker-compose up && docker-compose exec web python manage.py populate_db` — и приложение наполнено реалистичными данными для защиты.

**Коммит:** `chore: comprehensive populate_db with multi-city realistic data`

### День 4 — Финальная проверка функционала

Прогон сценариев:
1. Регистрация клиента с NDA → паспорт сохранён, NDA в БД
2. Регистрация владельца → банковские реквизиты сохранены
3. Владелец создаёт точку выдачи в Казани → добавляет инвентарь → менеджер модерирует → подписывает договор → публикует
4. Клиент ищет «лыжи в Казани» через AI-поиск → видит метки на карте → открывает карточку → оформляет аренду
5. Менеджер подтверждает аренду → клиент оплачивает → переписка в чате
6. После завершения — клиент оставляет отзыв → рейтинг пересчитался (Signals)
7. Админ экспортирует статистику в XLSX/PDF
8. Скачивание договора .docx с заполненными данными

Все сценарии должны работать end-to-end.

**Коммит:** `fix: end-to-end scenario fixes from QA`

### День 5 — README, актуализация документации

Файлы:
- `README.md` — описание проекта, технологий, как запустить (docker-compose), скриншоты
- Обновить `RUN.md`
- Опционально — обновить пояснительную записку (если требуется новая для диплома)

**Коммит:** `docs: comprehensive README with screenshots and run instructions`

### Чек-лист Недели 6

- [ ] Дополнительная AI-фича реализована
- [ ] 20+ тестов проходят
- [ ] `populate_db` создаёт реалистичные данные на 10+ городов
- [ ] Все 8 сценариев работают end-to-end
- [ ] README и RUN.md актуальны
- [ ] Минимум 30+ коммитов в ветке `diploma` за всё время
- [ ] Проект запускается одной командой `docker-compose up`

---

## 📌 Неделя 7 — Буфер

Что обычно сюда уходит:
- Доделки фронта (стили, мелкие баги)
- Презентация для защиты (PowerPoint/PDF)
- Обновление пояснительной записки (если требуется)
- Репетиция защиты
- Светлая цветовая схема (если есть время и желание)

---

## 📝 Что говорить на защите

### Технологии и почему
- **Django** — быстрая разработка, ORM, готовая аутентификация, ролевой доступ из коробки
- **DRF** — стандарт де-факто для REST API в Django, готовые сериализаторы и permissions
- **React + TypeScript** — SPA, типобезопасность, переиспользуемые компоненты
- **PostgreSQL + pgvector** — реляционные данные + векторный поиск в одной БД
- **MongoDB** — для логов и чатов, оптимизировано под write-heavy и schemaless
- **Redis** — channel layer для WebSocket, кэш геокодинга
- **Docker** — изоляция окружений, простой запуск, готовность к деплою
- **LangChain + OpenAI** — production-ready инструменты для AI

### Паттерны проектирования
- **Наблюдатель** через Django Signals: `post_save` на `Review` пересчитывает рейтинги
- (Опционально упомянуть **Стратегию** если будет реализована для расчёта рейтинга)

### Защита от уязвимостей
- **SQL-инъекции** — Django ORM с параметризованными запросами, никаких raw SQL
- **XSS** — auto-escape в шаблонах, не используем `|safe`
- **CSRF** — `{% csrf_token %}` в формах, CSRF middleware
- **JWT** — в httpOnly cookie с Secure и SameSite, не в localStorage

### Асинхронность
- WebSocket через Django Channels (AsyncWebsocketConsumer)
- `database_sync_to_async` для работы с ORM из async-кода

### AI
- LLM (gpt-4o-mini) для понимания запросов на естественном языке
- Embeddings (text-embedding-3-small) для семантического поиска через pgvector
- Yandex Geocoder для перевода названий городов в координаты
- Цепочка: запрос → парсинг → геокодинг → SQL-фильтр + cosine similarity → результат на карте

---

## 🔥 Анти-стресс лайфхаки

1. **Закомитил рабочую версию** = ничего не страшно. Любую правку откатишь.
2. **Сломал что-то локально** = `git stash` или `git checkout -- <file>`. Не паникуй.
3. **БД испортилась** = `docker-compose down -v && docker-compose up -d && manage.py migrate && manage.py populate_db`. Полный рестарт за минуту.
4. **Claude Code тупит на сложной задаче** = подключи sequential-thinking MCP, попроси «использовать sequential-thinking для разбивки задачи».
5. **Сроки горят** = пропусти Неделю 6 (Опциональная AI-фича), готовь демо на том что есть.

Удачи 🚀
