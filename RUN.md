# Запуск проекта СпортРент (с WebSocket для чатов)

Пошаговая инструкция для полного запуска проекта на **Windows** и **Linux**.  
Для работы чатов в реальном времени (без перезагрузки страницы) сервер нужно запускать через **Daphne**, а не через `runserver`.

---

## Общие требования

- Python 3.10 или выше
- Терминал (PowerShell / cmd на Windows; bash на Linux)

---

## Windows

### 1. Откройте терминал в папке проекта

Перейдите в папку, где лежит проект (например `Desktop\sport_kursach`):

```cmd
cd C:\Users\ВАШ_ПОЛЬЗОВАТЕЛЬ\Desktop\sport_kursach
```

### 2. Создайте виртуальное окружение (если ещё нет)

```cmd
python -m venv venv
```

### 3. Активируйте виртуальное окружение

**В cmd:**
```cmd
venv\Scripts\activate
```

**В PowerShell:**
```powershell
.\venv\Scripts\Activate.ps1
```

После активации в начале строки появится `(venv)`.

### 4. Установите зависимости

```cmd
pip install -r requirements.txt
```

### 5. Настройте переменные окружения

Скопируйте пример и при необходимости отредактируйте:

```cmd
copy .env.example .env
```

Файл `.env` можно оставить как есть для локальной разработки.

### 6. Примените миграции и создайте суперпользователя (если первый запуск)

```cmd
cd sportrent
python manage.py migrate
python manage.py createsuperuser
```

Команды выполняются из папки **sportrent** (где лежит `manage.py`).

### 7. Запуск сервера с поддержкой WebSocket

**Вариант А — через скрипт (из корня проекта `sport_kursach`):**

```cmd
cd ..
scripts\run_server_websocket.bat
```

**Вариант Б — вручную из папки sportrent:**

```cmd
cd sportrent
daphne -b 127.0.0.1 -p 8000 config.asgi:application
```

### 8. Откройте сайт

В браузере: **http://127.0.0.1:8000/**

Чаты и уведомления будут работать в реальном времени (WebSocket).

---

## Linux (и macOS)

### 1. Откройте терминал в папке проекта

```bash
cd /путь/к/sport_kursach
```

### 2. Создайте виртуальное окружение (если ещё нет)

```bash
python3 -m venv venv
```

### 3. Активируйте виртуальное окружение

```bash
source venv/bin/activate
```

В начале строки появится `(venv)`.

### 4. Установите зависимости

```bash
pip install -r requirements.txt
```

### 5. Настройте переменные окружения

```bash
cp .env.example .env
```

При необходимости отредактируйте `.env`.

### 6. Примените миграции и создайте суперпользователя (если первый запуск)

```bash
cd sportrent
python manage.py migrate
python manage.py createsuperuser
```

### 7. Запуск сервера с поддержкой WebSocket

**Вариант А — через скрипт (из корня проекта):**

```bash
chmod +x scripts/run_server_websocket.sh
./scripts/run_server_websocket.sh
```

**Вариант Б — вручную из папки sportrent:**

```bash
cd sportrent
daphne -b 127.0.0.1 -p 8000 config.asgi:application
```

### 8. Откройте сайт

В браузере: **http://127.0.0.1:8000/**

---

## Краткая шпаргалка (после первой настройки)

| Действие              | Windows                    | Linux / macOS                |
|-----------------------|----------------------------|------------------------------|
| Активация venv        | `venv\Scripts\activate`    | `source venv/bin/activate`   |
| Запуск с WebSocket    | `scripts\run_server_websocket.bat` | `./scripts/run_server_websocket.sh` |
| Или вручную (из sportrent) | `daphne -b 127.0.0.1 -p 8000 config.asgi:application` | то же самое |

---

## Важно про WebSocket

- **`python manage.py runserver`** — только HTTP, чаты не обновляются автоматически, по адресам `/ws/...` будет 404.
- **`daphne ... config.asgi:application`** — и HTTP, и WebSocket; чаты и уведомления работают в реальном времени.

Для разработки с чатами всегда запускайте проект через Daphne (скрипты выше или команду `daphne` из папки `sportrent`).
