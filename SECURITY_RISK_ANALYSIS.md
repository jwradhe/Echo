# Säkerhetsanalys och Hotmodell – Echo Microblogg

**Datum:** 2026-03-22  
**Version:** 1.0  
**Applikation:** Echo – mikroblogg-webbapplikation (Flask/Python + MySQL + Docker)  
**Metodik:** OWASP Top 10, STRIDE, DevSecOps-principer (Shift-Left, Security by Design)

---

## Innehållsförteckning

| Uppgiftspunkt | Avsnitt i rapporten |
|---|---|
| Hotmodellering / riskanalys | [Avsnitt 2 – Hotmodell (STRIDE)](#2-hotmodell--stride-analys), [Avsnitt 4 – Riskbedömning](#4-riskbedömning) |
| Identifiera attackytor | [Avsnitt 1.2 – Dataflöden](#12-dataflöden-dataflödesdiagram-i-text), [Avsnitt 1.3 – Endpoints](#13-endpoints-attack-surface) |
| Identifiera risker | [Avsnitt 4 – Riskbedömningstabell med S × K-poängsättning](#4-riskbedömning) |
| Identifiera potentiella sårbarheter | [Avsnitt 2 – STRIDE per komponent](#2-hotmodell--stride-analys), [Avsnitt 7 – OWASP Top 10-mappning](#7-owasp-top-10--mappning) |
| Dokumentera konkreta hot | [Avsnitt 3 – HOT-01 till HOT-15](#3-lista-med-konkreta-hot) |
| Riskbedömning (sannolikhet/konsekvens) | [Avsnitt 4 – Tabell S(1–5) × K(1–5) = riskpoäng + visuell riskmatris](#4-riskbedömning) |
| Föreslå åtgärder | [Avsnitt 5 – Å-01 till Å-15 med kodexempel, sorterade P1→P3](#5-föreslagna-åtgärder-sorterade-efter-riskprioritet) |

---

## 1. Applikationsöversikt

### 1.1 Arkitektur och teknisk stack

| Lager | Teknik |
|---|---|
| Backend | Python 3.11, Flask 3.x |
| Databas | MySQL 8.0 (PyMySQL, DBUtils connection pool) |
| Autentisering | Flask-Login + Argon2 lösenordshashning |
| Frontend/Templates | Jinja2 (autoescaping aktiverat), Bootstrap 5.3 (CDN) |
| JavaScript | Vanilla JS (main.js) |
| Containerisering | Docker, Docker Compose |
| CI/CD | GitHub Actions |
| Testning | Pytest (unit/API), Playwright (E2E), Newman/Postman |

### 1.2 Dataflöden (dataflödesdiagram i text)

```text
Webbläsare (Användare)
   │
   ├─ GET /          → index() → MySQL → Jinja2 → HTML-svar
   ├─ POST /login    → load_user_by_username() → verify_password() → session cookie
   ├─ POST /register → create_user() → hash_password() → MySQL
   ├─ POST /api/posts → JSON → MySQL INSERT → JSON-svar
   ├─ POST /api/posts/{id}/like → MySQL toggle → JSON-svar
   ├─ POST /api/posts/{id}/reply → MySQL INSERT → JSON-svar
   ├─ POST /profile  → update_profile() / upsert_profile_image() → MySQL + disk
   └─ POST /delete_echo/{id} → soft-delete MySQL (WHERE user_id = ?)
```

### 1.3 Endpoints (Attack Surface)

| Metod | Endpoint | Auth krävs | Beskrivning |
|---|---|---|---|
| GET | / | Nej | Flöde (publikt) |
| GET | /dashboard | Nej | Alias för / |
| GET | /?q=... | Nej | Sök användare/inlägg |
| POST | /login | Nej | Inloggning |
| POST | /register | Nej | Registrering |
| POST | /logout | Ja | Utloggning |
| GET | /profile/<username> | Nej | Visa profil |
| POST | /profile | Ja | Uppdatera profil |
| POST | /profile/picture | Ja | Ladda upp profilbild |
| POST | /create_echo | Ja | Skapa inlägg (form) |
| POST | /api/posts | Ja | Skapa inlägg (JSON API) |
| POST | /edit_echo/<post_id> | Ja | Redigera eget inlägg |
| POST | /delete_echo/<post_id> | Ja | Ta bort eget inlägg |
| POST | /api/posts/<id>/like | Ja | Gilla/ta bort gilla |
| POST | /api/posts/<id>/bookmark | Ja | Bokmärk inlägg |
| POST | /api/posts/<id>/reply | Ja | Kommentera inlägg |
| POST | /api/posts/<id>/reply-lock | Ja | Stäng/öppna svarstråd |
| POST | /api/posts/<id>/split-discussion | Ja | Bryt ut diskussion |
| POST | /profile/follow/<id> | Ja | Följ/avfölj |

### 1.4 Viktiga tillgångar (Assets)

- **Personuppgifter:** användarnamn, e-post, lösenordshash, bio, profilbild
- **Innehåll:** inlägg (Posts), svar (Replies), reaktioner (Reactions)
- **Sessioner:** Flask-sessionscookies
- **Konfiguration:** hemligheter i `.env`, databaskredentialer
- **Databas:** MySQL med fullständig användar- och innehållsdata
- **Plattformens rykte och användarförtroende**

---

## 2. Hotmodell – STRIDE-analys

| STRIDE-kategori | Hot | Berört komponent |
|---|---|---|
| **S**poofing (Förfalskning) | Kontoövertagande via credential stuffing | `/login` (inget rate-limiting) |
| **S**poofing | Svag eller förutsägbar `SECRET_KEY` möjliggör sessionförfalskning | Flask-session |
| **T**ampering (Manipulering) | CSRF-angrepp mot formuläraktioner (delvis mitigerat av SameSite=Lax) | Alla state-mutating POST-routes |
| **T**ampering | XSS via innerHTML-injection av användardata i JavaScript | `renderSplitParticipants()` i main.js |
| **T**ampering | Lagring av externa bild-URL:er utan begränsning | `/api/posts` image_url-fältet |
| **R**epudiation (Förnekelse) | Inga säkerhetsloggar för autentiseringshändelser | Autentiseringsflödet |
| **R**epudiation | Inga revisionsloggar för administrativa åtgärder | ModerationActions (outnyttjad tabell) |
| **I**nformation Disclosure | Intern felinformation läcker i HTTP-svar | Dashboard-felhanterare, flash-meddelanden |
| **I**nformation Disclosure | MySQL port 3306 exponerad externt i Docker | docker-compose.yml |
| **I**nformation Disclosure | Användaruppräkning via registreringsformulär | `/register` |
| **I**nformation Disclosure | Inga säkerhetshuvuden (saknas CSP, HSTS, X-Frame-Options m.fl.) | Alla HTTP-svar |
| **D**enial of Service | Inga rate-limit på inloggning, registrering eller API-anrop | `/login`, `/register`, `/api/*` |
| **D**enial of Service | Inga gränser för antal inlägg/kommentarer per tidsenhet | `/api/posts`, `/api/posts/*/reply` |
| **E**levation of Privilege | Standardkredentialer för testanvändare/admin i docker-compose och db.py | Docker-miljön, `db.py` |
| **E**levation of Privilege | Ingen explicit sessionsvalidering vid varje request (user kan vara banned utan invalidering) | Flask-Login session |

---

## 3. Lista med konkreta hot

### HOT-01 – Brute force/Credential Stuffing mot inloggning
Det finns ingen rate-limiting, inget kontoavstängning och ingen CAPTCHA på inloggningsendpointen. En angripare kan systematiskt testa lösenordskombinationer mot känd användardata.

### HOT-02 – XSS via innerHTML i JavaScript (renderSplitParticipants)
I `main.js` används `innerHTML` med template literals för att rendera deltagarnamn i "Bryt ut diskussion"-dialogen. Om en användares `display_name` innehåller HTML-tecken (t.ex. `<img src=x onerror=alert(1)>`) exekveras detta som JavaScript i offrets webbläsare.

```javascript
// Sårbar kod (main.js, renderSplitParticipants)
check.innerHTML = `
    <input ... value="${participant.id}" id="split_${participant.id}">
    <label ...>${participant.name}</label>  // ← participant.name är användarinput!
`;
```

### HOT-03 – Informationsläckage via felinformation i HTTP-svar
Undantagsdetaljer exponeras direkt i HTTP-svar till användaren:
```python
# app/__init__.py – dashboard-felhanterare
return f"<h1>Error loading dashboard</h1><p>{str(e)}</p>", 500

# Och i flash-meddelanden:
flash(f"Fel vid skapande av echo: {str(e)}", "danger")
```

### HOT-04 – Avsaknad av HTTP-säkerhetshuvuden
Inga säkerhetshuvuden sätts i applikationen: ingen CSP, ingen X-Frame-Options, ingen HSTS, ingen X-Content-Type-Options. Webbläsaren saknar instruktioner för att blockera inbäddning (clickjacking), MIME-sniffing och inline-skript.

### HOT-05 – MySQL-databas exponerad externt via Docker
```yaml
# docker-compose.yml
ports:
  - "3306:3306"  # ← exponerat på 0.0.0.0:3306 – nåbart utifrån
```
Tillsammans med svaga standardlösenord (`changeme`) innebär detta Direkt databasåtkomst från Internet.

### HOT-06 – Svaga/hårdkodade standardkredentialer
```yaml
# docker-compose.yml
MYSQL_ROOT_PASSWORD: changemeCHANGEME123
MYSQL_PASSWORD: changeme
```
```python
# app/db.py
os.environ.get("DEV_ADMIN_PASSWORD", "ChangeMeNow123")
```
Dessa behöver aldrig ersättas om de glöms bort i produktionsmiljön.

### HOT-07 – Ingen CSRF-skydd (Flask-WTF CSRFProtect används inte)
`Flask-WTF` finns som dependency men `CSRFProtect` initieras aldrig. SameSite=Lax ger partiellt skydd för de flesta POST-förfrågningar men är inte ett fullständigt CSRF-skydd.

### HOT-08 – Ingen rate-limiting på API-endpoints
Alla `/api/*`-endpoints saknar throttling. En angripare kan skicka tiotusentals inlägg, reaktioner eller sökförfrågningar och orsaka databas-DoS eller dataspam.

### HOT-09 – Användaruppräkning via registrering och inloggning
Registreringsformuläret returnerar specifika felmeddelanden: "Username is already taken" vs "Email is already registered", vilket låter angripare inventarisera existerande konton.

### HOT-10 – External CDN-resurser utan Subresource Integrity (SRI)
Bootstrap hämtas från `cdn.jsdelivr.net` utan SRI-hash. Om CDN:n komprometteras kan skadlig JavaScript laddas i alla användares webbläsare.

### HOT-11 – Externa bild-URL:er från godtyckliga domäner
Inlägg kan innehålla `image_url` pekande på valfri extern webbplats. Detta möjliggör:
- Spårpixlar (inhämtning av användarens IP/webbläsarinfo via tredjepartsserver)
- Hot-linking mot godtyckliga servrar
- Potential för client-side SSRF-liknande angrepp

### HOT-12 – Avsaknad av säkerhetsloggning och revisionslog
Misslyckade inloggningar, kontoregistreringar, administrativa åtgärder och säkerhetshändelser loggas inte som strukturerade säkerhetshändelser. Insatser för incidentdetektering saknas helt.

### HOT-13 – Flask körs som root i Docker-container
Dockerfile specificerar ingen icke-rootanvändare. Om applikationen komprometteras har angriparen omedelbart root-åtkomst i containern.

### HOT-14 – Avsaknad av lösenordskomplexitetsvalidering
Minimikravet är 10 tecken men inga krav på komplexitet (versaler, siffror, specialtecken) eller kontroll mot vanliga lösenordslistor.

### HOT-15 – Sessionens livslängd är 7 dagar utan inaktivitetstimeout
En stulen session är giltig i upp till en vecka. Inget stöd för "logga ut alla sessioner" vid misstänkt intrång.

---

## 4. Riskbedömning

Riskformel: **Risk = Sannolikhet (S) × Konsekvens (K)**  
Skala: 1 (Mycket låg) – 5 (Mycket hög)

| # | Hot | OWASP Top 10 | S (1–5) | K (1–5) | Risk | Prioritet |
|---|---|---|---|---|---|---|
| HOT-02 | XSS via innerHTML i JS | A03 – Injection | 4 | 4 | **16** | 🔴 KRITISK |
| HOT-03 | Informationsläckage via felmeddelanden | A05 – Security Misconfiguration | 5 | 3 | **15** | 🔴 KRITISK |
| HOT-05 | MySQL-port exponerad externt | A05 – Security Misconfiguration | 3 | 5 | **15** | 🔴 KRITISK |
| HOT-04 | Inga HTTP-säkerhetshuvuden | A05 – Security Misconfiguration | 5 | 3 | **15** | 🔴 KRITISK |
| HOT-01 | Brute force/Credential Stuffing | A07 – Auth Failures | 4 | 4 | **16** | 🔴 KRITISK |
| HOT-06 | Svaga standardkredentialer | A07 – Auth Failures | 3 | 5 | **15** | 🔴 KRITISK |
| HOT-08 | Ingen rate-limiting på API | A04 – Insecure Design | 4 | 3 | **12** | 🟠 HÖG |
| HOT-07 | Ingen CSRF-skydd | A01 – Broken Access Control | 3 | 3 | **9** | 🟠 HÖG |
| HOT-10 | CDN utan SRI | A08 – Software Integrity | 2 | 5 | **10** | 🟠 HÖG |
| HOT-13 | Docker kör som root | A05 – Security Misconfiguration | 2 | 4 | **8** | 🟡 MEDIUM |
| HOT-11 | Externa bild-URL:er | A10 – SSRF / Privacy | 4 | 2 | **8** | 🟡 MEDIUM |
| HOT-09 | Användaruppräkning | A07 – Auth Failures | 5 | 2 | **10** | 🟠 HÖG |
| HOT-12 | Ingen säkerhetsloggning | A09 – Logging Failures | 4 | 2 | **8** | 🟡 MEDIUM |
| HOT-15 | Lång sessionstid, ingen timeout | A07 – Auth Failures | 3 | 3 | **9** | 🟠 HÖG |
| HOT-14 | Svag lösenordspoliciy | A07 – Auth Failures | 3 | 2 | **6** | 🟡 MEDIUM |

### Riskmatris (visuell illustration)

```text
Konsekvens
  5 │         HOT-05  HOT-06          HOT-10
    │
  4 │                 HOT-01  HOT-02
    │                         HOT-13
  3 │         HOT-03  HOT-04  HOT-07  HOT-15
    │                 HOT-08
  2 │                 HOT-11  HOT-09  HOT-12
    │                         HOT-14
  1 │
    └────────────────────────────────────────
        1       2       3       4       5
                    Sannolikhet
```

---

## 5. Föreslagna åtgärder (sorterade efter risk/prioritet)

### P1 – KRITISK (åtgärda omedelbart)

---

#### Å-01: Implementera HTTP-säkerhetshuvuden (HOT-04)

**Åtgärd:** Lägg till ett middleware i Flask som sätter säkerhetshuvuden på varje svar.

```python
# app/__init__.py – lägg till i create_app() efter blueprints registreras

@app.after_request
def set_security_headers(response):
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/ "
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/; "
        "style-src 'self' https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/ "
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/; "
        "font-src 'self' https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/; "
        "img-src 'self' data: https:; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none';"
    )
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if not app.debug:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
```

**Kontroll:** Kör `securityheaders.com` mot applikationen och verifiera betyg A eller högre.

---

#### Å-02: Åtgärda XSS via innerHTML i JavaScript (HOT-02)

**Åtgärd:** Byt ut `innerHTML` med användardata i `renderSplitParticipants()` mot `textContent`-tilldelning.

```javascript
// app/static/js/main.js – renderSplitParticipants()
// ERSÄTT den nuvarande check.innerHTML med:
participants.forEach((participant) => {
    const check = document.createElement('div');
    check.className = 'form-check';

    const input = document.createElement('input');
    input.className = 'form-check-input split-participant-checkbox';
    input.type = 'checkbox';
    input.value = participant.id;        // UUID – säkert
    input.id = `split_${participant.id}`;

    const label = document.createElement('label');
    label.className = 'form-check-label';
    label.htmlFor = `split_${participant.id}`;
    label.textContent = participant.name;  // ← textContent, INTE innerHTML

    check.append(input, label);
    container.append(check);
});
```

**Kontroll:** Skapa testanvändare med `display_name = '<img src=x onerror=alert(1)>'` och verifiera att ingen alert visas.

---

#### Å-03: Förhindra informationsläckage i felmeddelanden (HOT-03)

**Åtgärd:** Ersätt råa undantagsmeddelanden i HTTP-svar och flash-meddelanden med generiska texter.

```python
# app/__init__.py – dashboard-felhanterare
except Exception as e:
    logger.error(f"Dashboard error: {e}", exc_info=True)  # logga internt
    return render_template("error.html", message="Ett fel uppstod. Försök igen."), 500

# Och för post-skapande:
except Exception as e:
    logger.error(f"Error creating post: {e}", exc_info=True)
    flash("Kunde inte skapa inlägget. Försök igen.", "danger")
```

---

#### Å-04: Stäng MySQL-porten och byt standardkredentialer (HOT-05, HOT-06)

**Åtgärd (docker-compose.yml):** Ta bort den exponerade MySQL-porten och byt lösenord.

```yaml
# docker-compose.yml
# Ta bort eller kommentera bort dessa rader:
# ports:
#   - "3306:3306"

# Ändra lösenord (använd miljövariabler från .env-fil):
environment:
  - MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD}
  - MYSQL_DATABASE=${MYSQL_DATABASE}
  - MYSQL_USER=${MYSQL_USER}
  - MYSQL_PASSWORD=${MYSQL_PASSWORD}
```

Säkerställ att `.env` innehåller starka, slumpmässiga lösenord och att `.env` är i `.gitignore`.

---

#### Å-05: Implementera rate-limiting på känsliga endpoints (HOT-01, HOT-08)

**Åtgärd:** Installera `Flask-Limiter` och sätt gränser på inloggning, registrering och API-anrop.

```bash
pip install Flask-Limiter
```

```python
# app/__init__.py – i create_app()
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# På login-route (auth_routes.py):
@auth_bp.route("/login", methods=["POST"])
@limiter.limit("10 per minute; 50 per hour")
def login():
    ...

# På register-route:
@auth_bp.route("/register", methods=["POST"])
@limiter.limit("5 per hour; 10 per day")
def register():
    ...

# På API-endpoints:
@app.route("/api/posts", methods=["POST"])
@login_required
@limiter.limit("30 per minute")
def create_post_api():
    ...
```

---

### P2 – HÖG (åtgärda inom nästa sprint)

---

#### Å-06: Aktivera CSRF-skydd med Flask-WTF (HOT-07)

**Åtgärd:** Flask-WTF är redan installerat men CSRFProtect är inte initierat. Aktivera det och lägg till CSRF-tokens i alla formulär.

```python
# app/__init__.py – i create_app()
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()
csrf.init_app(app)

# Undanta JSON API-endpoints (de använder SameSite=Lax-cookies):
# csrf.exempt(create_post_api)  # om behövs
```

```html
<!-- I varje HTML-formulär i templates: -->
<form method="post" action="...">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    ...
</form>
```

---

#### Å-07: Implementera Subresource Integrity (SRI) för CDN-resurser (HOT-10)

**Åtgärd:** Lägg till `integrity`-attribut på Bootstrap-resurserna.

```html
<!-- app/templates/index.html och profile.html -->
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css"
      rel="stylesheet"
      integrity="sha384-T3c6CoIi6uLrA9TneNEoa7RxnatzjcDSCmG1MXxSR1GAsXEV/Dwwykc2MPK8M2HN"
      crossorigin="anonymous">

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"
        integrity="sha384-C6RzsynM9kWDrMNeT87bh95OGNyZPhcTNXj1NW7RuBCsyN/o0jlpcV8Qyq46cDfL"
        crossorigin="anonymous"></script>
```

---

#### Å-08: Reducera sessionslivslängden och lägg till inaktivitetstimeout (HOT-15)

**Åtgärd:** Minska session-livslängden och implementera timeut vid inaktivitet.

```python
# app/config.py
PERMANENT_SESSION_LIFETIME = timedelta(hours=int(os.environ.get("SESSION_LIFETIME_HOURS", "8")))
```

```python
# app/__init__.py – lägg till before_request-hook
from datetime import datetime, timezone, timedelta

@app.before_request
def enforce_session_timeout():
    if current_user.is_authenticated:
        last_active = session.get("last_active")
        timeout_minutes = app.config.get("SESSION_INACTIVITY_TIMEOUT_MINUTES", 60)
        if last_active:
            last_active_dt = datetime.fromisoformat(last_active)
            if datetime.now(timezone.utc) - last_active_dt > timedelta(minutes=timeout_minutes):
                logout_user()
                flash("Sessionen har gått ut pga inaktivitet.", "warning")
                return redirect(url_for("auth.login"))
        session["last_active"] = datetime.now(timezone.utc).isoformat()
```

---

#### Å-09: Begränsa externa bild-URL:er med domänvitlista eller proxying (HOT-11)

**Åtgärd:** Antingen begränsa tillåtna domäner eller proxy:a externa bilder via servern.

```python
# app/__init__.py – _is_valid_http_url() – utöka validering
ALLOWED_IMAGE_DOMAINS: set[str] = set()  # tom = alla tillåtna, fyll i för restriktivt läge

# Alternativt: blockera privata IP-adresser (grundläggande SSRF-skydd)
import ipaddress, socket

def _is_valid_image_url(value: str) -> bool:
    if not value:
        return False
    try:
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return False
        # Blockera privata/interna adresser
        hostname = parsed.hostname or ""
        if hostname in ("localhost", "127.0.0.1", "::1"):
            return False
        try:
            ip = ipaddress.ip_address(socket.gethostbyname(hostname))
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                return False
        except (socket.gaierror, ValueError):
            pass
        return True
    except Exception:
        return False
```

---

#### Å-10: Implementera säkerhetsloggning (HOT-12)

**Åtgärd:** Logga säkerhetskritiska händelser strukturerat.

```python
# app/auth_routes.py – i login()
security_logger = logging.getLogger("security")

# Vid misslyckad inloggning:
security_logger.warning(
    "LOGIN_FAILED",
    extra={"username": username, "ip": request.remote_addr, "user_agent": request.user_agent.string}
)

# Vid lyckad inloggning:
security_logger.info(
    "LOGIN_SUCCESS",
    extra={"user_id": user.user_id, "ip": request.remote_addr}
)

# Vid registrering:
security_logger.info(
    "USER_REGISTERED",
    extra={"user_id": user.user_id, "username": username, "ip": request.remote_addr}
)
```

---

### P3 – MEDIUM (planera in i kommande sprints)

---

#### Å-11: Kör Docker-container som icke-root-användare (HOT-13)

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /code

RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Skapa icke-root-användare
RUN useradd --uid 1001 --no-create-home --shell /bin/false appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Byt till icke-root-användare
USER appuser

EXPOSE 5000
CMD ["python", "-m", "app"]
```

---

#### Å-12: Förbättra lösenordspolicyn och e-postvalidering (HOT-14)

```python
# app/auth_routes.py – i register()
import re

def _validate_password(password: str) -> list[str]:
    errors = []
    if len(password) < 10:
        errors.append("Lösenordet måste vara minst 10 tecken.")
    if not re.search(r"[A-Z]", password):
        errors.append("Lösenordet måste innehålla minst en versal.")
    if not re.search(r"\d", password):
        errors.append("Lösenordet måste innehålla minst en siffra.")
    # Blockera vanliga lösenord
    common = {"password12345", "qwertyuiop", "changeme123", "changemenow123"}
    if password.lower() in common:
        errors.append("Lösenordet är för vanligt.")
    return errors

def _validate_email(email: str) -> bool:
    # Enkel RFC-korrekt validering
    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))
```

---

#### Å-13: Minska användaruppräkning (HOT-09)

**Åtgärd:** Returnera ett generiskt felmeddelande för alla registreringsfel om ett konto redan finns.

```python
# app/auth_routes.py – i register()
# ERSÄTT specifika meddelanden med generiskt:
try:
    user = create_user(...)
except IntegrityError:
    flash("Registration failed. Please check your details and try again.", "danger")
    return redirect(url_for("dashboard"))
```

---

#### Å-14: Integrera SAST och dependency scanning i CI/CD (HOT-10, HOT-06)

**Åtgärd:** Lägg till säkerhetsskanningsverktyg i GitHub Actions-pipelinen.

```yaml
# .github/workflows/tests.yml – lägg till följande steg:

- name: Security scan – Python dependencies (Safety)
  run: |
    pip install safety
    safety check -r requirements.txt

- name: SAST – Bandit (Python)
  run: |
    pip install bandit
    bandit -r app/ -ll --exit-zero

- name: Secret scanning – detect-secrets
  run: |
    pip install detect-secrets
    detect-secrets scan --baseline .secrets.baseline
```

---

#### Å-15: Validera sessionen mot databasen vid varje request (HOT-15)

**Åtgärd:** Flask-Logins `user_loader` hämtar redan användaren från DB vid varje request (via `load_user_by_id`). Kontrollera att detta inkluderar `is_banned`-status, vilket redan görs via `is_active`-egenskapen. Lägg till kontostatusvalidering tydligare:

```python
# app/__init__.py – before_request
@app.before_request
def check_user_status():
    if current_user.is_authenticated and not current_user.is_active:
        logout_user()
        flash("Ditt konto har inaktiverats.", "warning")
        return redirect(url_for("dashboard"))
```

---

## 6. Befintliga säkerhetsstyrkor

Applikationen har redan ett gott antal säkerhetsmekanismer på plats:

| Styrka | Beskrivning |
|---|---|
| ✅ Argon2-lösenordshashning | Industristandard, starkt kryptografiskt algoritm |
| ✅ Parametriserade SQL-frågor | Förhindrar SQL-injektion genomgående i kodebasen |
| ✅ Ägarskapskontroll på mutations | `WHERE post_id = %s AND user_id = %s` förhindrar IDOR |
| ✅ Jinja2 autoescaping | `{{ variabel }}` HTML-escapas automatiskt i templates |
| ✅ `textContent` i JS för brödtext | Kommentarsinnehåll och inlägg renderas säkert utan HTML |
| ✅ `SameSite=Lax`-cookies | Delvist CSRF-skydd för POST-endpoints |
| ✅ `HttpOnly`-cookies | JavaScript kan inte läsa sessionscookien |
| ✅ Session protection "strong" | Flask-Login skyddar mot sessionskapning |
| ✅ Profilbild-validering via Pillow | Bildformat kontrolleras, konverteras till WebP |
| ✅ Säker URL-redirect-kontroll | `_is_safe_url()` förhindrar open redirect vid inloggning |
| ✅ Minsta lösenordslängd 10 tecken | Grundlägande lösenordskrav |
| ✅ Soft-delete-mönster | Data bevaras för revisionsändamål |
| ✅ Inloggningsstatus kontrolleras | Bannvariabel och deleted-variabel kontrolleras vid inloggning |

---

## 7. OWASP Top 10 – mappning

| OWASP Top 10 (2021) | Status i Echo | Relevanta hot |
|---|---|---|
| A01 – Broken Access Control | ⚠️ Partiellt | HOT-07 (CSRF) |
| A02 – Cryptographic Failures | ✅ Hanterat | Argon2 för lösenord, HTTPS rekommenderas |
| A03 – Injection | ✅ Hanterat / ⚠️ JS-risk | Parametriserade queries; HOT-02 (XSS) |
| A04 – Insecure Design | ⚠️ Partiellt | HOT-01, HOT-08 (ingen rate-limiting) |
| A05 – Security Misconfiguration | ❌ Saknas | HOT-03, HOT-04, HOT-05, HOT-06 |
| A06 – Vulnerable Components | ⚠️ Okänt | HOT-10 (ingen SRI eller dep-scanning) |
| A07 – Auth and Session Failures | ⚠️ Partiellt | HOT-01, HOT-09, HOT-15 |
| A08 – Software Integrity Failures | ⚠️ Partiellt | HOT-10 (CDN utan SRI, ingen CI-scanning) |
| A09 – Security Logging Failures | ❌ Saknas | HOT-12 |
| A10 – SSRF | ⚠️ Minimal risk | HOT-11 |

---

## 8. Sammanfattning och rekommendationsöversikt

| Prioritet | Åtgärd | Arbetsinsats |
|---|---|---|
| 🔴 P1 | HTTP-säkerhetshuvuden (CSP, HSTS, m.fl.) | Låg – ca 1h |
| 🔴 P1 | Fixa XSS i renderSplitParticipants (main.js) | Låg – ca 30min |
| 🔴 P1 | Ta bort felinformation från HTTP-svar | Låg – ca 1h |
| 🔴 P1 | Stäng MySQL-port i Docker Compose | Låg – ca 15min |
| 🔴 P1 | Rate-limiting på `/login`, `/register`, `/api/*` | Medel – ca 4h |
| 🟠 P2 | Aktivera Flask-WTF CSRFProtect | Medel – ca 4h |
| 🟠 P2 | SRI på CDN-resurser | Låg – ca 1h |
| 🟠 P2 | Sessionshantering (kortare livslängd, inaktivitetstimeout) | Medel – ca 3h |
| 🟠 P2 | Begränsa externa bild-URL:er | Medel – ca 2h |
| 🟠 P2 | Säkerhetsloggning | Medel – ca 4h |
| 🟡 P3 | Docker non-root user | Låg – ca 30min |
| 🟡 P3 | Stärk lösenordspolicy + e-postvalidering | Låg – ca 2h |
| 🟡 P3 | Minska användaruppräkning | Låg – ca 30min |
| 🟡 P3 | SAST + dep-scanning i CI/CD | Medel – ca 3h |
| 🟡 P3 | Sessionsvalidering mot DB | Låg – ca 1h |

---

*Detta dokument är producerat som en del av en DevSecOps-analys och bygger på principerna Shift-Left, Security by Design och OWASP Top 10. Analysen är ett levande dokument som bör uppdateras vid varje signifikant arkitekturförändring.*
