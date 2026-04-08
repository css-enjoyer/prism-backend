import httpx
from openai import AsyncOpenAI
from app.config import settings
import json
import re
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.analysis import AnalysisStatus
from ..models import Analysis

SYSTEM_PROMPT = """You are a senior software engineer performing a code review. Analyze the provided git diff and identify issues across exactly four categories.

Only report an issue if you are certain it is a problem based on the code shown in the diff. Do not speculate about code that is not shown. For each issue, provide a clear description of what the problem is and why it is an issue, along with a specific suggestion for how to fix it.

Return ONLY a JSON object in this exact structure, no markdown, no explanation:

{
    "bugs": [
        {"file": "<filename e.g. app/routers/webhook.py>", "line": "<line number or range>", "description": "<what the bug is and why it's wrong>", "suggestion": "<how to fix it>"}
    ],
    "security": [
        {"file": "<filename e.g. app/routers/webhook.py>", "line": "<line number or range>", "description": "<what the vulnerability is>", "suggestion": "<how to fix it>"}
    ],
    "performance": [
        {"file": "<filename e.g. app/routers/webhook.py>", "line": "<line number or range>", "description": "<what the issue is>", "suggestion": "<how to improve it>"}
    ],
    "style": [
        {"file": "<filename e.g. app/routers/webhook.py>", "line": "<line number or range>", "description": "<what the issue is>", "suggestion": "<how to improve it>"}
    ]
}

Each array may be empty if no issues are found in that category. Do not include any text outside the JSON object."""

EMPTY_FEEDBACK = {
    "bugs": [],
    "security": [],
    "performance": [],
    "style": [],
}

client = AsyncOpenAI(
    api_key=settings.openrouter_api_key,
    base_url=settings.openrouter_base_url,
)


async def run_analysis(repo_full_name: str, pr_number: int, gh_delivery_id: str):
    api_url = f"https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}"

    # 1. Fetch diff from url using httpx
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                api_url,
                headers={
                    "Authorization": f"Bearer {settings.github_token}",
                    "Accept": "application/vnd.github.v3.diff",
                },
            )
            response.raise_for_status()
            diff = response.text
        # 2. Analyze diff with LLM, normalize resulting feedback
        feedback = normalize_feedback(await review_diff(diff))
    except Exception as e:
        await _save_feedback_error(repo_full_name, pr_number, gh_delivery_id, e)
        return

    # 3. Save results to database
    try:
        # AsyncSessionLocal is the session factory. Outside of FastAPI's dependency injection cycle (e.g. in background tasks), we use it directly as an async context manager to manually manage the session lifecycle.
        async with AsyncSessionLocal() as session:
            # Idempotency check: if an analysis with the same gh_delivery_id already exists, we skip processing to avoid duplicates in case of webhook retries.
            existing = await session.execute(
                select(Analysis).where(Analysis.gh_delivery_id == gh_delivery_id)
            )
            if existing.scalar_one_or_none():
                return

            analysis = Analysis(
                repo_full_name=repo_full_name,
                pr_number=pr_number,
                gh_delivery_id=gh_delivery_id,
                feedback=feedback,
                status=AnalysisStatus.completed,
                error=None,
            )

            session.add(analysis)
            await session.commit()

    except Exception as e:
        await _save_feedback_error(repo_full_name, pr_number, gh_delivery_id, e)
        return

    # 4. Post feedback as a PR comment
    try:
        await post_pr_comment(repo_full_name, pr_number, feedback)
    except Exception as e:
        await _save_comment_error(repo_full_name, pr_number, gh_delivery_id, e)


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
    # print(f"RAW MODEL OUTPUT:\n{result}")
    try:
        return json.loads(result)
    except json.JSONDecodeError as e:
        print(f"Failed to parse model response: {e}\nRaw output: {result}")
        raise


async def post_pr_comment(repo_full_name: str, pr_number: int, feedback: dict):
    pr_comment_url = (
        f"https://api.github.com/repos/{repo_full_name}/issues/{pr_number}/comments"
    )

    # TODO: Post line-specific comments.
    # NOTE: Models are inconsistent with severity assessment, so for now severities are fixed to their categories, but in the future we may want to use the model's own severity assessment instead of hardcoding it here.
    category_config = {
        "bugs": ("🐛 Bugs", "🔴 Critical"),
        "security": ("🔒 Security", "🔴 Critical"),
        "performance": ("⚡ Performance", "🟡 Warning"),
        "style": ("📖 Style", "⚪ Nitpick"),
    }
    lines = ["## Prism Code Review\n"]

    has_issues = any(feedback.get(key) for key in category_config)
    if not has_issues:
        lines.append("✅ No issues found.")
    else:
        for key, (heading, severity) in category_config.items():
            issues = feedback.get(key, [])
            if not issues:
                continue
            lines.append(f"### {heading} — {severity}\n")

            # Group issues by file
            by_file = {}
            for issue in issues:
                file = issue.get("file", "unknown")
                by_file.setdefault(file, []).append(issue)

            for file, file_issues in by_file.items():
                lines.append(f"**`{file}`**\n")
                lines.append("| Line | Issue | Suggestion |")
                lines.append("|------|-------|------------|")
                for issue in file_issues:
                    line = issue["line"].replace("|", "\\|")
                    desc = issue["description"].replace("|", "\\|")
                    sugg = issue["suggestion"].replace("|", "\\|")
                    lines.append(f"| {line} | {desc} | {sugg} |")
                lines.append("")

    lines.append("\n---")
    lines.append("*Generated by [Prism](https://github.com/css-enjoyer/prism-backend)*")

    comment_body = "\n".join(lines)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            pr_comment_url,
            headers={"Authorization": f"Bearer {settings.github_token}"},
            json={"body": comment_body},
        )
        response.raise_for_status()


async def _save_feedback_error(
    repo_full_name: str,
    pr_number: int,
    gh_delivery_id: str,
    error: Exception,
):
    await _save_error(
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        gh_delivery_id=gh_delivery_id,
        error_message=str(error),
        preserve_existing_status=False,
    )


async def _save_comment_error(
    repo_full_name: str,
    pr_number: int,
    gh_delivery_id: str,
    error: Exception,
):
    await _save_error(
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        gh_delivery_id=gh_delivery_id,
        error_message=f"comment_error: {error}",
        preserve_existing_status=True,
    )


async def _save_error(
    repo_full_name: str,
    pr_number: int,
    gh_delivery_id: str,
    error_message: str,
    preserve_existing_status: bool,
):
    async with AsyncSessionLocal() as session:
        existing = await session.execute(
            select(Analysis).where(Analysis.gh_delivery_id == gh_delivery_id)
        )
        analysis = existing.scalar_one_or_none()

        if analysis is None:
            analysis = Analysis(
                repo_full_name=repo_full_name,
                pr_number=pr_number,
                gh_delivery_id=gh_delivery_id,
                feedback=EMPTY_FEEDBACK.copy(),
                status=AnalysisStatus.error,
                error=error_message,
            )
            session.add(analysis)
        else:
            if not preserve_existing_status:
                analysis.status = AnalysisStatus.error
            analysis.error = error_message

        await session.commit()


def normalize_feedback(feedback: dict | None) -> dict:
    # Ensure all expected keys are present and that feedback is in the correct format. This can help mitigate issues with model output inconsistencies.
    if not isinstance(feedback, dict):
        return EMPTY_FEEDBACK.copy()

    normalized = EMPTY_FEEDBACK.copy()
    for key in normalized:
        value = feedback.get(key, [])
        normalized[key] = value if isinstance(value, list) else []

    return normalized
