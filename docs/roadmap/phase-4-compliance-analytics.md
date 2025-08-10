# Phase 4: Compliance & Analytics

**Objective:**
Ensure regulatory compliance with geoblocking and logging, while adding analytics to track poll performance and user engagement.

## Goals

- `ComplianceLog` model and middleware for geoblocking and age checks.
- Simple geolocation via free API (`ipapi.co`) and caching.
- `PollAnalytics` model for time-series and geographic data aggregation.
- Endpoints for compliance logs and analytics reports.
- Dashboard stubs or export endpoints (CSV/JSON).

## Deliverables

1. Models, middleware, and migrations for compliance and analytics.
2. Celery tasks or background processor to aggregate analytics.
3. DRF viewsets for compliance logs and analytics retrieval.
4. Implement geoblocking middleware to enforce country restrictions.
5. Tests for compliance scenarios (blocked countries, age verification) and analytics accuracy.

## AI Agent Tasks

- Generate `ComplianceLog` and `PollAnalytics` models with migrations.
- Scaffold compliance middleware and integrate into settings.
- Implement geolocation utility and caching logic.
- Create analytics aggregator task and endpoints.
- Write tests for compliance enforcement and analytics aggregation.
- Update API documentation with compliance and analytics sections.

---
