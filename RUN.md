# Как запустить SportRent с нуля (Windows + PostgreSQL)

Проект использует **PostgreSQL**, не SQLite. Ниже порядок действий от нуля.

### Автоматизация (venv, pip, migrate, сервер)

После установки PostgreSQL и создания БД (шаги 1–3) можно запускать скрипты из **корня репозитория**:

**Windows (PowerShell):**

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned   # один раз, если скрипты запрещены
.\scripts\run-dev.ps1
```

С тестовыми данными (первый раз): `.\scripts\run-dev.ps1 -Seed`  
Только подготовка без сервера: `.\scripts\run-dev.ps1 -NoServer`

**Linux / macOS:**

```bash
chmod +x scripts/run-dev.sh
./scripts/run-dev.sh
```

С тестовыми данными: `./scripts/run-dev.sh --seed`  
Без сервера: `./scripts/run-dev.sh --no-server`

Скрипты не устанавливают сам PostgreSQL — только Python-зависимости и Django-команды.

---

## 1. Установить PostgreSQL

1. Откройте сайт: https://www.postgresql.org/download/windows/
2. Скачайте установщик (кнопка **Download the installer** с EDB).
3. Запустите установщик:
   - Запомните **порт** (по умолчанию **5432**).
   - Задайте пароль для пользователя **`postgres`** (суперпользователь) — он понадобится в `.env`, если будете подключаться как `postgres`.
4. Дождитесь конца установки. Служба **postgresql-x64-…** должна быть запущена (Панель управления → Службы).

Если не хотите создавать отдельного пользователя `sportrent`, можно подключаться под **`postgres`** (см. шаг 2 и `.env`).

---

## 2. Создать базу данных

Вариант **A — через «SQL Shell (psql)»** (ставится вместе с PostgreSQL, в меню Пуск):

1. Запустите **SQL Shell (psql)**.
2. Жмите Enter на всех вопросах (хост, порт, пользователь `postgres`), введите пароль от `postgres`.
3. Выполните по очереди:

```sql
CREATE DATABASE sportrent;
```

Если нужен отдельный пользователь (как в `.env.example`):

```sql
CREATE USER sportrent WITH PASSWORD 'sportrent';
CREATE DATABASE sportrent OWNER sportrent;
GRANT ALL PRIVILEGES ON DATABASE sportrent TO sportrent;
```

Вариант **B — через pgAdmin** (тоже в составе установщика): создайте базу с именем `sportrent`.

---

## 3. Файл `.env` (обязательно, кодировка UTF-8)

1. Скопируйте **`sport_kursach/.env.example`** в **`sport_kursach/sportrent/.env`**  
   (рядом с `manage.py` — так надёжнее всего).

2. Откройте `.env` в редакторе и сохраните как **UTF-8** (в VS Code / Cursor: внизу справа кодировка → **UTF-8**).

3. Подставьте свои данные:

**Если подключаетесь как `postgres`:**

```env
SECRET_KEY=любая-длинная-случайная-строка-для-разработки
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=sportrent
DB_USER=postgres
DB_PASSWORD=ВАШ_ПАРОЛЬ_ОТ_POSTGRES
DB_HOST=127.0.0.1
DB_PORT=5432
```

**Если создали пользователя `sportrent` (как в примере):**

```env
DB_NAME=sportrent
DB_USER=sportrent
DB_PASSWORD=sportrent
DB_HOST=127.0.0.1
DB_PORT=5432
```

---

## 4. Python: виртуальное окружение и пакеты

В PowerShell из **корня репозитория** (`sport_kursach`):

```powershell
cd C:\Users\ВАШ_ПУТЬ\Desktop\sport_kursach
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Дополнительно (договоры Word и т.п., если нужно):

```powershell
pip install python-docx
```

---

## 5. Папка логов и миграции

```powershell
cd .\sportrent\
if (-not (Test-Path logs)) { New-Item -ItemType Directory -Path logs }
python manage.py migrate
```

Одной командой **`migrate`** достаточно — не нужно отдельно `migrate rentals` / `inventory`.

### Если `migrate` выдаёт ошибку

| Симптом | Что проверить |
|--------|----------------|
| `could not connect` / `Connection refused` | Запущена ли служба PostgreSQL, верные ли `DB_HOST` и `DB_PORT`. |
| `password authentication failed` | Пароль и `DB_USER` в `.env`. |
| `database "sportrent" does not exist` | Создайте БД (шаг 2). |
| `UnicodeDecodeError` при подключении | Файл `.env` сохранить в **UTF-8**, без «странных» символов в пароле или переписать пароль латиницей/цифрами. |

---

## 6. Тестовые данные (по желанию)

```powershell
python manage.py populate_db
```

---

## 7. Запуск сервера

Из каталога **`sportrent`** (с активированным `venv`):

```powershell
python manage.py runserver
```

Сайт: http://127.0.0.1:8000/

С WebSocket (Channels):

```powershell
daphne -b 127.0.0.1 -p 8000 config.asgi:application
```

---

## Краткий чеклист

1. PostgreSQL установлен, служба работает.  
2. База **`sportrent`** создана.  
3. Файл **`sportrent/.env`** есть, **UTF-8**, верные `DB_*`.  
4. `venv` → `pip install -r requirements.txt`.  
5. `cd sportrent` → `python manage.py migrate` → при необходимости `populate_db` → `runserver`.


cd путь\к\sport_kursach
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd sportrent
mkdir logs -ErrorAction SilentlyContinue
python manage.py migrate
python manage.py populate_db
python manage.py runserver



Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
.\scripts\run-dev.ps1

chmod +x scripts/run-dev.sh
./scripts/run-dev.sh
