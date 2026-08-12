from tests.conftest import client


def test_list_instruments():
    resp = client.get("/market/instruments")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 12
    symbols = {i["symbol"] for i in data}
    assert "RELIANCE" in symbols
    assert "TCS" in symbols


def test_search_instruments():
    resp = client.get("/market/instruments/search?q=HDFC")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["symbol"] == "HDFCBANK"


def test_search_case_insensitive():
    resp = client.get("/market/instruments/search?q=tcs")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["symbol"] == "TCS"


def test_search_no_results():
    resp = client.get("/market/instruments/search?q=ZZZZZ")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 0


def test_get_instrument():
    resp = client.get("/market/instruments/RELIANCE")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "RELIANCE"
    assert data["name"] == "Reliance Industries Ltd"


def test_get_instrument_not_found():
    resp = client.get("/market/instruments/UNKNOWN")
    assert resp.status_code == 404


def test_get_quote():
    resp = client.get("/market/quote/TCS")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "TCS"
    assert "last_price" in data
    assert "change" in data
    assert "volume" in data


def test_get_quote_not_found():
    resp = client.get("/market/quote/UNKNOWN")
    assert resp.status_code == 404


def test_get_history():
    resp = client.get("/market/history/INFY")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "INFY"
    assert len(data["data"]) > 0
    bar = data["data"][0]
    assert "timestamp" in bar
    assert "open" in bar
    assert "close" in bar
    assert "volume" in bar
