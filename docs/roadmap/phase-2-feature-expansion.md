# Phase 2: Feature Expansion & Permissions

**Objective:**
Enhance core polling features, introduce advanced question types, user profiles, categories, and enforce permissions.

## Goals

- Extend models: `Choice`, `Bookmark`, `PollShare`, `UserProfile`, `Category`.
- Support multiple question types (single, multiple, free-text).
- Public vs. private polls and category filtering.
- Bookmark and share functionality.
- Role-based permissions (poll creator, admin).

## Deliverables

1. Updated Django models, migrations for new fields and relationships.
2. DRF serializers and viewsets for choices, bookmarks, poll shares, profiles, categories.
3. Filters: by category, public/private, creator.
4. Permission classes to restrict access to owners and admins.
5. Unit and API tests for new features.

## AI Agent Tasks

- Generate and update model definitions and migrations.
- Scaffold serializers and viewsets for new endpoints.
- Implement filter backends using `django-filter`.
- Write custom permission classes and integrate them.
- Create tests for question types, bookmarks, and sharing flows.
- Update API documentation.

---
