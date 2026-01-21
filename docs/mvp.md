# MVP – <ProjektNamn>

## 1. Syfte (1–3 meningar)
Bygg en minimal version av <produkt> som låter <målgrupp> göra <kärnnytta>.
Målet är att validera <antagande> och kunna driftsätta via CI.

## 2. Målgrupp & problem
- Målgrupp: <vem>
- Problem: <vad gör ont idag>
- Lösning (MVP): <hur ni löser det minimalt>

## 3. MVP-scope (vad ingår)
### Måste (P0)
- [ ] Autentisering: registrering + login + logout
- [ ] Skapa inlägg (text) + lista feed
- [ ] Profil-sida: visa användarnamn + antal inlägg
- [ ] Grundläggande moderation: rapportera inlägg (flagga)

### Bör (P1)
- [ ] Sök (enkel)
- [ ] Följ användare

### Inte i MVP (explicit)
- Realtid/chat (WebSockets)
- DM, grupper, filer/bilder
- Notiser, rekommendationsalgoritmer
- Mobilapp

## 4. User stories + Acceptance Criteria
### US-01: Registrera konto
**Som** besökare **vill jag** skapa konto **så att** jag kan posta.
**AC**
- Givet att jag anger unik e-post + lösenord, när jag skickar formuläret, då skapas konto.
- Lösenord lagras hashat.
- Vid fel (t.ex. e-post finns) visas tydligt felmeddelande.

### US-02: Skapa inlägg
**Som** inloggad användare **vill jag** posta text **så att** andra kan se det i flödet.
**AC**
- Endast inloggade får skapa inlägg (401 annars).
- Max 280 tecken.
- Inlägget syns i feed direkt efter skapande.

## 5. API-kontrakt (minsta endpoints)
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/posts`
- `GET /api/posts?limit=...`
- `GET /api/users/<id>`

*(håll det litet – hellre 5 stabila endpoints än 20 halvdana)*

## 6. Data-modell (minsta tabeller)
**User**
- id, email, password_hash, created_at

**Post**
- id, user_id, content, created_at

**Report** (om ni kör moderation)
- id, post_id, reporter_user_id, reason, created_at

## 7. Icke-funktionella krav (DevSecOps)
### Säkerhet (MVP-nivå)
- Inputvalidering (length, required)
- Rate limit på login
- Security headers (t.ex. via reverse proxy)
- Secrets via env vars (aldrig i repo)
- Dependabot/SCA + bandit (eller motsv.)

### Drift/CI
- `docker build` + `docker compose up` lokalt
- CI pipeline: lint + tester + build
- Deploy till staging (minst) automatiskt på merge till main

## 8. Definition of Done (MVP “klar” när)
- Alla P0 stories är implementerade och testade
- Minst:
  - unit tests för core logik
  - API/integration test för post-flöde
- CI är grön på main
- Kan köras med en kommando-rad: `docker compose up`
- README innehåller setup + hur man kör tester

## 9. Risker & avgränsningar
- Risk: auth tar tid → använd session/JWT standardbibliotek, ingen “egen crypto”
- Risk: scope creep → allt som inte står i P0 är “nej” tills MVP är live

## 10. Demo-scenario (vad ni visar)
1) Registrera konto  
2) Logga in  
3) Skapa post  
4) Visa feed  
5) Rapportera post  
6) Visa att CI passerar + deploy till staging
