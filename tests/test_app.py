import asyncio
from copy import deepcopy

import httpx
import pytest

from src import app as app_module


@pytest.fixture(autouse=True)
def restore_activities():
    original_activities = deepcopy(app_module.activities)
    yield
    app_module.activities.clear()
    app_module.activities.update(original_activities)


def request(method, url, **kwargs):
    async def make_request():
        transport = httpx.ASGITransport(app=app_module.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, url, **kwargs)

    return asyncio.run(make_request())


def test_root_redirects_to_static_index():
    # Arrange
    expected_location = "/static/index.html"

    # Act
    response = request("GET", "/", follow_redirects=False)

    # Assert
    assert response.status_code == 307
    assert response.headers["location"] == expected_location


def test_static_index_is_available():
    # Arrange
    expected_content = "Mergington High School"

    # Act
    response = request("GET", "/static/index.html")

    # Assert
    assert response.status_code == 200
    assert expected_content in response.text


def test_get_activities_returns_seeded_activity_data():
    # Arrange
    expected_activity = "Chess Club"

    # Act
    response = request("GET", "/activities")

    # Assert
    assert response.status_code == 200
    activity = response.json()[expected_activity]
    assert activity["description"]
    assert activity["schedule"]
    assert activity["max_participants"] == 12
    assert "michael@mergington.edu" in activity["participants"]


def test_signup_adds_participant():
    # Arrange
    activity_name = "Soccer Club"
    email = "student@example.com"

    # Act
    response = request(
        "POST",
        f"/activities/{activity_name}/signup",
        params={"email": email},
    )

    # Assert
    assert response.status_code == 200
    assert response.json() == {
        "message": f"Signed up {email} for {activity_name}"
    }
    assert email in app_module.activities[activity_name]["participants"]


def test_duplicate_signup_returns_bad_request():
    # Arrange
    activity_name = "Chess Club"
    email = "michael@mergington.edu"

    # Act
    response = request(
        "POST",
        f"/activities/{activity_name}/signup",
        params={"email": email},
    )

    # Assert
    assert response.status_code == 400
    assert response.json()["detail"] == "Student already signed up for this activity"


def test_signup_for_unknown_activity_returns_not_found():
    # Arrange
    activity_name = "Robotics Club"

    # Act
    response = request(
        "POST",
        f"/activities/{activity_name}/signup",
        params={"email": "student@example.com"},
    )

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_signup_without_email_returns_validation_error():
    # Arrange
    activity_name = "Soccer Club"

    # Act
    response = request("POST", f"/activities/{activity_name}/signup")

    # Assert
    assert response.status_code == 422


def test_unregister_removes_participant():
    # Arrange
    activity_name = "Chess Club"
    email = "michael@mergington.edu"

    # Act
    response = request(
        "DELETE",
        f"/activities/{activity_name}/signup",
        params={"email": email},
    )

    # Assert
    assert response.status_code == 200
    assert response.json() == {
        "message": f"Unregistered {email} from {activity_name}"
    }
    assert email not in app_module.activities[activity_name]["participants"]


def test_unregister_from_unknown_activity_returns_not_found():
    # Arrange
    activity_name = "Robotics Club"

    # Act
    response = request(
        "DELETE",
        f"/activities/{activity_name}/signup",
        params={"email": "student@example.com"},
    )

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_unregister_non_enrolled_participant_returns_not_found():
    # Arrange
    activity_name = "Soccer Club"
    email = "student@example.com"

    # Act
    response = request(
        "DELETE",
        f"/activities/{activity_name}/signup",
        params={"email": email},
    )

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Student is not signed up for this activity"