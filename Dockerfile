FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY sportrent/ ./sportrent/

RUN mkdir -p /app/sportrent/logs \
             /app/sportrent/staticfiles \
             /app/sportrent/media

COPY entrypoint.sh .
RUN chmod +x /app/entrypoint.sh

WORKDIR /app/sportrent

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
