#
# * This test file focuses on the /analyses endpoint and related endpoints, which is the main interface for clients to retrieve analysis results and submit review diffs. The tests cover various scenarios related to authentication, filtering, pagination, and error handling.

from app.config import settings


# ----------------------------------- Auth ----------------------------------- #
# 1. No API key header - 422
def test_no_api_key_header(client_empty_db):
    # Arrange: no API key header
    headers = {}
    # Act: GET /analyses without API key
    response = client_empty_db.get("/analyses", headers=headers)
    # Assert: 422 Unprocessable Entity
    assert response.status_code == 422


# 2. Wrong API key - 401
def test_wrong_api_key(client_empty_db):
    # Arrange: API key header with wrong value
    headers = {"X-API-Key": "wrongkey"}
    # Act: GET /analyses with wrong API key
    response = client_empty_db.get("/analyses", headers=headers)
    # Assert: 401 Unauthorized
    assert response.status_code == 401


# ------------------------------- GET /analyses ------------------------------ #
# 3. Valid key, no filters - 200, returns list
def test_valid_key_no_filters(client_empty_db):
    # Arrange: API key header with correct value
    headers = {"X-API-Key": settings.prism_api_key}
    # Act: GET /analyses with valid API key and no filters
    response = client_empty_db.get("/analyses", headers=headers)
    # Assert: 200 OK and response is a list (could be empty)
    assert response.status_code == 200


# 4. Valid key, filter by repo_full_name - 200
def test_valid_key_filter_by_repo_full_name(client_with_results):
    # Arrange: API key header with correct value and filter by repo_full_name
    headers = {"X-API-Key": settings.prism_api_key}
    params = {"repo_full_name": "test/repo"}
    # Act: GET /analyses with valid API key and repo_full_name filter
    response = client_with_results.get("/analyses", headers=headers, params=params)
    # Assert: 200 OK and correct response repo name
    assert response.status_code == 200

    data = response.json()
    assert data[0]["repo_full_name"] == "test/repo"


# 5. Valid key, filter by pr_number - 200
def test_valid_key_filter_by_pr_number(client_with_results):
    # Arrange: API key header with correct value and filter by repo_full_name
    headers = {"X-API-Key": settings.prism_api_key}
    params = {"repo_full_name": "owner/repo", "pr_number": "1"}

    # Act: Get /analyses
    response = client_with_results.get("analyses", headers=headers, params=params)

    # Assert: 200 OK and correct response pr_number
    assert response.status_code == 200

    data = response.json()
    assert data[0]["pr_number"] == 1


# 6. limit out of range (0 or 101) - 422
def test_limit_out_of_range(client_empty_db):
    # Arrange
    headers = {"X-API-Key": settings.prism_api_key}
    params = {"limit": 0}  # Invalid: must be >= 1 (ge=1)

    # Act
    response = client_empty_db.get("/analyses", headers=headers, params=params)

    # Assert
    assert response.status_code == 422


# 7. offset negative - 422
def test_offset_negative(client_empty_db):
    # Arrange
    headers = {"X-API-Key": settings.prism_api_key}
    params = {"offset": -1}  # Invalid: must be >= 0 (ge=0)

    # Act
    response = client_empty_db.get("/analyses", headers=headers, params=params)

    # Assert
    assert response.status_code == 422


# ---------------------------- GET /analyses/{id} ---------------------------- #
# 8. ID exists - 200, returns analysis
def test_id_exists(client_with_result):
    # Arrange
    headers = {"X-API-Key": settings.prism_api_key}

    # Act
    response = client_with_result.get("/analyses/1", headers=headers)

    # Assert
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == 1


# 9. ID does not exist - 404
def test_id_does_not_exist(client_with_no_result):
    # Arrange
    headers = {"X-API-Key": settings.prism_api_key}

    # Act
    response = client_with_no_result.get("/analyses/2", headers=headers)

    # Assert
    assert response.status_code == 404


# ----------------------------- POST /review-diff ---------------------------- #
# ? Not sure if needed, code reviews are tied with github prs
# 10. No API key - 422
def test_no_api_key(client_empty_db):
    pass


# 11. Valid key - 200
def test_valid_key(client_empty_db):
    pass
