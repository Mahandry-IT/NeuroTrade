# Trading Bot IA — Backend

Squelette de projet Python/FastAPI (structure uniquement, aucune logique implémentée).
Suit le plan `plan-bot-trading-ia-backend.md`.

## Structure

- `app/core/` — config, DB, sécurité, scheduler
- `app/modules/<feature>/` — models, repository, service, router (par feature)
- `app/schemas/` — DTO Pydantic transverses
- `app/tests/modules/<feature>/` — tests miroir de la structure modules

## Démarrage (une fois le code implémenté)

1. `cp .env.example .env` et remplir les valeurs
2. `pip install -r requirements.txt`
3. `alembic upgrade head`
4. `uvicorn app.main:app --reload`

## TODO globaux

- Implémenter chaque module en suivant l'ordre du plan (Conception → Modèle → DTO → Repository → Service → Controller → Sécurité → Tests).
- Invoquer `/postman` une fois les routes stabilisées pour la documentation API.
