pip install channels
pip install django pillow python-decouple psycopg2-binary django-crispy-forms crispy-bootstrap5 reportlab openpyxl matplotlib seaborn django-filter
pip install -r requirements.txt
cd .\sportrent\
mkdir -p logs
python manage.py makemigrations
python manage.py migrate rentals
python manage.py migrate
python -m venv venv
venv\Scripts\activate   или   .\venv\Scripts\Activate.ps1
python manage.py populate_db
daphne -b 127.0.0.1 -p 8000 config.asgi:application
python manage.py runserver
daphne -b 127.0.0.1 -p 8000 config.asgi:application
pip install python-docx