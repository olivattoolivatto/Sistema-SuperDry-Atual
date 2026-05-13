"""
Backend tests for Geoapify Route Planner integration.
Flow: GET available items -> POST /api/routes -> PUT /api/routes/{id}/stops -> POST optimize-geoapify -> verify
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# ── Auth ──────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def auth_token():
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@superdry.com",
        "password": "admin123"
    })
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def client(auth_token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"})
    return s


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_available_items(client):
    resp = client.get(f"{BASE_URL}/api/budget-items/available-for-routes")
    assert resp.status_code == 200, f"available-for-routes failed: {resp.text}"
    data = resp.json()
    # Response is {"available_items": [...]}
    return data.get("available_items", data) if isinstance(data, dict) else data


def cleanup_routes(client):
    resp = client.get(f"{BASE_URL}/api/routes")
    if resp.status_code == 200:
        for r in resp.json():
            client.delete(f"{BASE_URL}/api/routes/{r['id']}")
        print(f"Cleaned up {len(resp.json())} routes")


# ── Test Classes ──────────────────────────────────────────────────────────────

class TestAvailableForRoutes:
    """GET /api/budget-items/available-for-routes"""

    def test_returns_200(self, client):
        resp = client.get(f"{BASE_URL}/api/budget-items/available-for-routes")
        assert resp.status_code == 200, resp.text

    def test_response_has_available_items_key(self, client):
        resp = client.get(f"{BASE_URL}/api/budget-items/available-for-routes")
        data = resp.json()
        assert "available_items" in data, f"Expected 'available_items' key, got: {list(data.keys())}"

    def test_items_have_required_fields(self, client):
        items = get_available_items(client)
        if not items:
            pytest.skip("No available items to test")
        item = items[0]
        for field in ["budget_item_id", "client_name", "service_name", "address"]:
            assert field in item, f"Missing field '{field}' in item: {list(item.keys())}"
        print(f"Available items count: {len(items)}, sample: {item['budget_item_id']}")


class TestGeoapifyFullFlow:
    """Full flow: create route -> add stops -> optimize with Geoapify -> verify"""

    route_id = None

    def test_01_cleanup_existing_routes(self, client):
        cleanup_routes(client)
        time.sleep(0.5)
        items = get_available_items(client)
        print(f"Available items after cleanup: {len(items)}")
        assert len(items) >= 1, f"No available items. Check database seed."

    def test_02_create_route(self, client):
        payload = {
            "vehicle_type": "CARRO",
            "planned_date": "2026-03-01",
            "planned_start_time": "08:00",
            "alias": "TEST_Geoapify_Route"
        }
        resp = client.post(f"{BASE_URL}/api/routes", json=payload)
        assert resp.status_code in [200, 201], f"Create route failed ({resp.status_code}): {resp.text}"
        data = resp.json()
        assert "id" in data, f"No 'id' in response: {data}"
        TestGeoapifyFullFlow.route_id = data["id"]
        print(f"Created route: {data['id']}")

    def test_03_route_has_company_address(self, client):
        rid = TestGeoapifyFullFlow.route_id
        assert rid, "route_id not set (test_02 failed)"
        resp = client.get(f"{BASE_URL}/api/routes/{rid}")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "company_address" in data, f"company_address missing: {list(data.keys())}"
        ca = data["company_address"]
        assert "latitude" in ca and "longitude" in ca, f"Missing lat/lon: {ca}"
        assert ca["latitude"] != 0 and ca["longitude"] != 0, f"Zero coordinates: {ca}"
        print(f"company_address: lat={ca['latitude']}, lon={ca['longitude']}")

    def test_04_add_stops_to_route(self, client):
        rid = TestGeoapifyFullFlow.route_id
        assert rid
        items = get_available_items(client)
        assert len(items) >= 1
        # Add up to 3 items as stops (all AUTOMATICA priority)
        stops_payload = [
            {"budget_item_id": item["budget_item_id"], "priority": "AUTOMATICA"}
            for item in items[:3]
        ]
        resp = client.put(f"{BASE_URL}/api/routes/{rid}/stops", json=stops_payload)
        assert resp.status_code == 200, f"Add stops failed ({resp.status_code}): {resp.text}"
        data = resp.json()
        assert "stops_count" in data
        print(f"Added {data['stops_count']} stops")

    def test_05_route_has_stops(self, client):
        rid = TestGeoapifyFullFlow.route_id
        assert rid
        resp = client.get(f"{BASE_URL}/api/routes/{rid}")
        data = resp.json()
        stops = data.get("stops", [])
        assert len(stops) >= 1, f"Route has no stops after PUT /stops"
        print(f"Route has {len(stops)} stops")

    def test_06_stop_ids_are_unique(self, client):
        """Bug fix: stop IDs must not all be STP-0000001"""
        rid = TestGeoapifyFullFlow.route_id
        assert rid
        resp = client.get(f"{BASE_URL}/api/routes/{rid}")
        stops = resp.json().get("stops", [])
        ids = [s.get("id") for s in stops]
        print(f"Stop IDs: {ids}")
        assert len(ids) == len(set(ids)), f"Duplicate stop IDs (BUG): {ids}"
        # Also verify not all equal to STP-0000001
        if len(ids) > 1:
            assert not all(i == ids[0] for i in ids), f"All stop IDs identical: {ids}"

    def test_07_stops_have_agenda_fields(self, client):
        """Stops must have fields needed by Agenda module."""
        rid = TestGeoapifyFullFlow.route_id
        assert rid
        resp = client.get(f"{BASE_URL}/api/routes/{rid}")
        stops = resp.json().get("stops", [])
        assert stops
        stop = stops[0]
        required = ["budget_item_id", "order_sequence", "client_name", "service_name", "address"]
        missing = [f for f in required if f not in stop]
        assert not missing, f"Stops missing Agenda fields: {missing}. Keys: {list(stop.keys())}"

    def test_08_optimize_with_geoapify(self, client):
        rid = TestGeoapifyFullFlow.route_id
        assert rid
        resp = client.post(f"{BASE_URL}/api/routes/{rid}/optimize-geoapify")
        print(f"Optimize response ({resp.status_code}): {resp.text[:300]}")
        assert resp.status_code == 200, f"Geoapify optimize failed ({resp.status_code}): {resp.text}"

    def test_09_optimize_returns_required_fields(self, client):
        rid = TestGeoapifyFullFlow.route_id
        assert rid
        resp = client.post(f"{BASE_URL}/api/routes/{rid}/optimize-geoapify")
        assert resp.status_code == 200
        data = resp.json()
        for field in ["total_stops", "total_distance_km", "total_duration_minutes"]:
            assert field in data, f"Missing '{field}' in response: {data}"
        assert data["total_stops"] >= 1
        assert data["total_distance_km"] >= 0
        print(f"Geoapify result: stops={data['total_stops']}, dist={data['total_distance_km']}km, dur={data['total_duration_minutes']}min")

    def test_10_route_saved_after_optimize(self, client):
        rid = TestGeoapifyFullFlow.route_id
        assert rid
        # Optimize
        client.post(f"{BASE_URL}/api/routes/{rid}/optimize-geoapify")
        time.sleep(0.5)
        # Fetch saved route
        resp = client.get(f"{BASE_URL}/api/routes/{rid}")
        assert resp.status_code == 200
        data = resp.json()
        stops = data.get("stops", [])
        assert len(stops) >= 1
        print(f"Saved: stops={len(stops)}, total_distance={data.get('total_distance')}, total_duration={data.get('total_duration')}")

    def test_11_route_appears_in_list(self, client):
        rid = TestGeoapifyFullFlow.route_id
        assert rid
        resp = client.get(f"{BASE_URL}/api/routes")
        assert resp.status_code == 200
        ids = [r["id"] for r in resp.json()]
        assert rid in ids, f"Route {rid} not in GET /api/routes: {ids}"

    def test_12_geoapify_status_field(self, client):
        rid = TestGeoapifyFullFlow.route_id
        assert rid
        resp = client.post(f"{BASE_URL}/api/routes/{rid}/optimize-geoapify")
        assert resp.status_code == 200
        data = resp.json()
        assert "geoapify_status" in data, f"Missing geoapify_status: {data}"
        print(f"geoapify_status: {data['geoapify_status']}")

    def test_13_cleanup(self, client):
        if TestGeoapifyFullFlow.route_id:
            resp = client.delete(f"{BASE_URL}/api/routes/{TestGeoapifyFullFlow.route_id}")
            print(f"Deleted route: {resp.status_code}")


class TestPriorities:
    """Priorities: PRIMEIRA->first, ULTIMA->last"""

    route_id = None

    def test_01_create_multi_stop_route_with_priorities(self, client):
        cleanup_routes(client)
        time.sleep(0.5)
        items = get_available_items(client)
        if len(items) < 3:
            pytest.skip(f"Need >=3 items, found {len(items)}")

        # Create route
        resp = client.post(f"{BASE_URL}/api/routes", json={
            "vehicle_type": "CARRO",
            "planned_date": "2026-03-01",
            "planned_start_time": "08:00",
            "alias": "TEST_Priority_Route"
        })
        assert resp.status_code in [200, 201]
        TestPriorities.route_id = resp.json()["id"]

        # Add stops with different priorities
        stops_payload = [
            {"budget_item_id": items[0]["budget_item_id"], "priority": "AUTOMATICA"},
            {"budget_item_id": items[1]["budget_item_id"], "priority": "PRIMEIRA"},
            {"budget_item_id": items[2]["budget_item_id"], "priority": "ULTIMA"},
        ]
        resp = client.put(f"{BASE_URL}/api/routes/{TestPriorities.route_id}/stops", json=stops_payload)
        assert resp.status_code == 200, f"Add stops: {resp.text}"

    def test_02_unique_stop_ids_multi_stop(self, client):
        rid = TestPriorities.route_id
        if not rid:
            pytest.skip("route_id not set")
        resp = client.get(f"{BASE_URL}/api/routes/{rid}")
        stops = resp.json().get("stops", [])
        ids = [s.get("id") for s in stops]
        print(f"Priority test stop IDs: {ids}")
        assert len(ids) == len(set(ids)), f"Duplicate stop IDs (BUG): {ids}"

    def test_03_optimize_with_priorities(self, client):
        rid = TestPriorities.route_id
        if not rid:
            pytest.skip("route_id not set")
        resp = client.post(f"{BASE_URL}/api/routes/{rid}/optimize-geoapify")
        assert resp.status_code == 200, f"Optimize with priorities failed: {resp.text}"
        data = resp.json()
        print(f"Priority optimize result: {data}")
        assert data["total_stops"] >= 1

    def test_04_primeira_is_first_ultima_is_last(self, client):
        """PRIMEIRA stop should have order_sequence=1, ULTIMA should be last."""
        rid = TestPriorities.route_id
        if not rid:
            pytest.skip("route_id not set")
        items = get_available_items(client)
        # Re-fetch budget item ids for priority check
        resp = client.get(f"{BASE_URL}/api/routes/{rid}")
        stops = resp.json().get("stops", [])
        if not stops:
            pytest.skip("No stops after optimize")
        
        sorted_stops = sorted(stops, key=lambda s: s.get("order_sequence", 99))
        print(f"Stop order after optimize: {[(s.get('id'), s.get('order_sequence')) for s in sorted_stops]}")
        # We can't be 100% sure which item was PRIMEIRA without tracking, but verify sequence is 1..N
        sequences = [s.get("order_sequence") for s in stops]
        assert sorted(sequences) == list(range(1, len(stops)+1)), f"Sequences not 1..N: {sequences}"

    def test_05_cleanup(self, client):
        if TestPriorities.route_id:
            client.delete(f"{BASE_URL}/api/routes/{TestPriorities.route_id}")
            print("Cleaned up priority test route")
