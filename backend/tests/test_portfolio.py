from tests.conftest import client


def test_create_portfolio(auth_headers):
    resp = client.post("/portfolio", json={
        "name": "Test PF",
        "initial_cash": 100000.00,
    }, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test PF"
    assert data["initial_cash"] == 100000.00
    assert data["cash_balance"] == 100000.00


def test_list_portfolios(auth_headers):
    client.post("/portfolio", json={"name": "PF1", "initial_cash": 50000.00}, headers=auth_headers)
    client.post("/portfolio", json={"name": "PF2", "initial_cash": 25000.00}, headers=auth_headers)
    resp = client.get("/portfolio", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_buy_success(auth_headers):
    pf = client.post("/portfolio", json={"name": "PF", "initial_cash": 100000.00}, headers=auth_headers)
    pf_id = pf.json()["id"]

    resp = client.post(f"/portfolio/{pf_id}/buy", json={
        "symbol": "TCS", "quantity": 10, "price": 3850.00,
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "TCS"
    assert data["side"] == "BUY"
    assert data["quantity"] == 10


def test_buy_insufficient_cash(auth_headers):
    pf = client.post("/portfolio", json={"name": "PF", "initial_cash": 1000.00}, headers=auth_headers)
    pf_id = pf.json()["id"]

    resp = client.post(f"/portfolio/{pf_id}/buy", json={
        "symbol": "TCS", "quantity": 100, "price": 3850.00,
    }, headers=auth_headers)
    assert resp.status_code == 400
    assert "cash" in resp.json()["detail"].lower()


def test_buy_weighted_average_price(auth_headers):
    pf = client.post("/portfolio", json={"name": "PF", "initial_cash": 100000.00}, headers=auth_headers)
    pf_id = pf.json()["id"]

    client.post(f"/portfolio/{pf_id}/buy", json={
        "symbol": "RELIANCE", "quantity": 10, "price": 100.00,
    }, headers=auth_headers)

    client.post(f"/portfolio/{pf_id}/buy", json={
        "symbol": "RELIANCE", "quantity": 5, "price": 130.00,
    }, headers=auth_headers)

    summary = client.get(f"/portfolio/{pf_id}", headers=auth_headers)
    holdings = summary.json()["holdings"]
    assert len(holdings) == 1
    assert holdings[0]["average_price"] == 110.00
    assert holdings[0]["quantity"] == 15


def test_sell_success(auth_headers):
    pf = client.post("/portfolio", json={"name": "PF", "initial_cash": 100000.00}, headers=auth_headers)
    pf_id = pf.json()["id"]

    client.post(f"/portfolio/{pf_id}/buy", json={
        "symbol": "INFY", "quantity": 20, "price": 1500.00,
    }, headers=auth_headers)

    resp = client.post(f"/portfolio/{pf_id}/sell", json={
        "symbol": "INFY", "quantity": 10, "price": 1600.00,
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["side"] == "SELL"
    assert data["quantity"] == 10


def test_sell_oversell(auth_headers):
    pf = client.post("/portfolio", json={"name": "PF", "initial_cash": 100000.00}, headers=auth_headers)
    pf_id = pf.json()["id"]

    client.post(f"/portfolio/{pf_id}/buy", json={
        "symbol": "INFY", "quantity": 5, "price": 1500.00,
    }, headers=auth_headers)

    resp = client.post(f"/portfolio/{pf_id}/sell", json={
        "symbol": "INFY", "quantity": 20, "price": 1600.00,
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_cross_user_portfolio_access(auth_headers, second_auth_headers):
    pf = client.post("/portfolio", json={"name": "PF", "initial_cash": 10000.00}, headers=auth_headers)
    pf_id = pf.json()["id"]

    get_resp = client.get(f"/portfolio/{pf_id}", headers=second_auth_headers)
    assert get_resp.status_code == 403


def test_portfolio_summary(auth_headers):
    pf = client.post("/portfolio", json={"name": "PF", "initial_cash": 100000.00}, headers=auth_headers)
    pf_id = pf.json()["id"]

    client.post(f"/portfolio/{pf_id}/buy", json={
        "symbol": "RELIANCE", "quantity": 10, "price": 2450.00,
    }, headers=auth_headers)

    resp = client.get(f"/portfolio/{pf_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "cash_balance" in data
    assert "market_value" in data
    assert "equity" in data
    assert "unrealised_pnl" in data
    assert len(data["holdings"]) == 1


def test_delete_portfolio(auth_headers):
    pf = client.post("/portfolio", json={"name": "PF", "initial_cash": 10000.00}, headers=auth_headers)
    pf_id = pf.json()["id"]
    del_resp = client.delete(f"/portfolio/{pf_id}", headers=auth_headers)
    assert del_resp.status_code == 204
