def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_list_invoices(client):
    r = client.get("/invoices")
    assert r.status_code == 200
    assert len(r.json()) == 6


def test_list_invoices_filtered(client):
    r = client.get("/invoices", params={"vendor": "aws", "status": "unpaid"})
    assert r.status_code == 200
    assert [i["id"] for i in r.json()] == [2]


def test_get_invoice(client):
    r = client.get("/invoices/3")
    assert r.status_code == 200
    assert r.json()["vendor"] == "Figma"


def test_get_invoice_404(client):
    assert client.get("/invoices/999").status_code == 404


def test_negative_amount_422(client):
    assert client.get("/invoices", params={"min_amount": -5}).status_code == 422


def test_unknown_query_param_422(client):
    assert client.get("/invoices", params={"foo": 1}).status_code == 422
