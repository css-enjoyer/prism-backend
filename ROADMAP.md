# Roadmap

Prism is an AI-powered code review API. When a pull request is opened, Prism receives the event via webhook, analyzes the diff using an LLM, and posts structured feedback directly to the PR.

---

## Current State

**Month 1 — Complete**

- FastAPI backend with async PostgreSQL via SQLAlchemy and Supabase
- GitHub webhook receiver with HMAC-SHA256 signature verification
- AI diff analysis via OpenRouter returning structured JSON feedback across four categories: bugs, security, performance, and style
- Idempotency via delivery ID deduplication
- Background task processing to meet GitHub's 10-second webhook timeout

**Month 2 — In Progress**

- PR comment posting via GitHub REST API
- Analysis retrieval endpoints (`GET /analyses`, `GET /analyses/{id}`)
- API key authentication on retrieval endpoints
- Error handling and failed analysis logging
- Pytest coverage

**Month 3 — Planned**

- Docker containerisation
- GitHub Actions CI/CD pipeline
- Deployment to Render
- Next.js dashboard for visualising analysis history

---

## Known Improvements

**Inline review comments**
Currently Prism posts a single general PR comment. GitHub's API supports inline comments attached to specific lines in the diff. This requires parsing the raw diff to map source line numbers to diff positions. Deferred due to complexity — the architecture is already in place to support it.

**More Context**
Fetch the full file contents for each changed file and include them alongside the diff as context. The model would then see the complete picture. This uses the GitHub API's contents endpoint. Currently... "Analysis is based on the PR diff and may not reflect full file context"

**Richer comment formatting**
The current PR comment is functional markdown. A table-based layout with per-category sections and file references would be more readable.

**Failed analysis tracking**
If the AI call or JSON parsing fails, the error is currently logged to stdout and the analysis is dropped. A `status` column on the `analyses` table (pending / complete / failed) would make failures visible and retriable.

**Webhook retry queue**
FastAPI's `BackgroundTasks` is sufficient for current scale. For production, a proper task queue (ARQ or Celery) would provide retries, timeouts, and visibility into task state.

**Per-repo configuration**
Analysis categories and severity thresholds are currently global. Per-repo configuration would allow teams to tune what Prism flags.

**Rate limiting**
No rate limiting on the webhook endpoint. A production deployment would need this to prevent abuse.
