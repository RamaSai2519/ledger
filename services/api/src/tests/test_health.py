def test_health_ok(client):
    resp = client.get("/actions/health")
    assert resp.status_code == 200
    assert resp.get_json()["data"]["status"] == "ok"
