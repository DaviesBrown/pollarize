# Phase 1: Minimum Viable Product (MVP)

**Objective:**
Deliver a lean polling system with core functionality to validate product-market fit and gather early feedback.

## Goals

- Basic user management and authentication (JWT).
- Create, read, update, delete (CRUD) for polls and questions.
- Basic voting flow with anonymous support and IP tracking.
- Simple REST API endpoints using Django REST Framework.
- Persist data in MySQL and cache in Redis.

## Deliverables

1. Models and migrations for core, polls, and vote sessions.
2. DRF viewsets and serializers for user registration, login, polls, questions, and votes.
3. Authentication flows: signup, login, token refresh.
4. Vote endpoint validating one vote per IP per poll.
5. API documentation stub (Swagger/OpenAPI via drf-yasg).

## AI Agent Tasks

- Generate Django models for `User`, `Poll`, `Question`, `Choice`, and `VoteSession`.
- Scaffold DRF serializers and viewsets based on models.
- Configure SQLite/MySQL and Redis cache settings.
- Write unit tests for model validation and vote uniqueness.
- Generate initial migrations and apply them.
- Create basic CI workflow to run tests.

---

## Sprint Backlog (10x Developer Detail)

1. Project Setup
   - Create Python virtual environment and install dependencies (`Django`, `djangorestframework`, `djangorestframework-simplejwt`, `django-redis`).
   - Initialize Git repository and configure pre-commit hooks (flake8, black).
   - Scaffold Django project (`config/`, `manage.py`) and create `core` and `polls` apps.
   - Configure base settings: database (MySQL/SQLite fallback), Redis cache, installed apps.

2. Database Modeling
   - Define `User` model extending `AbstractUser` with `subscription_tier`, `is_premium`, `referral_code`.
   - In `polls/models.py`, define `Poll`, `Question`, `Choice`, and `VoteSession` models with fields, relationships, and indexes for performance.
   - Add database constraints: unique vote per `(poll, ip_address)`.
   - Generate and apply initial migrations.

3. API Layer
   - Implement DRF serializers for all models.
   - Build viewsets and routers for `User` (registration, login), `Poll`, `Question`, `Choice`, and `VoteSession`.
   - Integrate JWT authentication endpoints (register, login, token refresh).
   - Add IP tracking middleware or override `perform_create` to store IP in `VoteSession`.

4. Testing & CI
   - Write pytest-based unit tests for models: field validation and unique vote logic.
   - Write API tests using DRF test client to cover authentication and vote endpoint.
   - Set up GitHub Actions workflow: run lint, tests, and coverage badge enforcement.

5. Documentation & Swagger
   - Configure `drf-yasg` for OpenAPI schema generation.
   - Add initial Swagger UI endpoint and generate stub docs.
   - Document environment variables and setup steps in `README.md`.
