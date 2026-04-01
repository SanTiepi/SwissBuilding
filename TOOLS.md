# TOOLS.md — SwissBuilding Environment

## Workspace
- Chemin : `C:\PROJET IA\SwissBuilding`
- Branche active : `building-life-os`
- Repo GitHub : `SanTiepi/SwissBuilding`

## Exec Approval
- Wildcard `**` configuré pour agent swissbuilding → full auto (pas de demande de permission)
- Claude Code : permissions full dans le repo

## Commandes de validation
```bash
# Frontend
cd frontend
npm run validate     # tsc + eslint + prettier
npm test             # vitest unit tests (996 tests)

# Backend
cd backend
ruff check app/ tests/
ruff format --check app/ tests/
pytest --tb=short -q  # 7150+ tests
```

## Services clés
- API backend : FastAPI (port 8000)
- Frontend : React 18 + Vite (port 5173)
- DB : PostgreSQL/PostGIS (port 5432)
- Docker Compose : `docker-compose.yml`

## GitHub
- Owner : SanTiepi
- Repo : SwissBuilding
- Branche principale : `main`
- Branche active features : `building-life-os`
- Labels standards : P0/P1/P2/P3, bug, feature, tech-debt

## Variables d'environnement
- `ANTHROPIC_API_KEY` : configurée (Claude Sonnet)
- GitHub token : configuré dans les skills