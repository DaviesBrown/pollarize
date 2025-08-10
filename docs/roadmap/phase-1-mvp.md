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
