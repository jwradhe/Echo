
## 🚀 Kom igång lokalt

```bash
# 1. Klona repot
git clone <repo-url>
cd echo

# 2. Skapa och aktivera virtuell miljö
python3 -m venv venv
source venv/bin/activate

# 3. Installera beroenden
pip install -r requirements-dev.txt
npm install
python -m playwright install

# 4. Konfigurera miljövariabler
cp .env.example .env
# Redigera .env med dina MySQL-uppgifter

# 5. Skapa MySQL-databas
mysql -u root -p < schema.sql

# 6. Starta applikationen
python3 -m app

# Öppna i webbläsaren:
http://127.0.0.1:5001
```

## 🗄️ Databas

Projektet använder MySQL 8.0+ med raw SQL queries.

**Konfiguration:**
- Development: `.env` (lokal MySQL)
- Production: `.env.production` (managed database)

**Schema:** 16 tabeller definierade i `schema.sql`

## 🔎 Kodkvalitet (Lint)

Projektet använder linting för att säkerställa konsekvent kodstil och upptäcka vanliga fel.

```bash
# Python
npm run lint:py

# JavaScript / TypeScript
npm run lint:js

# Linting på allt
npm run lint
```

## 🧪 Tester

```bash
# Unit- och integrationstester (Python):
pytest

# API-tester (Postman / Newman)
npm run api-test

# End-to-End tester (Playwright)
npm run e2e

### Köra alla tester:
npm run test:all

```

## 🐳 Docker

**Docker-compose**
```bash
# Starta med Docker Compose (rekommenderat)
docker-compose up -d

# Stoppa
docker-compose down

# Stoppa och rensa data
docker-compose down -v
```

**Alternativ: Docker Run**
```bash
chmod +x start.sh stop.sh
./start.sh  # Starta
./stop.sh   # Stoppa
```

**Loggar och debugging**
```bash
docker-compose logs -f        # Alla loggar
docker logs -f echo_web       # Endast web
docker exec -it echo_db mysql -u root -pchangemeCHANGEME123
```