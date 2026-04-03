# Inlämning - Echo (DevSecOps kultur, processer och automation)

## Repo
Mitt repo finns här:
- https://github.com/jwradhe/Echo

## Kort om projektet
Echo är mitt projekt för en social app. Man kan skapa inlägg, kommentera och hantera trådar.
Man kan också stänga svarstråd och bryta ut en diskussion till en privat tråd med valda deltagare.

Teknik vi använt:
- Flask (Python)
- MySQL
- HTML/CSS/JavaScript
- pytest, Newman och Playwright för testning

## Hur vi jobbat (kultur och process)
Vi har försökt jobba enligt DevSecOps-tänk:
- Små ändringar i taget i stället för stora engångsändringar.
- Test och lint som en naturlig del av flödet, inte som sista steg.
- Fokus på behörighet och validering i API:er, så att fel personer inte kan göra fel saker.

Processen har i praktiken varit:
- implementera en funktion
- testa lokalt
- fixa fel
- köra samma saker i CI via GitHub Actions

## Automation / CI
Vi har ett workflow i:
- `.github/workflows/tests.yml`

Den kör på push och pull request och gör bland annat:
- startar MySQL i CI
- laddar in `schema.sql`
- kör lint:
  - `npm run lint:py`
  - `npm run lint:js`
- kör tester:
  - `pytest -q`
  - `npm run api-test`
  - `npm run e2e`

## Säkerhet och kvalitet
Exempel på saker vi jobbat med:
- inloggning/autentisering för skyddade actions
- inputvalidering (t.ex. tomma fält och maxlängd)
- behörighetskontroller i sociala funktioner (ägarskap, privata trådar)
- testning på flera nivåer (API + E2E + Python-tester)

## Vad jag lämnar in
- Repo: https://github.com/jwradhe/Echo
- Dokumentation:
  - `README.md`
  - `INLAMNING.md`
- Arbetsfiler i repot:
  - kod i `app/`
  - tester i `tests/`
  - CI i `.github/workflows/`
  - databas i `schema.sql`

## Så kör man projektet
```bash
cp .env.example .env
mysql -u root -p < schema.sql
python3 -m app
```

Köra tester:
```bash
pytest
npm run api-test
npm run e2e
```
