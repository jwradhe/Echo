FROM python:3.11-slim

WORKDIR /code

# Installera nödvändiga systempaket
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Kopiera requirements och installera Python-paket
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Exponera port
EXPOSE 5000

# Kör Flask-applikationen
CMD ["python", "-m", "app"]