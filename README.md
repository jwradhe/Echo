
## 🚀 Kom igång lokalt

```bash
# 1. Klona repot
git clone <repo-url>
cd echo

# 2. Skapa och aktivera virtuell miljö
python3 -m venv venv
source venv/bin/activate

#3. Installera beroenden
pip install -r requirements.txt
pip install -r requirements-dev.txt
npm install
npx playwright install     

# 4. Starta applikationen
python3 -m app

# Öppna i webbläsaren:
http://127.0.0.1:5001
```

## 🔎 Kodkvalitet (Lint)

Projektet använder linting för att säkerställa konsekvent kodstil och upptäcka vanliga fel.
```bash
### Python
npm run lint:py

### JavaScript / TypeScript
npm run lint:js

### Linting på allt
npm run lint
```

## 🧪 Tester

```bash
### Unit- och integrationstester (Python):
pytest

### API-tester (Postman / Newman):
npm run api-test

### End-to-End tester (Playwright):
npm run e2e

### Köra alla tester:
npm run test:all