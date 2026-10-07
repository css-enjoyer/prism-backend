import asyncio
from unittest.mock import AsyncMock

from app.services import analysis as svc


def patch_steps(monkeypatch, **overrides):
    """Replace every step with a fake. Returns the dict of fakes so tests can inspect them."""
    fakes = {
        "fetch_diff": AsyncMock(return_value="diff text"),
        "review_diff": AsyncMock(return_value={"bugs": []}),
        "_save_feedback": AsyncMock(),
        "post_pr_comment": AsyncMock(),
        "_mark_error": AsyncMock(),
        "_record_comment_error": AsyncMock(),
    }
    fakes.update(overrides)
    for name, fake in fakes.items():
        monkeypatch.setattr(f"app.services.analysis.{name}", fake)
    return fakes


def test_happy_path(monkeypatch):
    fakes = patch_steps(monkeypatch)
    asyncio.run(svc.run_analysis(1, "org/repo", 5))
    fakes["fetch_diff"].assert_awaited_once_with("org/repo", 5)
    fakes["_save_feedback"].assert_awaited_once()
    fakes["post_pr_comment"].assert_awaited_once()
    fakes["_mark_error"].assert_not_awaited()


def test_fetch_failure_marks_error_and_stops(monkeypatch):
    fakes = patch_steps(
        monkeypatch, fetch_diff=AsyncMock(side_effect=RuntimeError("boom"))
    )
    asyncio.run(svc.run_analysis(1, "org/repo", 5))
    fakes["_mark_error"].assert_awaited_once_with(1, "boom")
    fakes["review_diff"].assert_not_awaited()
    fakes["post_pr_comment"].assert_not_awaited()


def test_comment_failure_keeps_analysis_completed(monkeypatch):
    fakes = patch_steps(
        monkeypatch, post_pr_comment=AsyncMock(side_effect=RuntimeError("nope"))
    )
    asyncio.run(svc.run_analysis(1, "org/repo", 5))
    fakes["_save_feedback"].assert_awaited_once()
    fakes["_record_comment_error"].assert_awaited_once_with(1, "comment_error: nope")
    fakes["_mark_error"].assert_not_awaited()
