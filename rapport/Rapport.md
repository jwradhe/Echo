# Echo — Projektrapport
## DevSecOps: Säker containeriserad webbapplikation

**Kurs:** DevSecOps & Säker Infrastruktur  
**Datum:** 2026-04-29 
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

Applikationen är byggd från grunden inom ramen för kursen. Arbetet har skett iterativt — funktionalitet och säkerhet har vuxit fram parallellt i takt med att ny kunskap tillförts. Istället för att säkerhet behandlats som ett separat steg i slutet har det integrerats löpande under hela utvecklingsprocessen, i linje med principen *Shift Left*: hotmodellering, containerisering, säkerhetsscanning och automatiserad driftsättning har etablerats allteftersom vi lärt oss verktygen och metoderna.

Resultatet är en fullständig webbapplikation med containeriserad driftsmiljö, automatiserad CI/CD-pipeline med inbyggd säkerhetsanalys och realtidsövervakning via Prometheus och Grafana.

Rapporten beskriver hur applikationen växt fram och de tekniska beslut som fattats längs vägen.

---

## 2. Arkitektur


---

## 3. Hotmodellering


---

## 4. Säkerhetsåtgärder

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

1. **Lint** — `flake8` för Python, `eslint` för JavaScript
2. **Enhetstester och integrationstester** — `pytest` mot en riktig testdatabas
3. **API-tester** — `newman` (Postman CLI) mot en körande Flask-instans
4. **End-to-end-tester** — `playwright` i headless-läge

Testmiljön konfigureras helt via miljövariabler och använder separata databasinställningar (`EchoDB_test`) för att inte påverka produktion.

#### 6.2 Säkerhetspipeline (`security.yml`)

Triggas vid push, pull request och schemalagt varje måndag kl. 06:00 UTC. Består av fyra parallella jobb:

| Jobb | Verktyg | Vad som skannas |
|---|---|---|
| SCA | `pip-audit`, `npm audit` | Kända CVE:er i tredjepartsberoenden |
| SAST | `bandit` | Statisk analys av Python-kod (SQL-injection, svag krypto m.m.) |
| Secret scanning | `gitleaks` | Hårdkodade nycklar och hemligheter i git-historiken |
| Container & IaC | `trivy` | Misconfigurationer i `Dockerfile` och `docker-compose.yml` |

Den schemalagda körningen på måndagar fångar upp nya sårbarheter i beroenden även när ingen kod förändrats.

**SCA — Software Composition Analysis:**
`pip-audit` skannar `requirements.txt` mot PyPI Advisory Database. `npm audit` körs med `--omit=dev` eftersom alla Node-paket är testverktyg som aldrig driftsätts.

**SAST — Static Application Security Testing:**
`bandit` analyserar Python-koden i `app/`-mappen med flaggan `-ll` (medium och hög allvarlighetsgrad) och rapporterar fynd som SQL-injection-risker, osäker deserialisering och svaga hashfunktioner.

**Secret scanning:**
`gitleaks` hämtar hela git-historiken (`fetch-depth: 0`) och söker igenom varje commit efter mönster som matchar API-nycklar, lösenord och tokens.

**Container & IaC-scanning:**
`trivy` i `config`-läge analyserar Dockerfile och docker-compose.yml mot kända säkerhetsrekommendationer. Bygget bryts vid fynd med allvarlighetsgrad HIGH eller CRITICAL.

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
  security.yml ── FAIL → blockeras
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