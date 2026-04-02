import httpx
from openai import AsyncOpenAI
from app.config import settings
import json
import re
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from ..models import Analysis

SYSTEM_PROMPT = """You are a senior software engineer performing a code review. Analyze the provided git diff and identify issues across exactly four categories.

Return ONLY a JSON object in this exact structure, no markdown, no explanation:

{
  "bugs": [
    {"line": "<line number or range>", "description": "<what the bug is and why it's wrong>", "suggestion": "<how to fix it>"}
  ],
  "security": [
    {"line": "<line number or range>", "description": "<what the vulnerability is>", "suggestion": "<how to fix it>"}
  ],
  "performance": [
    {"line": "<line number or range>", "description": "<what the issue is>", "suggestion": "<how to improve it>"}
  ],
  "style": [
    {"line": "<line number or range>", "description": "<what the issue is>", "suggestion": "<how to improve it>"}
  ]
}

Each array may be empty if no issues are found in that category. Do not include any text outside the JSON object."""

client = AsyncOpenAI(
    api_key=settings.openrouter_api_key,
    base_url=settings.openrouter_base_url,
)


# This function will be called in the background after receiving the webhook, so we can take our time to analyze the diff without worrying about Github's 10 second timeout. The diff will be passed as a string and we will return the analysis as a dict.
async def review_diff(diff: str) -> dict:
    response = await client.chat.completions.create(
        model=settings.openrouter_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": diff},
        ],
    )
    result = response.choices[0].message.content
    result = re.sub(r"^```json\s*|\s*```$", "", result.strip())
    return json.loads(result)


async def run_analysis(repo_full_name: str, pr_number: int, gh_delivery_id: str):
    api_url = f"https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}"

    # Fetch diff from url using httpx
    async with httpx.AsyncClient() as client:
        response = await client.get(
            api_url,
            headers={
                "Authorization": f"Bearer {settings.github_token}",
                "Accept": "application/vnd.github.v3.diff",
            },
        )
        diff = response.text
        print(f"URL: {api_url}")
        print(f"TOKEN PREFIX: {settings.github_token[:10]}")
        print(f"STATUS: {response.status_code}")
        print(f"DIFF CONTENT:\n{diff[:500]}")

    feedback = await review_diff(diff)

    # AsyncSessionLocal is the session factory. Outside of FastAPI's dependency injection cycle (e.g. in background tasks), we use it directly as an async context manager to manually manage the session lifecycle.
    async with AsyncSessionLocal() as session:
        # Idempotency check: if an analysis with the same gh_delivery_id already exists, we skip processing to avoid duplicates in case of webhook retries. This is important because Github may resend the same webhook multiple times if it doesn't receive a timely response, and we don't want to create multiple analyses for the same PR event.
        existing = await session.execute(
            select(Analysis).where(Analysis.gh_delivery_id == gh_delivery_id)
        )
        if existing.scalar_one_or_none():
            return

        # Save results to database
        analysis = Analysis(
            repo_full_name=repo_full_name,
            pr_number=pr_number,
            gh_delivery_id=gh_delivery_id,
            feedback=feedback,
        )

        # TODO: Log failed analysis and save to database.
        session.add(analysis)
        await session.commit()

        prCommentUrl = (
            f"https://api.github.com/repos/{repo_full_name}/issues/{pr_number}/comments"
        )
        lines = []
        lines.append("## Bugs")
        for issue in feedback["bugs"]:
            lines.append(f"- **Line {issue['line']}**: {issue['description']}")
            lines.append(f"  - Suggestion: {issue['suggestion']}")
        comment_body = "\n".join(lines)

        # Post review to pull request
        async with httpx.AsyncClient() as client:
            await client.post(
                prCommentUrl,
                headers={"Authorization": f"Bearer {settings.github_token}"},
                json={"body": comment_body},
            )
