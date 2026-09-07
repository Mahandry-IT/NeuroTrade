# 🤖 Trading Bot IA — Backend

Backend Python/FastAPI pour un bot de trading crypto mono-utilisateur, piloté par IA (Gemini free tier).

## Architecture

```
app/
├── core/                    # Config, DB, sécurité, scheduler
│   ├── config.py            # Variables d'environnement (pydantic-settings)
│   ├── database.py          # SQLAlchemy engine + session
│   ├── deps.py              # FastAPI dependencies (JWT auth)
│   ├── security.py          # Chiffrement Fernet + JWT + bcrypt
│   └── scheduler.py         # Boucle d'analyse continue (APScheduler)
├── modules/
│   ├── auth/                # Inscription, connexion, plateforme trading
│   ├── trading_config/      # Paramètres trading + contrôle bot
│   ├── simulation/          # Mode simulation (RG-5)
│   ├── market_analysis/     # Indicateurs techniques + Gemini + fallback
│   ├── trading_engine/      # Décision + exécution ordres
│   ├── notifications/       # In-app + email
│   ├── history/             # Historique trades + stats
│   └── tax_tracking/        # Compteurs fiscaux + export CSV
├── schemas/                 # DTOs Pydantic transverses
└── tests/                   # Tests unitaires + intégration
```

## 🚀 Démarrage rapide avec Docker

### Prérequis

- [Docker](https://docs.docker.com/get-docker/) >= 24.0
- [Docker Compose](https://docs.docker.com/compose/install/) >= 2.20

### 1. Configurer l'environnement

```bash
cp .env.example .env
# Éditer .env avec vos clés (surtout GEMINI_API_KEY et ENCRYPTION_KEY)
```

Générer une clé de chiffrement :
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 2. Lancer avec Docker Compose

```bash
docker compose up -d --build
```

Cela lance :
- **API** FastAPI sur `http://localhost:8000`
- **PostgreSQL 16** sur `localhost:5432`

### 3. Vérifier

```bash
# Healthcheck
curl http://localhost:8000/health

# Documentation Swagger
open http://localhost:8000/docs

# ReDoc
open http://localhost:8000/redoc
```

### 4. Arrêter

```bash
docker compose down          # arrête les conteneurs
docker compose down -v       # arrête + supprime les données
```

## 🐍 Développement local (sans Docker)

```bash
# 1. Créer l'environnement virtuel
python -m venv .venv
source .venv/bin/activate      # Linux/Mac
# .venv\Scripts\activate       # Windows

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Lancer PostgreSQL (ou utiliser Docker pour la DB seule)
docker compose up -d db

# 4. Configurer
cp .env.example .env
# Éditer .env

# 5. Créer les tables
python -c "from app.core.database import engine, Base; from app.main import app; Base.metadata.create_all(bind=engine)"

# 6. Lancer l'API
uvicorn app.main:app --reload
```

## 📡 Endpoints API

Base URL : `http://localhost:8000/api/v1`

### Authentification

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `POST` | `/auth/register` | Inscription utilisateur |
| `POST` | `/auth/login` | Connexion → JWT |
| `POST` | `/auth/platform-connect` | Connexion plateforme trading |
| `GET` | `/auth/platform-status` | Statut connexion plateforme |

### Configuration Trading

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/config/trading-params` | Lire la config |
| `PUT` | `/config/trading-params` | Modifier la config |
| `PUT` | `/config/simulation-mode` | Bascule simulation/réel (RG-5) |

### Contrôle Bot

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `POST` | `/bot/start` | Démarrer le bot |
| `POST` | `/bot/stop` | Arrêter le bot (immédiat, RG-6) |
| `GET` | `/bot/status` | État du bot |

### Historique

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/history/trades` | Liste paginée des trades |
| `GET` | `/history/stats` | Stats performance |

### Fiscalité

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/tax/counters` | Compteurs RG-8/RG-11 |
| `GET` | `/tax/export` | Export CSV fiscal |

### Notifications

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/notifications/` | Notifications non lues |
| `POST` | `/notifications/{id}/read` | Marquer comme lu |
| `POST` | `/notifications/read-all` | Tout marquer comme lu |

### Autres

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/health` | Healthcheck (DB) |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/redoc` | ReDoc |

## 🔐 Variables d'environnement

| Variable | Requis | Description |
|----------|--------|-------------|
| `DATABASE_URL` | ✅ | URL PostgreSQL |
| `GEMINI_API_KEY` | ✅ | Clé API Google Gemini |
| `ENCRYPTION_KEY` | ✅ | Clé Fernet pour chiffrer les clés API |
| `JWT_SECRET_KEY` | ✅ | Secret pour signer les JWT |
| `TRADING_PLATFORM_API_KEY` | ⚙️ | Clé API plateforme trading |
| `TRADING_PLATFORM_API_SECRET` | ⚙️ | Secret API plateforme trading |
| `SMTP_HOST` | ⚙️ | Serveur SMTP (notifications email) |
| `SMTP_PORT` | ⚙️ | Port SMTP |
| `SMTP_USER` | ⚙️ | Utilisateur SMTP |
| `SMTP_PASSWORD` | ⚙️ | Mot de passe SMTP |

## 🧪 Tests

```bash
# Tous les tests
pytest

# Avec couverture
pytest --cov=app --cov-report=html

# Un seul module
pytest app/tests/modules/trading_engine/
```

## 🏗️ Règles métier (RG)

| RG | Description | Implémentation |
|----|-------------|----------------|
| RG-1 | Paramètres configurables | `TradingConfig` + endpoints CRUD |
| RG-2 | Limite de gain | `gain_limit_pct` dans config |
| RG-3 | Limite de perte (prioritaire) | `should_force_sell()` — pure function testable |
| RG-4 | Décision par analyse technique | `MarketAnalysisService` — Gemini + fallback rule-based |
| RG-5 | Mode simulation par défaut | `simulation_mode=True` + confirmation requise pour désactiver |
| RG-6 | Arrêt immédiat du bot | `stop_scheduler(wait=False)` — aucune action après stop |
| RG-8 | Quota mensuel de trades | `max_trades_per_month` + compteur en base |
| RG-9 | Durée min de détention | `min_holding_duration` — prioritaire APRÈS RG-3 |
| RG-10 | Idempotence ordres | Clé `position_id + cycle_timestamp` |
| RG-11 | Export fiscal | `TaxTrackingService.export_csv()` |

## 📁 Structure des données

- **SQLAlchemy** — ORM avec PostgreSQL
- **Alembic** — migrations versionnées
- **Pydantic v2** — validation des DTOs
- **JWT** — authentification applicative
- **Fernet** — chiffrement des clés API au repos

## 📄 License

Projet privé.
