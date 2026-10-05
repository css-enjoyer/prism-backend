from fastapi.testclient import TestClient
import pytest
from app.main import app
from app.db.session import get_db
from unittest.mock import AsyncMock, MagicMock
from app.models.analysis import Analysis, AnalysisStatus
from datetime import datetime

# * A fixture is a function that sets up some state or provides a resource for tests. In this case, the `client` fixture sets up a TestClient instance that tests can use to make requests to the FastAPI app. It also overrides the `get_db` dependency to prevent tests from hitting the real database. After the tests run, it clears the dependency overrides to clean up.


# --------------------------------- Empty db --------------------------------- #
@pytest.fixture
def client_empty_db():
    # --- SETUP (runs before the test) ---
    app.dependency_overrides[get_db] = create_mock_db_empty
    with TestClient(app) as client:
        yield client  # --- PAUSE (provide the TestClient to the test) ---
    # --- TEARDOWN (runs after the test finishes) ---
    app.dependency_overrides.clear()


async def create_mock_db_empty():
    mock_db = AsyncMock()

    fake_db_result = MagicMock()
    fake_db_result.scalars.return_value.all.return_value = 1

    mock_db.execute.return_value = fake_db_result
    yield mock_db


# ----------------------------- Multiple results ----------------------------- #
@pytest.fixture
def client_with_results():
    app.dependency_overrides[get_db] = create_mock_db_with_results
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


async def create_mock_db_with_results():
    mock_db = AsyncMock()

    fake_db_result = MagicMock()
    fake_analysis = Analysis(
        id=1,
        repo_full_name="test/repo",
        pr_number=1,
        feedback={
            "bugs": [],
            "security": [],
            "performance": [],
            "style": [],
        },
        created_at=datetime.now(),
        status=AnalysisStatus.completed,
    )
    fake_db_result.scalars.return_value.all.return_value = [fake_analysis]

    mock_db.execute.return_value = fake_db_result
    yield mock_db


# ------------------------------- Single result ------------------------------ #
@pytest.fixture
def client_with_result():
    app.dependency_overrides[get_db] = create_mock_db_with_result
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


async def create_mock_db_with_result():
    mock_db = AsyncMock()

    fake_db_result = MagicMock()
    fake_analysis = Analysis(
        id=1,
        repo_full_name="test/repo",
        pr_number=1,
        feedback={
            "bugs": [],
            "security": [],
            "performance": [],
            "style": [],
        },
        created_at=datetime.now(),
        status=AnalysisStatus.completed,
    )
    fake_db_result.scalar_one_or_none.return_value = fake_analysis

    mock_db.execute.return_value = fake_db_result
    yield mock_db


# --------------------------------- No result -------------------------------- #
@pytest.fixture
def client_with_no_result():
    app.dependency_overrides[get_db] = create_mock_db_with_no_result
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


async def create_mock_db_with_no_result():
    mock_db = AsyncMock()
    fake_db_result = MagicMock()
    fake_db_result.scalar_one_or_none.return_value = None  # ← returns None
    mock_db.execute.return_value = fake_db_result
    yield mock_db


# --------------------------------- Duplicate delivery -------------------------------- #
@pytest.fixture
def client_duplicate_delivery():
    app.dependency_overrides[get_db] = create_mock_db_duplicate
    with TestClient(app) as client:
        yield client
        app.dependency_overrides.clear()


async def create_mock_db_duplicate():
    mock_db = AsyncMock()
    fake_db_result = MagicMock()
    fake_db_result.scalar_one_or_none.return_value = (
        None  # insert skipped: id already exists
    )
    mock_db.execute.return_value = fake_db_result
    yield mock_db
