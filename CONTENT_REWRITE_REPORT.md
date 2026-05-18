# Content Rewrite Report

## Batch 0 - Prep

Status: code prep complete, production data not migrated yet.

Completed in this batch:

- Added `guide_posts.tags` model/schema/API support.
- Added Alembic migration `20260518_0004_content_rewrite_prep`:
  - fixes post #116 typo from `Hướng dẫn thu hoạch lúa hiệu qảu` to `Hướng dẫn thu hoạch lúa hiệu quả`;
  - deletes duplicate post #54 when the legacy UUID slug matches;
  - changes post #102 slug to `phong-tru-sau-duc-than-xen-toc-xoai-1364`;
  - adds nullable `tags` column if missing.
- Added Caddy redirects for the deleted/renamed guide URLs.
- Added Caddy compose mount for `redirects.caddy` so production reload will not fail on import.
- Added `scripts/import_rewritten_articles.py` with title/slug guards.
- Added `scripts/verify_article.py` for per-article acceptance checks.

Not completed yet:

- No production DB migration has been run from this report.
- No rewritten guide article has been imported.
- No live redirect validation has been performed yet.

Required before production migration:

1. Create and verify a PostgreSQL backup.
2. Apply migration in production.
3. Confirm:
   - `SELECT COUNT(*) FROM guide_posts;` returns `128`;
   - post #116 title is corrected;
   - post #54 is deleted;
   - post #102 has the shortened slug;
   - `guide_posts.tags` exists.
4. Reload Caddy and test both old guide URLs return 301 to the new URLs.

## Rewrite Progress

| Batch | Scope | Status | Notes |
|---|---:|---|---|
| 0 | Prep / migration / tooling | Code complete | Awaiting production backup + migration approval |
| 1 | First 5-10 guide drafts | Not started | Must pass `scripts/verify_article.py` one by one |
