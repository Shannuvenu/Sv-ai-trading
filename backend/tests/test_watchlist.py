from tests.conftest import client


def test_create_watchlist(auth_headers):
    resp = client.post("/watchlists", json={"name": "My Watchlist"}, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Watchlist"


def test_list_watchlists(auth_headers):
    client.post("/watchlists", json={"name": "W1"}, headers=auth_headers)
    client.post("/watchlists", json={"name": "W2"}, headers=auth_headers)
    resp = client.get("/watchlists", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


def test_rename_watchlist(auth_headers):
    resp = client.post("/watchlists", json={"name": "Old"}, headers=auth_headers)
    wl_id = resp.json()["id"]
    patch_resp = client.patch(f"/watchlists/{wl_id}", json={"name": "New"}, headers=auth_headers)
    assert patch_resp.status_code == 200
    assert patch_resp.json()["name"] == "New"


def test_delete_watchlist(auth_headers):
    resp = client.post("/watchlists", json={"name": "ToDelete"}, headers=auth_headers)
    wl_id = resp.json()["id"]
    del_resp = client.delete(f"/watchlists/{wl_id}", headers=auth_headers)
    assert del_resp.status_code == 204


def test_add_item(auth_headers):
    resp = client.post("/watchlists", json={"name": "Tech"}, headers=auth_headers)
    wl_id = resp.json()["id"]
    item_resp = client.post(f"/watchlists/{wl_id}/items", json={"symbol": "TCS"}, headers=auth_headers)
    assert item_resp.status_code == 201
    assert item_resp.json()["symbol"] == "TCS"


def test_add_duplicate_item(auth_headers):
    resp = client.post("/watchlists", json={"name": "Tech"}, headers=auth_headers)
    wl_id = resp.json()["id"]
    client.post(f"/watchlists/{wl_id}/items", json={"symbol": "TCS"}, headers=auth_headers)
    dup_resp = client.post(f"/watchlists/{wl_id}/items", json={"symbol": "TCS"}, headers=auth_headers)
    assert dup_resp.status_code == 400


def test_remove_item(auth_headers):
    resp = client.post("/watchlists", json={"name": "Tech"}, headers=auth_headers)
    wl_id = resp.json()["id"]
    item_resp = client.post(f"/watchlists/{wl_id}/items", json={"symbol": "INFY"}, headers=auth_headers)
    item_id = item_resp.json()["id"]
    del_resp = client.delete(f"/watchlists/{wl_id}/items/{item_id}", headers=auth_headers)
    assert del_resp.status_code == 204


def test_cross_user_watchlist_access(auth_headers, second_auth_headers):
    resp = client.post("/watchlists", json={"name": "U1 List"}, headers=auth_headers)
    wl_id = resp.json()["id"]

    get_resp = client.get(f"/watchlists/{wl_id}", headers=second_auth_headers)
    assert get_resp.status_code == 403

    del_resp = client.delete(f"/watchlists/{wl_id}", headers=second_auth_headers)
    assert del_resp.status_code == 403
