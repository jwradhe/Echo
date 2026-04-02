## Demo
Demo finns att testa på https://echo.wradhe.se/


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

**Schema:** tabeller definierade i `schema.sql`

## 🧵 Trådar och kommentarer

Nya funktioner i feeden:
- Kommentera inlägg.
- Stäng/öppna svarstråd (inläggsägare).
- Bryt ut diskussion till privat tråd med valda deltagare.

Regler vid utbrytning:
- Inlägg/svar före utbrytning förblir synliga för alla.
- Nya svar efter utbrytning syns endast för inläggsägare + valda deltagare.
- Inläggsägaren läggs till automatiskt i utbruten tråd.

Relevanta API-endpoints:
- `POST /api/posts/<post_id>/comments`
- `POST /api/posts/<post_id>/reply-lock`
- `POST /api/posts/<post_id>/discussion-groups`

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

## 📊 Grafana

Grafana körs som en del av Docker Compose och är tillgänglig på `http://localhost:3000`.

**Inloggning (default):**
- Användare: `admin`
- Lösenord: `admin` (byt vid första inloggning)

**Konfigurera i `.env` (valfritt):**
```env
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=ditt-lösenord
```

MySQL-datakällan och ett färdigt dashboard (Echo Overview) konfigureras automatiskt vid uppstart via provisioning-filer i `grafana/provisioning/`. Inget manuellt setup krävs.

**Loggar:**
```bash
docker-compose logs -f grafana
```

## 🔒 Säkerhet

### HTTP-säkerhet
- Rate limiting på `/login` och `/register` via Flask-Limiter
- HTTP-säkerhetsheaders: `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options`, `Strict-Transport-Security` (production)
- Session-skydd via Flask-Login med `session_protection = "strong"`

### Lösenord och data
- Lösenord hashade med Argon2
- Inga credentials i källkod eller `docker-compose.yml` — allt via `.env`
- Soft delete på användare, inlägg och svar (data raderas aldrig permanent)

## 📋 Loggning

Strukturerade JSON-loggar skrivs av `echo.security`-loggern i `app/structured_log.py`.

**Vad som loggas:**

| Händelse | Fält |
|---|---|
| `login_success` | `user_id`, `username`, `ip` |
| `login_failure` | `username`, `reason`, `ip` |
| `register_success` | `user_id`, `username`, `ip` |
| `register_failure` | `username`, `reason`, `ip` |
| `logout` | `user_id`, `ip` |
| `rate_limit_hit` | `endpoint`, `ip` |
| `unauthorized_access` | `path`, `method`, `ip` |

**Vad som aldrig loggas:** lösenord, e-postadresser, sessionstokens, request-body.

**Exempel:**
```json
{"timestamp": "2026-04-03T10:22:31+00:00", "event": "login_failure", "ip": "10.0.0.5", "username": "jimmy", "reason": "invalid_credentials"}
{"timestamp": "2026-04-03T10:25:00+00:00", "event": "rate_limit_hit", "ip": "10.0.0.5", "endpoint": "auth.login"}
```

**Filtrera säkerhetshändelser:**
```bash
docker logs echo_web 2>&1 | grep '"event"'
```

**Incidentdetektering:**

| Mönster | Indikation |
|---|---|
| Burst av `login_failure reason=invalid_credentials` från samma IP | Brute force |
| `login_failure reason=banned_account` upprepat | Försök kringgå ban |
| `rate_limit_hit` i snabb följd | Automatiserad attack |
| `unauthorized_access` mot `/api/`-paths | Scanning/fuzzing |

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
