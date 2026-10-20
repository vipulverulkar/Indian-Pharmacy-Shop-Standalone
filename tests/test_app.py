import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

os.environ["DATABASE_URL"] = (
    f"sqlite:///{tempfile.mkdtemp(prefix='pharmacy-test-')}/test.db"
)
os.environ.setdefault("ADMIN_USER", "admin")
os.environ.setdefault("ADMIN_PASS", "admin")

import app as pharmacy  # noqa: E402
from migrations import migrate  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def database():
    migrate(pharmacy.engine, pharmacy.ADMIN_USER, pharmacy.ADMIN_PASS)


@pytest.fixture()
def client():
    pharmacy.app.config.update(TESTING=True)
    with pharmacy.app.test_client() as test_client:
        yield test_client


def auth_headers(client):
    res = client.post(
        "/api/login", json={"username": pharmacy.ADMIN_USER, "password": pharmacy.ADMIN_PASS}
    )
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.get_json()['token']}"}


def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.get_json() == {"status": "ok", "currency": "INR"}


def test_frontend_or_api_hint_is_served(client):
    res = client.get("/")
    assert res.status_code == 200
    if b'id="root"' not in res.data:
        assert b"/api/health" in res.data


def test_login_rejects_bad_password(client):
    res = client.post("/api/login", json={"username": "admin", "password": "wrong"})
    assert res.status_code == 401


def test_session_and_logout(client):
    headers = auth_headers(client)
    assert client.get("/api/me", headers=headers).get_json()["username"] == "admin"
    assert client.post("/api/logout", headers=headers).status_code == 200
    assert client.get("/api/me", headers=headers).status_code == 401


def test_bill_flow_and_stock(client):
    headers = auth_headers(client)

    res = client.get("/api/medicines?page=1&per_page=5", headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["total"] > 5
    medicine = data["medicines"][0]
    before = int(medicine["quantity"])
    assert before > 0

    res = client.post(
        "/api/bills",
        headers=headers,
        json={
            "customer_name": "Test Customer",
            "customer_phone": "9000000000",
            "payment_mode": "Cash",
            "discount_percent": 5,
            "items": [{"medicine_id": medicine["id"], "qty": 1}],
        },
    )
    assert res.status_code == 201
    bill = res.get_json()
    assert bill["items"][0]["qty"] == 1

    res = client.get(
        "/api/medicines",
        query_string={"page": 1, "per_page": 100, "search": medicine["name"]},
        headers=headers,
    )
    after = next(m for m in res.get_json()["medicines"] if m["id"] == medicine["id"])
    assert int(after["quantity"]) == before - 1

    res = client.post(f"/api/bills/{bill['id']}/return", headers=headers)
    assert res.status_code == 200
    assert res.get_json()["status"] == "returned"

    res = client.get(
        "/api/medicines",
        query_string={"page": 1, "per_page": 100, "search": medicine["name"]},
        headers=headers,
    )
    restored = next(m for m in res.get_json()["medicines"] if m["id"] == medicine["id"])
    assert int(restored["quantity"]) == before


def test_dashboard_and_reports(client):
    headers = auth_headers(client)
    dashboard = client.get("/api/dashboard", headers=headers)
    assert dashboard.status_code == 200
    assert "today_sales" in dashboard.get_json()

    report = client.get("/api/reports/sales?days=7", headers=headers)
    assert report.status_code == 200
    assert len(report.get_json()["daily"]) == 7


def test_store_settings(client):
    res = client.get("/api/settings")
    assert res.status_code == 200
    assert res.get_json()["name"]
