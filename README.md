# Prism

**Automated code review powered by LLMs, delivered as a GitHub PR comment.**

When a pull request is opened, Prism receives a webhook from GitHub, fetches the diff, runs it through a large language model, and posts structured feedback as a comment — no manual action required.

---

## How It Works

```
GitHub PR opened
      │
      ▼
POST /webhook  ──► Verify HMAC-SHA256 signature
      │
      ▼
Background task queued  ──► Return 200 immediately
      │
      ▼
Fetch PR diff (GitHub API)
      │
      ▼
Send diff to LLM (OpenRouter)
      │
      ▼
Store structured feedback (PostgreSQL/Supabase)
      │
      ▼
Post formatted comment to PR
```

Feedback is categorized across four dimensions — **bugs**, **security**, **performance**, and **style** — grouped by file and formatted as markdown tables in the PR comment.

---

## Tech Stack

| Layer            | Choice                                       | Why                                                                   |
| ---------------- | -------------------------------------------- | --------------------------------------------------------------------- |
| Framework        | FastAPI                                      | Async-native; handles concurrent outbound HTTP calls without blocking |
| Database         | PostgreSQL (Supabase) + SQLAlchemy + asyncpg | Async ORM stack; JSONB for flexible feedback storage                  |
| Validation       | Pydantic / pydantic-settings                 | Type-safe config; fails loudly on missing env vars                    |
| LLM Proxy        | OpenRouter                                   | Single API key, swap models without code changes                      |
| Containerization | Docker                                       | Reproducible builds; non-root user; layer-cached dependency installs  |
| CI               | GitHub Actions + Ruff + Pytest               | Lint and test on every push and PR                                    |
| Hosting          | Render                                       | Pulls Dockerfile, manages TLS, provides public URL                    |

---

## Key Design Decisions

**Webhook security via HMAC-SHA256** — Every incoming request is verified against GitHub's signature header using `hmac.compare_digest` (constant-time comparison to prevent timing attacks). Signature is verified against the raw request bytes before JSON parsing.

**Idempotency via `gh_delivery_id`** — GitHub retries failed deliveries. A `UNIQUE` constraint on the delivery ID column in PostgreSQL ensures each event is processed exactly once, even if two requests race simultaneously.

**Immediate response, background processing** — The `/webhook` endpoint returns `200 OK` before any analysis work begins. GitHub has delivery timeouts; doing the work inline risks missed deliveries. FastAPI's `BackgroundTasks` handles the processing after the response is sent.

**Structured error handling** — Three distinct failure modes are handled separately: analysis failure (stores `status=error`), database failure (best-effort error record), and comment posting failure (preserves `status=completed`, records the comment error). Analysis data is never lost due to a comment delivery failure.

**`expire_on_commit=False`** — Prevents SQLAlchemy from attempting implicit lazy-loads after commit in an async context, where there is no implicit async context to run them in.

---

## API

Authentication for retrieval endpoints uses an `X-API-Key` header. The webhook endpoint uses HMAC verification instead — GitHub controls the headers it sends.

| Method | Path             | Auth        | Description                                          |
| ------ | ---------------- | ----------- | ---------------------------------------------------- |
| `POST` | `/webhook`       | HMAC-SHA256 | Receive GitHub webhook events                        |
| `GET`  | `/analyses`      | API Key     | List analyses with optional filtering and pagination |
| `GET`  | `/analyses/{id}` | API Key     | Retrieve a single analysis result                    |

**Query parameters for `GET /analyses`:**

- `repo_full_name` — filter by repository (e.g. `owner/repo`)
- `pr_number` — filter by PR number
- `limit` / `offset` — pagination (default: 20/0, ordered by `created_at` desc)

---

## Running Locally

**Prerequisites:** Docker, or Python 3.12+ with a PostgreSQL instance.

```bash
git clone https://github.com/your-username/prism-backend
cd prism-backend
cp .env.example .env
# Fill in DATABASE_URL, WEBHOOK_SECRET, PRISM_API_KEY, OPENROUTER_API_KEY
```

**With Docker:**

```bash
docker build -t prism .
docker run --env-file .env -p 8000:8000 prism
```

**Without Docker:**

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

To receive webhooks locally, use [ngrok](https://ngrok.com/) or [smee.io](https://smee.io/) to tunnel to `localhost:8000/webhook`.

---

## Environment Variables

| Variable             | Description                                                   |
| -------------------- | ------------------------------------------------------------- |
| `DATABASE_URL`       | PostgreSQL connection string (`postgresql+asyncpg://...`)     |
| `WEBHOOK_SECRET`     | Secret set in GitHub webhook configuration                    |
| `PRISM_API_KEY`      | Key required to call the retrieval endpoints                  |
| `OPENROUTER_API_KEY` | API key for OpenRouter                                        |
| `GITHUB_TOKEN`       | Personal access token for fetching diffs and posting comments |

---

## Known Limitations

- **No task queue** — Background tasks run in-process. If the server restarts mid-analysis, the task is lost. A production system would use ARQ or Celery with a Redis broker.
- **No rate limiting** — A high volume of webhook deliveries would each trigger an LLM call. `slowapi` or a reverse proxy rule would address this.
- **Single-tenant** — One GitHub account, one API key. No multi-user or multi-repo registration.

---

## Project Structure

```
prism-backend/
├── app/
│   ├── main.py          # FastAPI app, route definitions
│   ├── config.py        # Pydantic BaseSettings
│   ├── models.py        # SQLAlchemy ORM models
│   ├── schemas.py       # Pydantic request/response schemas
│   ├── dependencies.py  # FastAPI dependencies (auth, db session)
│   ├── services/
│   │   ├── analysis.py  # Core run_analysis logic
│   │   ├── github.py    # GitHub API client
│   │   └── llm.py       # OpenRouter client
│   └── database.py      # Async engine and session setup
├── tests/
├── Dockerfile
├── .github/workflows/ci.yml
└── requirements.txt
```

---

## CI

GitHub Actions runs on every push to `main` and every PR targeting `main`:

1. **Ruff** — linting and formatting checks
2. **Pytest** — test suite with required environment variables injected from repository secrets

Both jobs must pass for a PR to be mergeable.
