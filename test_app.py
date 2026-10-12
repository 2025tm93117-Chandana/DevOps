from datetime import date, timedelta

import pytest

from app import PROGRAM_TEMPLATES, __version__, bmi_category, create_app


@pytest.fixture
def client(tmp_path):
    app = create_app({"DATABASE": str(tmp_path / "test.db"), "TESTING": True})
    return app.test_client()


@pytest.fixture
def bob(client):
    client.post("/clients", json={"name": "Bob", "age": 30, "weight": 80.5})
    return "Bob"


# ---------- General ----------
def test_dashboard_served_at_root(client):
    res = client.get("/")
    assert res.status_code == 200
    assert res.mimetype == "text/html"
    assert b"ACEest" in res.data


@pytest.mark.parametrize("path", ["/static/app.js", "/static/style.css"])
def test_static_assets_served(client, path):
    assert client.get(path).status_code == 200


def test_dashboard_has_summary_and_search_but_no_empty_message(client):
    html = client.get("/").data
    assert b'id="summary"' in html
    assert b'id="client-search"' in html
    assert b"Select or add a client" not in html


# ---------- Stats ----------
def test_stats_empty(client):
    assert client.get("/stats").get_json() == {
        "total_clients": 0,
        "active_members": 0,
        "expired_members": 0,
        "total_workouts": 0,
        "total_minutes": 0,
        "avg_adherence": None,
    }


def test_stats_with_data(client):
    future = (date.today() + timedelta(days=30)).isoformat()
    past = (date.today() - timedelta(days=1)).isoformat()
    client.post("/clients", json={"name": "Active", "membership_end": future})
    client.post("/clients", json={"name": "Lapsed", "membership_end": past})
    client.post("/clients", json={"name": "Gone", "membership_status": "Expired"})
    client.post("/clients", json={"name": "Paused", "membership_status": "Inactive"})
    client.post("/clients/Active/workouts", json={"workout_type": "Cardio", "duration_min": 30})
    client.post("/clients/Active/workouts", json={"workout_type": "Strength", "duration_min": 45})
    client.post("/clients/Active/progress", json={"week": "W1", "adherence": 80})
    client.post("/clients/Lapsed/progress", json={"week": "W1", "adherence": 71})

    stats = client.get("/stats").get_json()
    assert stats["total_clients"] == 4
    assert stats["active_members"] == 1
    assert stats["expired_members"] == 2
    assert stats["total_workouts"] == 2
    assert stats["total_minutes"] == 75
    assert stats["avg_adherence"] == 75.5


def test_stats_updates_after_delete(client, bob):
    client.post(f"/clients/{bob}/workouts", json={"workout_type": "Cardio", "duration_min": 20})
    client.delete(f"/clients/{bob}")
    stats = client.get("/stats").get_json()
    assert stats["total_clients"] == 0
    assert stats["total_workouts"] == 0


def test_api_index_lists_endpoints(client):
    res = client.get("/api")
    assert res.status_code == 200
    assert "endpoints" in res.get_json()


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json() == {"status": "ok"}


def test_version(client):
    res = client.get("/version")
    assert res.status_code == 200
    assert res.get_json() == {"version": __version__}


def test_programs(client):
    assert client.get("/programs").get_json() == PROGRAM_TEMPLATES


def test_unknown_route_returns_json_404(client):
    res = client.get("/nope")
    assert res.status_code == 404
    assert res.get_json()["error"] == "Not found"


def test_method_not_allowed(client):
    assert client.patch("/health").status_code == 405


# ---------- Clients ----------
def test_create_and_get_client(client):
    res = client.post("/clients", json={"name": " Alice ", "age": 25, "height": 170})
    assert res.status_code == 201
    body = res.get_json()
    assert body["name"] == "Alice"
    assert body["membership_status"] == "Active"
    assert client.get("/clients/Alice").get_json()["age"] == 25


def test_list_clients_sorted(client):
    for name in ("Zed", "Amy"):
        client.post("/clients", json={"name": name})
    assert [c["name"] for c in client.get("/clients").get_json()] == ["Amy", "Zed"]


def test_create_duplicate_client_conflicts(client, bob):
    assert client.post("/clients", json={"name": bob}).status_code == 409


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"name": "  "},
        {"name": 5},
        {"name": "X", "age": "abc"},
        {"name": "X", "age": -1},
        {"name": "X", "age": True},
        {"name": "X", "target_adherence": 101},
        {"name": "X", "membership_status": "Banned"},
        {"name": "X", "membership_end": "31-12-2026"},
    ],
)
def test_create_client_validation(client, payload):
    assert client.post("/clients", json=payload).status_code == 400


def test_create_client_requires_json_object(client):
    res = client.post("/clients", data="not json", content_type="text/plain")
    assert res.status_code == 400


def test_get_missing_client(client):
    assert client.get("/clients/Ghost").status_code == 404


def test_update_client(client, bob):
    res = client.put(f"/clients/{bob}", json={"weight": 75, "membership_status": "Inactive"})
    assert res.status_code == 200
    body = res.get_json()
    assert body["weight"] == 75
    assert body["membership_status"] == "Inactive"
    assert body["age"] == 30


def test_update_client_validation_and_missing(client, bob):
    assert client.put(f"/clients/{bob}", json={"age": -5}).status_code == 400
    assert client.put("/clients/Ghost", json={"age": 5}).status_code == 404


def test_delete_client_removes_related_data(client, bob):
    client.post(f"/clients/{bob}/workouts", json={"workout_type": "Cardio", "duration_min": 30})
    client.post(f"/clients/{bob}/progress", json={"week": "W1", "adherence": 80})
    assert client.delete(f"/clients/{bob}").status_code == 204
    assert client.get(f"/clients/{bob}").status_code == 404
    client.post("/clients", json={"name": bob})
    assert client.get(f"/clients/{bob}/workouts").get_json() == []
    assert client.get(f"/clients/{bob}/progress").get_json() == []


def test_delete_missing_client(client):
    assert client.delete("/clients/Ghost").status_code == 404


# ---------- Program generator ----------
def test_generate_program_persists(client, bob):
    res = client.post(f"/clients/{bob}/program")
    assert res.status_code == 200
    body = res.get_json()
    assert body["program"] in PROGRAM_TEMPLATES[body["category"]]
    assert client.get(f"/clients/{bob}").get_json()["program"] == body["program"]


def test_generate_program_missing_client(client):
    assert client.post("/clients/Ghost/program").status_code == 404


# ---------- Membership ----------
def test_membership_active_without_end_date(client, bob):
    body = client.get(f"/clients/{bob}/membership").get_json()
    assert body["status"] == "Active"
    assert body["renewal_date"] is None


def test_membership_future_end_date_stays_active(client, bob):
    end = (date.today() + timedelta(days=30)).isoformat()
    client.put(f"/clients/{bob}", json={"membership_end": end})
    body = client.get(f"/clients/{bob}/membership").get_json()
    assert body["status"] == "Active"
    assert body["renewal_date"] == end


def test_membership_past_end_date_is_expired(client, bob):
    end = (date.today() - timedelta(days=1)).isoformat()
    client.put(f"/clients/{bob}", json={"membership_end": end})
    assert client.get(f"/clients/{bob}/membership").get_json()["status"] == "Expired"


def test_membership_missing_client(client):
    assert client.get("/clients/Ghost/membership").status_code == 404


# ---------- Summary ----------
@pytest.mark.parametrize(
    "bmi, expected",
    [(17.0, "Underweight"), (18.5, "Normal"), (24.9, "Normal"), (25.0, "Overweight"), (29.9, "Overweight"), (30.0, "Obese")],
)
def test_bmi_category_boundaries(bmi, expected):
    assert bmi_category(bmi) == expected


def test_summary_without_data(client):
    client.post("/clients", json={"name": "Empty"})
    assert client.get("/clients/Empty/summary").get_json() == {
        "client": "Empty",
        "bmi": None,
        "bmi_category": None,
        "workout_count": 0,
        "total_minutes": 0,
        "last_workout": None,
        "avg_adherence": None,
        "target_adherence": None,
        "on_target": None,
    }


def test_summary_with_data(client):
    client.post("/clients", json={"name": "Dana", "height": 180, "weight": 81, "target_adherence": 80})
    for day, minutes in (("2026-03-01", 30), ("2026-03-05", 45)):
        client.post("/clients/Dana/workouts", json={"date": day, "workout_type": "Cardio", "duration_min": minutes})
    for week, value in (("W1", 70), ("W2", 95)):
        client.post("/clients/Dana/progress", json={"week": week, "adherence": value})

    body = client.get("/clients/Dana/summary").get_json()
    assert body["bmi"] == 25.0
    assert body["bmi_category"] == "Overweight"
    assert body["workout_count"] == 2
    assert body["total_minutes"] == 75
    assert body["last_workout"] == "2026-03-05"
    assert body["avg_adherence"] == 82.5
    assert body["on_target"] is True


def test_summary_below_target(client):
    client.post("/clients", json={"name": "Eli", "target_adherence": 90})
    client.post("/clients/Eli/progress", json={"week": "W1", "adherence": 60})
    assert client.get("/clients/Eli/summary").get_json()["on_target"] is False


def test_summary_only_counts_own_data(client, bob):
    client.post("/clients", json={"name": "Other"})
    client.post("/clients/Other/workouts", json={"workout_type": "Cardio", "duration_min": 50})
    assert client.get(f"/clients/{bob}/summary").get_json()["workout_count"] == 0


def test_summary_missing_client(client):
    assert client.get("/clients/Ghost/summary").status_code == 404


# ---------- Workouts ----------
def test_add_and_list_workouts_newest_first(client, bob):
    for day in ("2026-01-01", "2026-02-01"):
        res = client.post(
            f"/clients/{bob}/workouts",
            json={"date": day, "workout_type": "Strength", "duration_min": 60, "notes": "ok"},
        )
        assert res.status_code == 201
    rows = client.get(f"/clients/{bob}/workouts").get_json()
    assert [r["date"] for r in rows] == ["2026-02-01", "2026-01-01"]


def test_workout_date_defaults_to_today(client, bob):
    res = client.post(f"/clients/{bob}/workouts", json={"workout_type": "Cardio", "duration_min": 20})
    assert res.get_json()["date"] == date.today().isoformat()


@pytest.mark.parametrize(
    "payload",
    [
        {"duration_min": 30},
        {"workout_type": "Yoga", "duration_min": 30},
        {"workout_type": "Cardio"},
        {"workout_type": "Cardio", "duration_min": 0},
        {"workout_type": "Cardio", "duration_min": 30, "date": "yesterday"},
    ],
)
def test_add_workout_validation(client, bob, payload):
    assert client.post(f"/clients/{bob}/workouts", json=payload).status_code == 400


def test_workouts_missing_client(client):
    assert client.get("/clients/Ghost/workouts").status_code == 404
    res = client.post("/clients/Ghost/workouts", json={"workout_type": "Cardio", "duration_min": 5})
    assert res.status_code == 404


# ---------- Progress ----------
def test_add_and_list_progress_in_order(client, bob):
    for week, value in (("W1", 70), ("W2", 85)):
        assert client.post(f"/clients/{bob}/progress", json={"week": week, "adherence": value}).status_code == 201
    rows = client.get(f"/clients/{bob}/progress").get_json()
    assert [(r["week"], r["adherence"]) for r in rows] == [("W1", 70), ("W2", 85)]


@pytest.mark.parametrize(
    "payload",
    [
        {"adherence": 50},
        {"week": " ", "adherence": 50},
        {"week": "W1"},
        {"week": "W1", "adherence": 101},
        {"week": "W1", "adherence": -1},
        {"week": "W1", "adherence": "high"},
    ],
)
def test_add_progress_validation(client, bob, payload):
    assert client.post(f"/clients/{bob}/progress", json=payload).status_code == 400


def test_progress_missing_client(client):
    assert client.get("/clients/Ghost/progress").status_code == 404
