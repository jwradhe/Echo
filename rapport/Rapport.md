# Echo — Projektrapport
## DevSecOps: Säker containeriserad webbapplikation

**Kurs:** DevSecOps & Säker Infrastruktur  
**Datum:** 2026-04-28 
**Författare:** Christoffer Jörgensen & Jimmy Wrådhe  
**Repo:** https://github.com/jwradhe/Echo  
**Demo:** https://echo.wradhe.se

---

## Innehållsförteckning

1. [Introduktion](#1-introduktion)
2. [Arkitektur](#2-arkitektur)
3. [Hotmodellering](#3-hotmodellering)
4. [Säkerhetsåtgärder](#4-säkerhetsåtgärder)
5. [Containerisering](#5-containerisering)
6. [CI/CD Pipeline](#6-cicd-pipeline)
7. [Deployment](#7-deployment)
8. [Övervakning & Incidenthantering](#8-övervakning--incidenthantering)
9. [Slutlig reflektion](#9-slutlig-reflektion)

---

## 1. Introduktion

Echo är en mikroblogg-webbapplikation byggd med Python och Flask där användare kan skapa inlägg, kommentera, följa varandra och bryta ut privata diskussionstrådar. Applikationen använder MySQL som databas och exponeras via en självhostad server på [echo.wradhe.se](https://echo.wradhe.se).

Denna slutrapport beskriver vidareutvecklingen av Echo från en tidigare fungerande kursapplikation till en mer produktionsmässig tjänst enligt DevSecOps-principer. Arbetets fokus har varit säkerhet, containerisering, automatisering och driftsättning, där hotmodellering och riskanalys har kopplats till konkreta tekniska förändringar i kod, infrastruktur och pipeline.

Applikationen är byggd från grunden inom ramen för kursen. Arbetet har skett iterativt — funktionalitet och säkerhet har vuxit fram parallellt i takt med att ny kunskap tillförts. Istället för att säkerhet behandlats som ett separat steg i slutet har det integrerats löpande under hela utvecklingsprocessen, i linje med principen *Shift Left*: hotmodellering, containerisering, säkerhetsscanning och automatiserad driftsättning har etablerats allteftersom vi lärt oss verktygen och metoderna.

Resultatet är en fullständig webbapplikation med containeriserad driftsmiljö, automatiserad CI/CD-pipeline med inbyggd säkerhetsanalys och realtidsövervakning via Prometheus och Grafana.

Rapporten redovisar både vilka tekniska val som gjorts och hur de valen kopplar till kraven för en säkrare, driftsatt och mer hållbar tjänst.

---

## 2. Arkitektur

### Före slutprojekt

Före slutprojektet var Echo i huvudsak utformat som en traditionell serverrenderad webbapplikation med Flask som backend, MySQL som databas och Jinja2 för HTML-rendering. Lösningen var funktionell och tydlig, men arkitekturen var primärt applikationscentrerad: affärslogik, route-hantering och felhantering låg nära varandra i samma lager, med begränsad separation mellan funktionella och operativa ansvar.

Frontendlagret byggde på HTML-mallar, Bootstrap via CDN samt egen JavaScript för interaktiva moment. Datakommunikation skedde både via klassiska formulärflöden och via enklare JSON-endpoints. Ur utvecklingsperspektiv gav detta snabb iteration, men ur säkerhets- och driftsynpunkt blev flera kontroller implicit beroende av enskilda implementationer snarare än av gemensamma skyddsmekanismer.

Driftsmässigt var lösningen i detta skede främst anpassad för lokal användning. Miljökonfiguration hanterades i `.env`, och teststöd fanns redan med `pytest`, `newman` och `playwright`. Samtidigt saknades en fullt sammanhållen leveranskedja där säkerhetskontroller, containerhärdning och deployment ingick som en konsekvent del av arkitekturen.

**Arkitekturöversikt före förändringar:**

```text
Klient (webbläsare)
  │
  ▼
Flask + Jinja2 (app-lager)
  ├── Routes och affärslogik nära varandra
  ├── Enklare JSON-endpoints
  └── Grundläggande sessionshantering
  │
  ▼
MySQL (lokal/utvecklingsfokus)
```

### Efter slutprojekt

Under slutprojektet vidareutvecklades Echo till en helhetsorienterad DevSecOps-arkitektur där applikation, infrastruktur och leveranskedja behandlas som en sammanhängande teknisk lösning. Den grundläggande stacken (Flask, MySQL, Jinja2, JavaScript) behölls, men kompletterades med tydligare lager för säkerhet, observerbarhet, reproducerbar drift och automatiserad leverans.

Arkitekturen omfattar nu fyra samverkande lager:

- Applikationslager: Flask-app med separerade blåkopior, strukturerad loggning och endpoint-specifik rate limiting.
- Datalager: MySQL med miljöseparerad konfiguration för utveckling, test och produktion.
- Driftslager: Docker Compose med `web`, `db`, `prometheus`, `mysqld_exporter` och `grafana`.
- Leveranslager: GitHub Actions för test (`tests.yml`), beroendeskanning (`sca.yml`) och deployment (`deploy.yml`).

I förändringshistoriken mellan 2026-03-08 och 2026-04-28 framträder en stegvis mognad från funktionsutveckling till drift- och säkerhetshärdning. Funktioner som likes, bild/emoji-stöd, följ/följer och sök kompletterades med säkerhetsmekanismer (bland annat HTTP-säkerhetshuvuden, XSS-reducering och rate limiting), containerhärdning (multi-stage build, non-root user) samt utbyggd observability med Prometheus och Grafana.

**Arkitekturöversikt efter förändringar:**

```text
         GitHub Actions
   (tests.yml + sca.yml + deploy.yml)
        │
        ▼
Klient ──► Reverse proxy/TLS ──► Flask (web)
               │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
     MySQL            Prometheus         Strukturerad loggning
        │                  │
        └────────────► Grafana ◄───────────────┘
```

Förändringen innebär att arkitekturen inte längre enbart beskriver hur applikationen körs, utan även hur kvalitet, säkerhet och driftbarhet säkerställs över tid.


---

## 3. Hotmodellering

### Metod och avgränsning

Hotmodelleringen utgår från `SECURITY_RISK_ANALYSIS.md` och genomfördes med STRIDE som analysmetod samt OWASP Top 10 som klassificeringsstöd. Arbetet avgränsades till de attackytor som är mest relevanta för Echo i drift: autentisering, tillståndsförändrande endpoints, sessionshantering, klientnära rendering av användardata, containerkonfiguration och leveransflöde.

**Metodflöde:**

```text
Systemavgränsning
  │
  ▼
Identifiering av attackytor
  │
  ▼
STRIDE-analys per komponent
  │
  ▼
Riskvärdering (sannolikhet × konsekvens)
  │
  ▼
Prioriterade åtgärder och implementation
```

### Identifierade attackytor

Följande ytor bedömdes som mest kritiska:

- Auth-flöden: `/login`, `/register`, session cookies.
- API-routes för skrivande trafik: skapande av inlägg/svar, reaktioner och sociala interaktioner.
- Frontend-JavaScript som renderar användargenererat innehåll.
- Docker och nätverksexponering mellan `web` och `db`.
- Miljövariabler/hemligheter i build- och deploykedjan.

**Förenklat dataflöde för hotmodellering:**

```text
Användare
  │
  ├── POST /login, /register
  ├── POST /api/posts, /api/posts/*
  └── GET / (rendering av användargenererat innehåll)
          │
          ▼
      Flask-applikation
          │
          ▼
         MySQL
```

### Riskbild (sammanfattning)

Riskanalysen identifierade flera återkommande mönster av hög prioritet:

- Brute force och credential stuffing mot inloggning vid avsaknad av throttling.
- XSS-risk vid osäker DOM-rendering (tidigare `innerHTML`-mönster).
- Informationsläckage via alltför detaljerade felmeddelanden.
- Security misconfiguration i HTTP-lagret (saknade headers/CSP/HSTS i tidigare läge).
- Exponeringsrisker i containerdrift (databasport, root-exekvering, credential-hygien).

Riskerna bedömdes med sannolikhet/konsekvens och prioriterades i nivåerna P1-P3. P1-åtgärderna användes som underlag för det första härdningssteget i kod och driftmiljö, medan P2/P3 dokumenterades för efterföljande iterationer.

### Från analys till implementation

Projektets styrka i slutskedet är att hotmodelleringen inte stannade vid teori. Flera tidigare identifierade HOT-områden omsattes till kod- och konfigurationsförändringar i samma period som feature-leveranserna:

- HOT-01/HOT-08: rate limiting implementerades för auth och API.
- HOT-02: osäker DOM-rendering ersattes med säkrare hantering i JavaScript.
- HOT-03: felhantering hardenades med mindre exponerande felutdata.
- HOT-04: säkerhetshuvuden lades till centralt i Flask.
- HOT-05/HOT-13: containerhärdning genom portstrategi och non-root-körning.

Den direkta kopplingen mellan identifierat hot, prioriterad åtgärd och faktisk implementation har varit avgörande för att säkerhetsarbetet skulle bli mätbart och spårbart.


---

## 4. Säkerhetsåtgärder

### Översikt

Säkerhetsarbetet i Echo har genomförts i flera lager: applikationskod, HTTP-lager, containerdrift och leveranspipeline. Åtgärderna har prioriterats utifrån riskanalysen och verifierats genom tester, konfigurationsgranskning och förändringshistorik i Git.

**Åtgärdskedja från risk till drift:**

```text
Riskidentifiering (STRIDE/OWASP)
          │
          ▼
Teknisk åtgärd i kod/konfiguration
          │
          ▼
Verifiering i test/pipeline
          │
          ▼
Driftsatt kontroll i produktion
```

### Implementerade åtgärder i applikationen

**1. Rate limiting för auth och API**  
Flask-Limiter har införts och kopplats till inloggning, registrering och API-trafik. Det minskar risken för brute force, credential stuffing och enklare DoS-spam mot skrivande endpoints.

**2. Säkrare klient-IP bakom reverse proxy**  
IP-hanteringen har gjorts proxy-aware med `ProxyFix` och anpassad `key_func` för limitering/loggning. Det säkerställer att rate limiting träffar verklig klient även bakom proxy.

**3. HTTP-säkerhetshuvuden**  
Centralt `after_request`-middleware sätter bl.a. CSP, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy` och HSTS i produktion. Detta stärker skydd mot clickjacking, MIME-sniffing och viss script-missbruk.

**4. XSS-reducering i frontend**  
Frontendkod har justerats för säkrare rendering av användardata i deltagarvyer (från osäkra mönster till säkrare DOM-hantering), vilket direkt adresserar ett av de högst prioriterade hoten i analysen.

**5. Felhantering och informationsläckage**  
Felhantering i appen har härdats med tydligare felgränser och mer kontrollerad exponering av felinformation till slutanvändare, samtidigt som intern loggning bibehålls.

**6. Strukturerad säkerhetsloggning och metrik**  
Säkerhetsrelevanta händelser (exempelvis misslyckade inloggningar) fångas via strukturerad loggning och Prometheus-metriker, vilket förbättrar möjligheterna till upptäckt och uppföljning.

### Implementerade åtgärder i container- och driftmiljö

- Multi-stage Docker build minskar attackytan i runtime-image.
- Applikationen körs som dedikerad non-root-användare i container.
- Databasexponering styrs via miljövariabler och säkrare default-beteende.
- Konfiguration och hemligheter separeras från kod via `.env`/GitHub Secrets.
- Grafana/Prometheus-provisionering sker som kod och kan reproduceras säkert.

### Implementerade åtgärder i CI/CD

- Kvalitetsgrindar i `tests.yml` (lint + tester) på push/pull request.
- SCA i `sca.yml` med `pip-audit` och `npm audit --omit=dev`.
- Dependabot för kontinuerlig uppdatering av Python-, Node- och GitHub Actions-beroenden.
- Deployment via `deploy.yml` efter godkänd kedja till `main`.

### Kvarstående risker och förbättringar

Alla åtgärder i riskanalysen är inte slutimplementerade ännu. Exempel på förbättringar för nästa iteration är full CSRF-tokenstrategi för alla relevanta formulärflöden, utökad secret scanning/SAST i samma säkerhetsworkflow samt ännu striktare sessionspolicy vid lång inaktivitet.

Den övergripande trenden är dock tydlig: från punktvisa skydd till integrerad, pipelinebaserad säkerhet där kod, beroenden och driftmiljö kontrolleras kontinuerligt och med tydlig spårbarhet.

---

## 5. Containerisering

### Översikt

Echo körs i sin helhet som en containeriserad applikation med Docker och Docker Compose. Målet var att uppnå reproducerbara miljöer, isolering mellan tjänster och en minimal attackyta i produktion.

### Dockerfile — multi-stage build

Applikationens container byggs med en tvåstegs-Dockerfile (`Dockerfile`).

**Stage 1 — Builder:**
```dockerfile
FROM python:3.11-slim AS builder
RUN apt-get install -y default-libmysqlclient-dev build-essential
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt
```

Det första steget installerar byggverktyg och kompilerar C-extensions som krävs av `mysqlclient`. Dessa verktyg behövs enbart under bygget och ska inte följa med till produktion.

**Stage 2 — Runtime:**
```dockerfile
FROM python:3.11-slim
COPY --from=builder /install /usr/local
RUN useradd --no-create-home --shell /bin/false appuser
USER appuser
```

Det andra steget startar från en ren basimage och kopierar enbart de kompilerade paketen från builder-steget. Byggverktygen lämnar ingen yta i den slutliga imagen. En dedikerad `appuser` utan shell skapas och applikationen körs aldrig som root — i enlighet med principen om lägsta möjliga behörighet.

### Docker Compose — tjänstearkitektur

Hela stacken definieras i `docker-compose.yml` och består av fem tjänster:

| Tjänst | Image | Syfte |
|---|---|---|
| `web` | Byggd lokalt | Flask-applikation |
| `db` | mysql:8.0 | Relationsdatabas |
| `prometheus` | prom/prometheus | Metrikinsamling |
| `mysqld_exporter` | prom/mysqld-exporter | Exporterar MySQL-metriker till Prometheus |
| `grafana` | grafana/grafana | Visualisering av metriker |

Alla tjänster kommunicerar via ett internt Docker-nätverk (`echo_network` med `bridge`-driver). Databasen exponeras inte på ett publikt interface — MySQL-porten binds till `127.0.0.1` om inte annat konfigureras via miljövariabel.

**Startordning och hälsokontroll:**

`web` och `grafana` är beroende av att databasen är redo:

```yaml
depends_on:
  db:
    condition: service_healthy
```

MySQL-containern kör en healthcheck med `mysqladmin ping` var 10:e sekund och anses redo först efter fem lyckade svar. Detta förhindrar race conditions vid uppstart.

**Persistent lagring:**

Databasdata, Prometheus-metriker och Grafana-konfiguration lagras i namngivna Docker-volymer (`mysql_data`, `prometheus_data`, `grafana_data`) och överlever en omstart av containrarna.

### Säkerhetsperspektiv

Under hotmodelleringen (se avsnitt 3) identifierades ett antal containerrelaterade risker. Dessa har adresserats direkt i konfigurationen:

| Risk | Åtgärd |
|---|---|
| Container kör som root (HOT-13) | `appuser` utan shell skapad i Dockerfile — applikationen körs aldrig som root |
| Byggverktyg i produktionsimage | Multi-stage build — byggverktyg finns enbart i `builder`-steget |
| Databas åtkomlig externt | MySQL-porten binds till `127.0.0.1`, inte `0.0.0.0` |
| Hemligheter i imagen | Injiceras via `.env` vid körning, aldrig bakade in i imagen |
| Skrivbar konfiguration | `schema.sql` och Grafana-provisionering monteras som `ro` (read-only) |

---

## 6. CI/CD Pipeline

### Översikt

Projektet använder GitHub Actions för att automatisera testning, säkerhetsanalys och driftsättning. Pipelines är indelade i tre separata workflows med tydliga ansvarsområden.

### Pipelines

#### 6.1 Testpipeline (`tests.yml`)

Triggas vid varje push och pull request, oavsett branch.

Pipelinen startar en MySQL 8.0-service med healthcheck direkt i GitHub Actions-miljön och kör sedan följande steg i ordning:

1. **Lint** — `ruff` för Python, `eslint` för JavaScript
2. **Enhetstester och integrationstester** — `pytest` mot en riktig testdatabas
3. **API-tester** — `newman` (Postman CLI) mot en körande Flask-instans
4. **End-to-end-tester** — `playwright` i headless-läge

Testmiljön konfigureras helt via miljövariabler och använder separata databasinställningar (`EchoDB_test`) för att inte påverka produktion.

#### 6.2 Säkerhetspipeline (`sca.yml`)

Triggas vid push, pull request och schemalagt varje måndag kl. 06:00 UTC.

Nuvarande pipeline fokuserar på SCA (Software Composition Analysis) med två huvudsakliga steg:

| Jobb | Verktyg | Vad som skannas |
|---|---|---|
| SCA | `pip-audit`, `npm audit` | Kända CVE:er i tredjepartsberoenden |

Den schemalagda körningen på måndagar fångar upp nya sårbarheter i beroenden även när ingen kod förändrats.

**SCA — Software Composition Analysis:**
`pip-audit` skannar `requirements.txt` mot PyPI Advisory Database. `npm audit` körs med `--omit=dev` eftersom alla Node-paket är testverktyg som aldrig driftsätts.

I kombination med branch protection, testworkflows och Dependabot skapas en kontinuerlig säkerhetskontroll över beroenden i hela leveranskedjan.

#### 6.3 Deployment-pipeline (`deploy.yml`)

Triggas enbart vid push till `main`. Se avsnitt 7 för detaljerad beskrivning.

### Gate-modell

```text
Push till feature-branch
        │
        ▼
  tests.yml ──── FAIL → blockeras
        │
      PASS
        │
        ▼
  sca.yml ─────── FAIL → blockeras
        │
      PASS
        │
        ▼
   Pull Request → merge till main
        │
        ▼
  deploy.yml → driftsättning
```

Kod som inte passerar tester eller säkerhetsscanningar kan inte mergas till `main` och når aldrig produktion. Gate-modellen förutsätter att `main` är skyddad med branch protection rules i GitHub — dessa kräver att alla status checks passerar och att en pull request skapats innan merge tillåts. 

### Dependabot

Utöver pipelines är Dependabot konfigurerat (`.github/dependabot.yml`) för att automatiskt föreslå uppdateringar av beroenden. Det bevakar tre ekosystem och skapar pull requests varje måndag:

| Ekosystem | Katalog | Max öppna PR:s |
|---|---|---|
| `pip` (Python) | `/` | 10 |
| `npm` (Node.js) | `/` | 10 |
| `github-actions` | `/` | 5 |

Pull requests från Dependabot löper genom samma test- och säkerhetspipelines som all annan kod innan de kan mergas.

---

## 7. Deployment

### Översikt

Applikationen driftsätts på en självhostad server och är tillgänglig på [https://echo.wradhe.se](https://echo.wradhe.se). Driftsättningen sker automatiskt via GitHub Actions när kod mergas till `main`-branchen.

### Före och efter

Innan CI/CD-pipelinen var på plats skedde driftsättning manuellt:

**Före:**
1. Utvecklaren SSH:ar manuellt in till servern
2. `git pull` körs för hand
3. Applikationen startas om manuellt
4. Inga kontroller av att tester eller säkerhetsskanningar passerat

**Efter:**
1. Kod pushas till `main` (kräver att tester + säkerhetsskanningar passerat)
2. GitHub Actions tar över automatiskt
3. Hemligheter injiceras säkert från GitHub Secrets
4. Containrar byggs om och startas — ingen manuell inblandning krävs

Det manuella flödet var både långsamt och felkänsligt: hemligheter hanterades ad hoc och det fanns ingen garanti för att tester körts innan deploy.

### Driftsättningsflöde

```text
Push till main
      │
      ▼
GitHub Actions: deploy.yml
      │
      ├── Generera .env från GitHub Secrets
      │
      ├── SSH till produktionsserver
      │
      ├── git pull origin main
      │
      ├── docker compose down
      ├── docker compose up -d --build
      └── docker image prune -f
```

**1. Trigga:**
Varje push till `main` startar deployment-workflowen. Eftersom `main` skyddas av att tester och säkerhetsscanningar måste passera är det garanterat att bara validerad kod driftsätts.

**2. Hemlighetshantering:**
Alla känsliga värden — databaslösenord, Flask secret key, SSH-nyckel, Grafana-lösenord — lagras som GitHub Secrets och injiceras dynamiskt under körning:

```yaml
printf "FLASK_SECRET_KEY=${{ secrets.FLASK_SECRET_KEY }}\n\
MYSQL_PASSWORD=${{ secrets.MYSQL_PASSWORD }}\n..." > .env
```

`.env`-filen skapas på servern vid varje deploy och existerar aldrig i git-historiken. Detta förhindrar att hemligheter exponeras vid en eventuell repo-kompromiss.

**3. SSH-åtkomst:**
GitHub Actions ansluter till servern med en privat SSH-nyckel (`SSH_PRIVATE_KEY`) lagrad som secret. Värden `SSH_HOST`, `SSH_USER` och `SSH_PORT` är också secrets, vilket gör att serveradressen inte exponeras i workflow-konfigurationen.

**4. Noll-driftstopp (begränsat):**
`docker compose down` följt av `docker compose up -d --build` innebär ett kort avbrott under omstarten. I nuvarande konfiguration accepteras detta. En framtida förbättring vore blue-green deployment eller rolling updates.

**5. Skräphantering:**
`docker image prune -f` tar bort gamla, oanvända images efter varje build för att förhindra att diskutrymmet tar slut på servern.

### Miljöseparation

Applikationen har tre distinkta miljöer med separata konfigurationer:

| Miljö | Konfiguration | Databas |
|---|---|---|
| Development | `.env` (lokal) | Lokal MySQL |
| Testing | Miljövariabler i GitHub Actions | `EchoDB_test` (ephemeral) |
| Production | Genererad `.env` från GitHub Secrets | MySQL via Docker |

Produktionsmiljön aktiverar hårdare säkerhetsinställningar som inte är aktiva i test:

```ini
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Strict
FLASK_DEBUG=0
LOG_LEVEL=WARNING
```

### HTTPS och TLS

Applikationen är tillgänglig via HTTPS på [echo.wradhe.se](https://echo.wradhe.se). TLS-terminering sker på servernivå av en reverse proxy som hanterar certifikat via Let's Encrypt. Proxyn tar emot krypterad extern trafik och vidarebefordrar den till Flask-containern internt via HTTP inom Docker-nätverket. Flask-applikationen behöver därmed inte hantera TLS direkt — det ansvaret är delegerat till infrastrukturlagret utanför Docker Compose-stacken.

### Säkerhetsperspektiv

- Hemligheter lagras aldrig i repot — injiceras vid deploy-tillfället
- SSH-nyckel för deploy är separerad från personliga nycklar
- Produktionsservern är inte direkt åtkomlig utan korrekt SSH-nyckel
- `FLASK_DEBUG=0` i produktion — förhindrar att debugger och stack traces exponeras
- Säkra cookie-flaggor aktiveras enbart i produktion
- All extern trafik krypteras via TLS — HTTP-trafik hanteras enbart internt i Docker-nätverket

---

## 8. Övervakning & Incidenthantering

### Översikt

Echo använder Prometheus och Grafana för realtidsövervakning av applikation och databas. Övervakningsinfrastrukturen är en integrerad del av Docker Compose-stacken och konfigureras som kod — ingen manuell setup krävs vid omstart eller ny driftsättning.

### Arkitektur

```text
  Flask-app (:8080)
       │
       ▼ scrape var 15s
  Prometheus (:9090) ◄─── mysqld_exporter (:9104) ◄─── MySQL
       │
       ▼
    Grafana (:3000)
       │
       ▼
  Dashboard (webbläsare)
```

### Prometheus

Prometheus (`prom/prometheus`) samlar in metriker via HTTP-scraping var 15:e sekund från två källor:

**Applikationsmetriker (`web:8080`):**
Flask-applikationen exponerar ett `/metrics`-endpoint med Prometheus-kompatibla metriker, bland annat:
- Antal HTTP-requests per endpoint och statuskod
- Request-latens (histogram)
- Aktiva anslutningar

**Databasmetriker (`mysqld_exporter:9104`):**
`mysqld_exporter` ansluter till MySQL och exporterar metriker som:
- Antal queries per sekund
- Antal aktiva anslutningar
- Bufferpoolstatus
- Felfrekvens

Konfigurationen i `prometheus.yml` definierar scrape-intervall och targets:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: echo_web
    static_configs:
      - targets: ["web:8080"]
  - job_name: mysql
    static_configs:
      - targets: ["mysqld_exporter:9104"]
```

### Grafana

Grafana (`grafana/grafana`) visualiserar data från Prometheus och MySQL. Hela konfigurationen är provisionerad som kod under `grafana/provisioning/`:

- **Datakällor** definieras i `datasources/prometheus.yml` och `datasources/mysql.yml` — laddas automatiskt vid start
- **Dashboards** provisioneras från `dashboards/default.yml` och pekar på JSON-filer i `grafana/dashboards/`

Tre dashboards ingår i repot:

| Dashboard | Innehåll |
|---|---|
| `echo_overview.json` | Överblick — aktiva användare, inlägg per minut, HTTP-statuskoder |
| `echo_monitoring.json` | Systemhälsa — request-latens, databasanslutningar, CPU/minne |
| `echo_security.json` | Säkerhetshändelser — misslyckade inloggningar, 4xx/5xx-trender |

Detta innebär att Grafana är fullt konfigurerat direkt efter `docker compose up` utan några manuella steg. Övervakningskonfigurationen versionshanteras tillsammans med resten av koden — vid en ny driftsättning återställs alla dashboards automatiskt.

### Incidenthantering

#### Nuvarande förmåga

Med Prometheus och Grafana på plats kan driftstörningar identifieras genom att:

1. Observera ökad felfrekvens (5xx-svar) i applikationsdashboardet
2. Identifiera korrelation med databasmetriker (t.ex. full anslutningspool)
3. Undersöka loggar på servern (`docker compose logs web`)

#### Framtida förbättringar

Nuvarande setup saknar automatiserade larm (alerting). Nästa steg för en produktionsmogen övervakningslösning vore:

- **Prometheus Alertmanager** — definiera tröskelregler, t.ex. larm vid >5% 5xx-svar under 2 minuter
- **Notifieringskanaler** — skicka larm via e-post, Slack eller PagerDuty
- **Uptime-check** — extern övervakning (t.ex. UptimeRobot) för att fånga om hela servern är nere

#### Återhämtning

Vid en incident återställs tjänsten via:

```bash
docker compose down
docker compose up -d
```

Alternativt, om en felaktig kod-deploy orsakade problemet, kan föregående version återställas med:

```bash
git revert HEAD
git push origin main  # triggar automatisk re-deploy
```

Databasdata bevaras i Docker-volymer och påverkas inte av en omstart av containrarna.

Övervakningsfilosofin speglar samma princip som genomsyrar resten av projektet: problem ska fångas så tidigt som möjligt. Precis som säkerhetsscanning sker redan vid varje push — inte efter driftsättning — är målet att en driftstörning ska vara synlig i Grafana innan den märks av användarna.

---

## 9. Slutlig reflektion

Echo har under projektets gång utvecklats från en fungerande webbapplikation till en mer sammanhållen DevSecOps-leverans. Den största skillnaden är att säkerhet inte längre hanteras som en separat slutaktivitet, utan som en löpande del av utveckling, test och drift.

Arbetet med hotmodellering gav en tydlig prioritering av risker och gjorde det möjligt att motivera vilka åtgärder som behövde implementeras först. I praktiken innebar detta att säkerhetshärdning kunde ske parallellt med funktionsutveckling (likes, media/emoji, follow/following, sök) utan att tappa leveranstakt.

En viktig lärdom är att driftbarhet och säkerhet är nära kopplade: containerhärdning, secrets-hantering, observability och CI/CD-grindar bidrar tillsammans till robusthet. Projektet visar också värdet av versionshanterad infrastruktur och automatisering, där reproducerbarhet och spårbarhet förbättrar både kvalitet och incidentberedskap.