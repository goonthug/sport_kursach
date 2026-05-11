# MCP_SETUP_GUIDE.md — Гайд по MCP-серверам для проекта

> Подробная справка по всем MCP-серверам, которые мы подключаем к Claude Code для работы над дипломом. Базовая установка есть в `WINDOWS_SETUP.md` — здесь детали и продвинутое использование.

---

## 🧠 Что такое MCP

**MCP (Model Context Protocol)** — это плагины-инструменты для Claude Code. Каждый MCP-сервер даёт Claude доступ к новому источнику данных или возможности.

Без MCP Claude работает только с тем, что видит в текущей сессии (твои сообщения + файлы которые открыл). С MCP он может:
- Читать актуальную документацию (context7) — не из своей тренировки
- Выполнять SQL-запросы напрямую в БД (postgres)
- Управлять PR/issues на GitHub (github)
- Думать пошагово над сложными задачами (sequential-thinking)
- И многое другое

MCP-серверы прописываются в `.mcp.json` в корне проекта. Каждый стартует как отдельный процесс через `npx` и общается с Claude через stdio.

---

## 📋 MCP, которые подключаем для проекта

| MCP | Когда подключаем | Зачем |
|-----|------------------|-------|
| **context7** | Сразу | Актуальная документация фреймворков |
| **sequential-thinking** | Сразу | Пошаговое мышление для сложных задач |
| **github** | Сразу | Управление репозиторием, PR, issues |
| **postgres** | Неделя 1, после Docker | Прямые SQL-запросы к БД |
| **filesystem** | Опционально | Расширенная работа с файлами (обычно встроено) |

---

## 🔧 MCP №1 — Context7

### Что делает

Достаёт свежую документацию из официальных источников: Django, DRF, React, Vite, Tailwind, LangChain, pgvector, OpenAI SDK, Yandex Maps — что угодно популярное.

Это критично потому что:
- Тренировочная база Claude может быть устаревшей (Django 5 уже многое поменял после 4.2)
- Многие библиотеки (LangChain, pgvector-python) активно развиваются
- В документации часто есть свежие best practices, которых в тренировке нет

### Установка

```bash
cd ~/Documents/diploma/sport_kursach
claude mcp add --scope project --transport stdio context7 -- npx -y @upstash/context7-mcp
```

### Как использовать в Claude Code

Просто проси в чате:
```
Use context7 to fetch the latest Django REST Framework SimpleJWT docs about httpOnly cookies authentication.
```

Или коротко:
```
context7: latest pgvector Django integration guide
```

Или ещё короче (Claude сам поймёт когда нужно):
```
Покажи актуальный пример настройки channels-redis для Channels 4.
```

### Когда обязательно использовать

- Перед первой работой с **новой библиотекой** (langchain, drf-spectacular, pgvector-python)
- Когда **версия Django/Python важна** и в коде используются конструкции свежее тренировки
- Когда сомневаешься в актуальности API какой-то функции

---

## 🧩 MCP №2 — Sequential Thinking

### Что делает

Заставляет Claude думать **шагами вслух** перед тем как давать ответ. Полезно для:
- Дизайна архитектуры (как структурировать новое приложение)
- Сложных миграций БД (data migration с переносом данных)
- Рефакторинга больших кусков кода
- Дебага непонятных багов

### Установка

```bash
cd ~/Documents/diploma/sport_kursach
claude mcp add --scope project --transport stdio sequential-thinking -- npx -y @modelcontextprotocol/server-sequential-thinking
```

### Как использовать

Просто упоминай:
```
Use sequential-thinking. Я хочу добавить модель PickupPoint и связать с Inventory.
Сейчас у инвентаря есть FK на Owner и Manager.
Какие шаги нужны чтобы не сломать существующие данные?
```

Claude разобьёт задачу на пронумерованные шаги, обоснует каждый, и только потом начнёт писать код. Это очень спасает на сложных задачах, где «просто написать» — почти гарантированно баг.

### Когда обязательно

- Любая data migration (с переносом существующих записей)
- Изменения которые затрагивают 5+ файлов
- Дизайн нового API endpoint с нетривиальной логикой
- Когда первая попытка решения провалилась — не повторять то же самое, а подумать пошагово

---

## 🐙 MCP №3 — GitHub

### Что делает

Управляет твоим репозиторием с GitHub изнутри Claude Code:
- Создаёт issues и PR
- Читает существующие issues
- Смотрит коммиты и diff'ы
- Управляет releases

Зачем для диплома: можно вести todo-list через GitHub Issues, видеть прогресс. Для защиты — красиво смотрится «Project board» с закрытыми задачами.

### Установка

1. Создай Personal Access Token на **https://github.com/settings/tokens**:
   - **Generate new token (classic)**
   - Note: `claude-code-mcp`
   - Expiration: **90 days**
   - Scopes: ✅ **repo** (полностью), ✅ **read:user**, ✅ **read:org**
   - **Generate token** → скопируй ключ (показывается ОДИН раз!)

2. Подключи:
```bash
cd ~/Documents/diploma/sport_kursach
claude mcp add --scope project --transport stdio github \
  -e GITHUB_PERSONAL_ACCESS_TOKEN=ghp_твой_токен_сюда \
  -- npx -y @modelcontextprotocol/server-github
```

3. **СРАЗУ** добавь `.mcp.json` в `.gitignore` (там твой токен):
```bash
echo ".mcp.json" >> .gitignore
git rm --cached .mcp.json 2>/dev/null || true
git add .gitignore
git commit -m "chore: exclude .mcp.json from git"
```

⚠️ Если успел запушить токен на GitHub — **немедленно** отзови его (https://github.com/settings/tokens) и сделай новый.

### Использование

```
github: создай issue "Добавить модель PickupPoint" с лейблом "feature/week-2"
```
```
github: покажи 5 последних коммитов в ветке diploma
```
```
github: создай PR с веткой diploma в master с описанием изменений
```

---

## 🐘 MCP №4 — Postgres

### Что делает

Прямой SQL-доступ к Postgres. Claude может:
- Делать `SELECT` запросы для проверки данных
- Видеть схему БД через INFORMATION_SCHEMA
- Подсказывать оптимизации запросов на основе реальной структуры

**НЕ может** (по умолчанию): делать `INSERT/UPDATE/DELETE/DROP` — это write protection MCP-сервера. Только чтение.

### Когда подключать

**После Дня 1 Недели 1**, когда поднимешь Postgres через Docker и сделаешь `migrate`.

### Установка

Сначала запусти Postgres:
```bash
cd ~/Documents/diploma/sport_kursach
docker-compose up -d db
docker-compose exec web python manage.py migrate
```

Подключи MCP (подставь свои креды из `.env`):
```bash
claude mcp add --scope project --transport stdio postgres \
  -- npx -y @modelcontextprotocol/server-postgres \
  postgresql://sportrent:sportrent@localhost:5432/sportrent
```

### Использование

```
postgres: сколько записей в таблице inventory со статусом 'available'?
```
```
postgres: покажи структуру таблицы users
```
```
postgres: найди всех клиентов без паспортных данных
```

Особенно полезно при debug:
```
У меня в каталоге не показывается некоторый инвентарь.
postgres: проверь, есть ли записи в inventory с pickup_point=NULL?
```

---

## 🤖 Опциональные MCP (по желанию)

### Filesystem MCP

Обычно встроен в Claude Code, но если нужно явно — для расширенной работы с файлами вне проекта.

```bash
claude mcp add --scope project --transport stdio filesystem \
  -- npx -y @modelcontextprotocol/server-filesystem ~/Documents/diploma
```

### Fetch MCP

Чтобы Claude мог скачивать страницы по URL (документация, статьи).

```bash
claude mcp add --scope project --transport stdio fetch \
  -- npx -y @modelcontextprotocol/server-fetch
```

### Brave Search MCP

Если нужен поиск в интернете через Claude Code (не путать с Anthropic web search в чате):

```bash
# Получи ключ на https://brave.com/search/api/
claude mcp add --scope project --transport stdio brave-search \
  -e BRAVE_API_KEY=твой_ключ \
  -- npx -y @modelcontextprotocol/server-brave-search
```

---

## 🛠 Управление MCP

### Список подключенных

```bash
claude mcp list
```

Покажет статус каждого: `✓ Connected` или `✗ Failed`.

### Удалить MCP

```bash
claude mcp remove context7
```

### Где лежит конфиг

В корне проекта: `.mcp.json`. Можно открыть в VS Code и поправить руками:
```bash
code .mcp.json
```

Структура:
```json
{
  "mcpServers": {
    "context7": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp"]
    },
    "github": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_..."
      }
    }
  }
}
```

### Scope: project vs user

В командах выше использован `--scope project` — MCP виден только в этом проекте, конфиг в `.mcp.json` в корне.

Альтернатива — `--scope user`: MCP виден во всех проектах, конфиг в `~/.claude.json`. Не используй для проектов с токенами в env-переменных — другие проекты получат к ним доступ.

Рекомендую **всегда `--scope project`** для всего что относится к диплому.

---

## ⚙️ Проверка работы MCP в Claude Code

Запусти Claude в проекте:
```bash
cd ~/Documents/diploma/sport_kursach
claude
```

Напиши:
```
Покажи список MCP инструментов которые тебе доступны.
```

Claude перечислит подключенные. Если какого-то нет — проверь `claude mcp list` в терминале.

Тестовый запрос для каждого:

**Context7:**
```
context7: latest Django 5.1 migration patterns
```

**Sequential thinking:**
```
use sequential-thinking: design a database schema for storing user activity logs
```

**GitHub:**
```
github: list issues in my repository
```

**Postgres:**
```
postgres: SELECT COUNT(*) FROM users;
```

---

## ⚠️ Troubleshooting

### `✗ Failed` в `claude mcp list`

Чаще всего — проблема с `npx`. Запусти MCP вручную чтобы увидеть ошибку:
```bash
npx -y @upstash/context7-mcp
```

Если пишет «package not found» — проверь интернет, кэш npm:
```bash
npm cache clean --force
```

### MCP подключен, но Claude его не использует

Иногда Claude не понимает что нужно вызвать инструмент. Скажи явно:
```
Use the context7 MCP tool to fetch ...
```

Или:
```
Call the github MCP tool with action create_issue.
```

### Postgres MCP не подключается

Проверь:
1. Контейнер запущен: `docker-compose ps`
2. Порт открыт наружу в `docker-compose.yml` (`ports: - "5432:5432"`)
3. Креды верные: `docker-compose exec db psql -U sportrent -d sportrent` должно зайти

### Токен GitHub попал в коммит

```bash
# отозвать токен в браузере на https://github.com/settings/tokens
# создать новый
# обновить .mcp.json локально
# НЕ комитить заново, удалить .mcp.json из истории:
git rm --cached .mcp.json
echo ".mcp.json" >> .gitignore
git commit -m "chore: gitignore .mcp.json"
git push --force-with-lease     # ОСТОРОЖНО, переписывает историю
```

### MCP-серверы кушают много памяти

Каждый MCP — отдельный Node-процесс (~50-100MB). 5 MCP = ~500MB RAM. Если комп слабенький — отключай неиспользуемые:
```bash
claude mcp remove brave-search
```

---

## 📚 Дополнительные ресурсы

- Официальный список MCP-серверов: **https://github.com/modelcontextprotocol/servers**
- Документация Claude Code: **https://docs.anthropic.com/claude-code**
- Создание своего MCP-сервера: **https://modelcontextprotocol.io/docs/concepts/servers**

---

## ✅ Чек-лист «MCP готовы»

После выполнения всего гайда:

- [ ] `claude mcp list` показывает 3 connected MCP (context7, sequential-thinking, github)
- [ ] Тестовый запрос через context7 возвращает свежую доку
- [ ] GitHub MCP может прочитать твой репозиторий
- [ ] `.mcp.json` в `.gitignore`
- [ ] (После Недели 1) postgres MCP подключен, может делать SELECT-запросы

Готово 💪
