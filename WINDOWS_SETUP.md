# 🪟 Установка Claude Code для проекта SportRent (Windows)

> Гайд для работы с **существующим** проектом `sport_kursach` через Claude Code в Git Bash. Если что-то уже стоит — пропускай шаг. Время на всё: ~1.5 часа.

---

## 🎯 Что в итоге будет установлено

К концу гайда у тебя на компе будет:

1. **Git for Windows** — программа для работы с Git + терминал «Git Bash»
2. **Node.js** — нужен чтобы запустить Claude Code и MCP-серверы
3. **Docker Desktop** — для PostgreSQL + Redis + MongoDB в контейнерах
4. **VS Code** — редактор кода
5. **Python 3.11+** — уже должен быть (проект на Django), проверим
6. **Claude Code** — главный инструмент в терминале
7. **3-5 MCP-серверов** для проекта

---

## 📥 Часть 1. Установка программ (45 минут)

### Шаг 1.1 — Git for Windows

Если уже стоит — пропусти.

1. Открой: **https://git-scm.com/download/win**
2. Скачается `Git-...-64-bit.exe` — запусти
3. На всех экранах **Next**, кроме **«Choosing the default editor»** — выбери **VS Code** (если есть) или оставь Vim
4. **Install** → **Finish**

**Проверка:** в меню Пуск найди «Git Bash» → запусти. В нём:
```bash
git --version
```
Должно показать `git version 2.40+`.

> 💡 Стрелка ↑ возвращает предыдущую команду. Tab дополняет имена.

---

### Шаг 1.2 — Node.js

1. Открой: **https://nodejs.org**
2. Жми зелёную кнопку **«LTS»**
3. Скачается `node-v...-x64.msi` — запусти
4. **Next** → **Next** → галочка **«Automatically install the necessary tools»** → **Install**
5. После установки появится доп. окно «Tools for Native Modules» — **жди пока само закроется** (10-15 минут).

**Проверка** в **новом** окне Git Bash:
```bash
node --version    # v20+
npm --version     # 10+
```

---

### Шаг 1.3 — Docker Desktop

> Самая капризная программа. Если сломается — будем чинить.

1. Открой: **https://www.docker.com/products/docker-desktop/**
2. Жми **«Download for Windows - AMD64»** (для Intel/AMD)
3. Запусти `Docker Desktop Installer.exe`
4. Галочка **«Use WSL 2 instead of Hyper-V»** — оставь → **OK**
5. После установки **обязательно перезагрузи комп**
6. Запусти Docker Desktop. Прими лицензию → «Use recommended settings» → «Continue without signing in» → опрос пропусти
7. Когда увидишь зелёный значок 🐳 в трее — готово

**Проверка:**
```bash
docker --version
docker run hello-world
```

❌ **Ошибка «WSL 2 installation is incomplete»** — PowerShell от админа:
```powershell
wsl --update
```
Перезапусти Docker Desktop.

❌ **Docker не стартует** — в BIOS проверь, включена ли виртуализация (Intel VT-x / AMD-V).

---

### Шаг 1.4 — VS Code

Если уже стоит — пропусти.

1. **https://code.visualstudio.com** → **Download for Windows**
2. Запусти инсталлер
3. **ВАЖНО** на «Select Additional Tasks»:
   - ✅ «Add to PATH»
   - ✅ «Open with Code» — оба пункта (файл + папка)
4. **Install** → **Finish**

Расширения которые стоит поставить (потом, из VS Code):
- Python (Microsoft) + Pylance
- Django (`batisteo.vscode-django`)
- Docker (Microsoft)
- ES7+ React/Redux snippets — когда дойдём до React

---

### Шаг 1.5 — Python (проверка)

Проект на Python 3.11+. Скорее всего уже установлен.

```bash
python --version
```

Если `Python 3.11.x` или выше — отлично. Если нет:
1. **https://www.python.org/downloads/** → Python 3.12
2. На первом экране **ОБЯЗАТЕЛЬНО** галочка **«Add python.exe to PATH»**
3. **Install Now**

---

## 📚 Часть 2. Терминал на минималках (5 минут)

В Git Bash домашняя папка — **`~`** (тильда). Минимум команд:

```bash
pwd                    # где я сейчас
ls                     # что в этой папке
cd <папка>             # перейти в папку
cd ..                  # на уровень выше
cd ~                   # домой
mkdir <папка>          # создать папку
explorer .             # открыть в проводнике
code .                 # открыть в VS Code
```

> 💡 **Tab** дополняет имена. Это спасёт нервы.

---

## 🤖 Часть 3. Установка Claude Code (10 минут)

### Шаг 3.1 — Установка

В Git Bash:
```bash
npm install -g @anthropic-ai/claude-code
```

Подождать 1-3 минуты. Когда появится строка с `$` — готово.

**Проверка:**
```bash
claude --version
```
Должна показать `1.x.x`.

❌ «command not found» — закрой Git Bash, открой заново. Не помогло — перезагрузи комп.

### Шаг 3.2 — Авторизация

```bash
claude
```

Откроется меню. Выбор:
- **Claude.ai account** — нужна подписка **Claude Pro ($20/мес)** или Max ($100). Откроется браузер.
- **Anthropic API key** — ключ с console.anthropic.com, платишь за токены.

**Что выбрать для диплома:** на 1.5-2 месяца активной работы хватает **Claude Pro ($20)** одной картой. Если упрёшься в лимиты — переходи на Max.

После авторизации:
```
✓ Logged in as ...
```
Enter → попадёшь в чат с Claude.

**Выход:** `/exit` или Ctrl+C дважды.

---

## 📂 Часть 4. Подключаем существующий проект (10 минут)

У тебя `sport_kursach` на рабочем столе. Перенесём его и подготовим к работе.

### Шаг 4.1 — Скопируй проект в рабочую папку

```bash
cd ~
mkdir -p Documents/diploma
cp -r "/c/Users/$USER/Desktop/sport_kursach" Documents/diploma/
cd Documents/diploma/sport_kursach
pwd
```

Должно показать `/c/Users/<имя>/Documents/diploma/sport_kursach`.

> ⚠️ Если имя пользователя с русскими буквами или в пути пробелы — оборачивай в двойные кавычки. Если знаешь точный путь — подставь его. Если возможно, лучше работать в `C:\Projects\diploma` — кириллица в путях иногда ломает Python/Node.

### Шаг 4.2 — Проверь git и создай ветку диплома

```bash
git status
git log --oneline | head -10
git checkout -b diploma
```

Теперь все изменения идут в ветку `diploma`, а `master` остаётся как «эталон курсача» для подстраховки.

### Шаг 4.3 — Создай GitHub репозиторий

1. **https://github.com/new**
2. Имя: `sportrent-diploma`
3. **Private** (можешь сделать публичным после защиты)
4. **БЕЗ** README, .gitignore, license — они у тебя уже есть
5. **Create repository**

Привяжи локальный репо к удалённому:
```bash
git remote add origin https://github.com/<твой-логин>/sportrent-diploma.git
git push -u origin master
git push -u origin diploma
```

При первом push GitHub попросит залогиниться через браузер — согласись.

---

## 🔌 Часть 5. Подключаем MCP-серверы (15 минут)

MCP — это плагины-инструменты для Claude Code. Подробности — в `MCP_SETUP_GUIDE.md`. Здесь — минимум для старта.

Находясь в `~/Documents/diploma/sport_kursach`:

### MCP №1 — Context7 (актуальная документация)

```bash
claude mcp add --scope project --transport stdio context7 -- npx -y @upstash/context7-mcp
```

Зачем: свежая документация Django, DRF, React, LangChain, Tailwind — не из тренировки модели, а самая последняя с официальных доков.

### MCP №2 — Sequential Thinking (структурированное мышление)

```bash
claude mcp add --scope project --transport stdio sequential-thinking -- npx -y @modelcontextprotocol/server-sequential-thinking
```

Зачем: при сложных задачах (рефакторинг, миграция БД, дизайн API) Claude думает пошагово и не теряет нить.

### MCP №3 — GitHub

Сначала **Personal Access Token**:
1. **https://github.com/settings/tokens** → **Generate new token (classic)**
2. Note: `claude-code-mcp`
3. Expiration: **90 days**
4. Scopes: **repo** (целиком), **read:user**, **read:org**
5. **Generate token** → **скопируй** (показывается один раз!)

Подключи MCP (вставь свой токен вместо `ghp_xxx`):
```bash
claude mcp add --scope project --transport stdio github -e GITHUB_PERSONAL_ACCESS_TOKEN=ghp_YOUR_TOKEN_HERE -- npx -y @modelcontextprotocol/server-github
```

⚠️ **Важно:** после установки появится `.mcp.json` с твоим токеном. **Добавь его в .gitignore СРАЗУ**:
```bash
echo ".mcp.json" >> .gitignore
echo ".env.mcp" >> .gitignore
```

Если успел запушить токен — отзови его на GitHub и сделай новый.

### MCP №4 — Postgres (добавим позже)

Подключим после поднятия БД в Docker (День 1 диплома). Команда есть в `MCP_SETUP_GUIDE.md`. Зачем: Claude сможет напрямую делать SQL-запросы для проверки данных.

### Проверь что MCP подключились

```bash
claude mcp list
```

Должно показать:
```
context7              ✓ Connected
sequential-thinking   ✓ Connected
github                ✓ Connected
```

---

## 📥 Часть 6. Положи файлы плана в проект (5 минут)

У тебя 4 файла плана (включая этот):

1. **`WINDOWS_SETUP.md`** — этот гайд
2. **`CLAUDE.md`** — правила проекта (читается Claude Code автоматически из корня проекта)
3. **`DIPLOMA_PLAN.md`** — главный план диплома
4. **`MCP_SETUP_GUIDE.md`** — детали по MCP

Открой папку:
```bash
cd ~/Documents/diploma/sport_kursach
explorer .
```

Скопируй туда все 4 файла. Структура:
```
~/Documents/diploma/sport_kursach/
├── .git/
├── .gitignore
├── .mcp.json                     ← в .gitignore
├── .env.mcp                      ← в .gitignore
├── CLAUDE.md                     ⭐ Claude Code читает автоматически
├── DIPLOMA_PLAN.md
├── MCP_SETUP_GUIDE.md
├── WINDOWS_SETUP.md              (этот файл)
├── RUN.md                        (был)
├── requirements.txt
├── scripts/
└── sportrent/
```

Закоммить:
```bash
git add CLAUDE.md DIPLOMA_PLAN.md MCP_SETUP_GUIDE.md WINDOWS_SETUP.md .gitignore
git status                        # проверь что .mcp.json и .env.mcp НЕ в списке
git commit -m "docs: add diploma plan and Claude Code setup"
git push
```

---

## ✅ Часть 7. Финальная проверка

```bash
cd ~/Documents/diploma/sport_kursach
claude
```

В чате напиши:
```
Прочитай CLAUDE.md и DIPLOMA_PLAN.md, затем подтверди:
1. Какой стек у проекта и что уже реализовано
2. Какая главная новая фича диплома
3. Что мы делаем в Неделе 1
4. Какие MCP инструменты тебе доступны
```

Claude должен:
- Прочитать оба файла через свои встроенные инструменты
- Рассказать про Django + Postgres + Channels + кастомный User + 4 роли
- Сказать что главное — **AI-геолокационный поиск и расширение на всю РФ**
- Перечислить задачи Недели 1 (Docker + NDA + базовая инфра)
- Упомянуть context7, sequential-thinking, github

Если всё это произошло — **готово** 🎉

---

## 🚀 Что дальше

```bash
cd ~/Documents/diploma/sport_kursach
claude
```

В чате:
```
Сегодня День 1 Недели 1 из DIPLOMA_PLAN.md.
Задача: настроить Docker Compose с PostgreSQL 16 + pgvector + Redis + MongoDB.

Сначала покажи ПЛАН ФАЙЛОВ, которые ты собираешься создать или изменить, БЕЗ КОДА. Я подтвержу — после этого реализуешь.
```

---

## ⚠️ Если что-то сломалось

### `npm: command not found`
Закрой Git Bash, открой заново. Не помогло — перезагрузи комп.

### `claude: command not found`
```bash
npm install -g @anthropic-ai/claude-code
```
Перезапусти Git Bash.

### `claude` пишет «authentication failed»
Без подписки Claude Pro/Max через Claude.ai не работает. Альтернатива: API key с **https://console.anthropic.com**, положи $5-10.

### Docker Desktop не запускается
```powershell
wsl --update   # PowerShell от админа
```
Перезагрузи комп. Если всё ещё нет — включи виртуализацию в BIOS.

### `claude mcp add` ошибка про «transport»
Старая версия:
```bash
npm install -g @anthropic-ai/claude-code@latest
```

### `npx` долго запускает MCP (минуту+)
Это первый раз, потом быстрее. Чтобы ускорить — глобально:
```bash
npm install -g @upstash/context7-mcp @modelcontextprotocol/server-sequential-thinking @modelcontextprotocol/server-github
```

### Кириллица в путях ломает что-то
Лучшее решение — переехать в `C:\Projects\diploma\sport_kursach`:
```bash
mkdir -p /c/Projects/diploma
cp -r ~/Documents/diploma/sport_kursach /c/Projects/diploma/
cd /c/Projects/diploma/sport_kursach
```

### MCP не подключается («✗ Failed»)
Запусти руками чтобы увидеть ошибку:
```bash
npx -y @upstash/context7-mcp
```

---

## 🎓 Чек-лист «всё готово»

- [ ] `git --version` работает
- [ ] `node --version` показывает v20+
- [ ] `docker --version` работает, `docker run hello-world` успешно
- [ ] `code .` открывает VS Code
- [ ] `python --version` показывает 3.11+
- [ ] `claude --version` работает
- [ ] `claude` запускается, авторизация прошла
- [ ] Проект скопирован в `~/Documents/diploma/sport_kursach`
- [ ] Создана ветка `diploma`, запушена на GitHub
- [ ] `claude mcp list` показывает 3 connected MCP
- [ ] 4 файла плана лежат в папке
- [ ] `.mcp.json` и `.env.mcp` в `.gitignore`

Готово — переходи к `DIPLOMA_PLAN.md`, День 1 Недели 1 💪
