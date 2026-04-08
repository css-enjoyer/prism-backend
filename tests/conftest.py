from fastapi.testclient import TestClient
import pytest
from app.main import app
from app.db.session import get_db


async def get_db_fake():
    yield None  # Return None or a mock session for testing purposes


# * A fixture is a function that sets up some state or provides a resource for tests. In this case, the `client` fixture sets up a TestClient instance that tests can use to make requests to the FastAPI app. It also overrides the `get_db` dependency to prevent tests from hitting the real database. After the tests run, it clears the dependency overrides to clean up.
@pytest.fixture
def client():
    # --- SETUP (runs before the test) ---
    app.dependency_overrides[get_db] = get_db_fake
    with TestClient(app) as client:
        yield client  # --- PAUSE (provide the TestClient to the test) ---
    # --- TEARDOWN (runs after the test finishes) ---
    app.dependency_overrides.clear()


# Create a test version of the FastAPI app
# Override the database dependency so tests don't hit your real Supabase database
# Provide a TestClient instance that tests can use to make requests
# app.dependency_overrides[original_dependency] = replacement_dependency
