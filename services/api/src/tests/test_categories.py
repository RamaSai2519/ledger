from conftest import auth_headers, signup


def _signup_household(client, mobile_number="9876543210", name="Rama"):
    resp = signup(client, mobile_number=mobile_number, name=name)
    token = resp.get_json()["data"]["access_token"]
    client.post("/auth/household/create", json={"name": "Our Home"}, headers=auth_headers(token))
    return token


def test_default_categories_seeded_on_household_create(client):
    token = _signup_household(client)
    resp = client.get("/categories", headers=auth_headers(token))
    assert resp.status_code == 200
    names = {c["name"] for c in resp.get_json()["data"]["categories"]}
    assert "Food & Dining" in names
    assert "Salary" in names
    assert "Balance Adjustment" in names


def test_create_category_success(client):
    token = _signup_household(client)
    resp = client.post("/categories", json={"name": "Pets", "type": "expense"}, headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.get_json()["data"]["name"] == "Pets"
    assert resp.get_json()["data"]["is_default"] is False


def test_create_category_invalid_type(client):
    token = _signup_household(client)
    resp = client.post("/categories", json={"name": "Pets", "type": "neutral"}, headers=auth_headers(token))
    assert resp.status_code == 400


def test_create_category_duplicate_name_conflicts(client):
    token = _signup_household(client)
    resp = client.post(
        "/categories", json={"name": "Food & Dining", "type": "expense"}, headers=auth_headers(token)
    )
    assert resp.status_code == 409


def test_create_category_requires_auth(client):
    resp = client.post("/categories", json={"name": "Pets", "type": "expense"})
    assert resp.status_code == 401


def test_categories_household_scoped(client):
    token_a = _signup_household(client, mobile_number="9876543210", name="A")
    token_b = _signup_household(client, mobile_number="9111111111", name="B")

    client.post("/categories", json={"name": "A Only", "type": "expense"}, headers=auth_headers(token_a))

    resp_b = client.get("/categories", headers=auth_headers(token_b))
    names_b = {c["name"] for c in resp_b.get_json()["data"]["categories"]}
    assert "A Only" not in names_b


def test_update_category_success(client):
    token = _signup_household(client)
    create_resp = client.post("/categories", json={"name": "Pets", "type": "expense"}, headers=auth_headers(token))
    category_id = create_resp.get_json()["data"]["id"]

    resp = client.patch(f"/categories/{category_id}", json={"name": "Pet Care"}, headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.get_json()["data"]["name"] == "Pet Care"


def test_update_category_cannot_change_type(client):
    token = _signup_household(client)
    create_resp = client.post("/categories", json={"name": "Pets", "type": "expense"}, headers=auth_headers(token))
    category_id = create_resp.get_json()["data"]["id"]

    resp = client.patch(f"/categories/{category_id}", json={"type": "income"}, headers=auth_headers(token))
    assert resp.status_code == 400


def test_update_system_category_blocked(client):
    token = _signup_household(client)
    categories = client.get("/categories", headers=auth_headers(token)).get_json()["data"]["categories"]
    adjustment = next(c for c in categories if c["name"] == "Balance Adjustment")

    resp = client.patch(
        f"/categories/{adjustment['id']}", json={"is_archived": True}, headers=auth_headers(token)
    )
    assert resp.status_code == 409


def test_delete_unreferenced_category_hard_deletes(client):
    token = _signup_household(client)
    create_resp = client.post("/categories", json={"name": "Pets", "type": "expense"}, headers=auth_headers(token))
    category_id = create_resp.get_json()["data"]["id"]

    resp = client.delete(f"/categories/{category_id}", headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.get_json()["data"]["hard_deleted"] is True

    list_resp = client.get("/categories", headers=auth_headers(token))
    names = {c["name"] for c in list_resp.get_json()["data"]["categories"]}
    assert "Pets" not in names


def test_delete_referenced_category_archives_instead(client):
    token = _signup_household(client)
    wallet_resp = client.post(
        "/wallets",
        json={"name": "Cash", "type": "cash", "opening_balance": 500},
        headers=auth_headers(token),
    )
    wallet_id = wallet_resp.get_json()["data"]["id"]

    category_resp = client.post("/categories", json={"name": "Pets", "type": "expense"}, headers=auth_headers(token))
    category_id = category_resp.get_json()["data"]["id"]

    client.post(
        "/transactions",
        json={"wallet_id": wallet_id, "category_id": category_id, "type": "expense", "amount": 50},
        headers=auth_headers(token),
    )

    resp = client.delete(f"/categories/{category_id}", headers=auth_headers(token))
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["hard_deleted"] is False
    assert body["is_archived"] is True

    list_resp = client.get("/categories", headers=auth_headers(token))
    names = {c["name"] for c in list_resp.get_json()["data"]["categories"]}
    assert "Pets" not in names  # archived, excluded from default listing

    list_all_resp = client.get("/categories?include_archived=true", headers=auth_headers(token))
    names_all = {c["name"] for c in list_all_resp.get_json()["data"]["categories"]}
    assert "Pets" in names_all


def test_delete_system_category_blocked(client):
    token = _signup_household(client)
    categories = client.get("/categories", headers=auth_headers(token)).get_json()["data"]["categories"]
    adjustment = next(c for c in categories if c["name"] == "Balance Adjustment")

    resp = client.delete(f"/categories/{adjustment['id']}", headers=auth_headers(token))
    assert resp.status_code == 409


def test_new_category_gets_next_sort_order(client):
    token = _signup_household(client)
    seeded = client.get("/categories", headers=auth_headers(token)).get_json()["data"]["categories"]

    resp = client.post("/categories", json={"name": "Pets", "type": "expense"}, headers=auth_headers(token))
    assert resp.get_json()["data"]["sort_order"] == len(seeded)


def test_reorder_categories_success(client):
    token = _signup_household(client)
    categories = client.get("/categories", headers=auth_headers(token)).get_json()["data"]["categories"]
    ids = [c["id"] for c in categories]
    new_order = list(reversed(ids))

    resp = client.patch("/categories/reorder", json={"order": new_order}, headers=auth_headers(token))
    assert resp.status_code == 200
    reordered_ids = [c["id"] for c in resp.get_json()["data"]["categories"]]
    assert reordered_ids == new_order

    list_resp = client.get("/categories", headers=auth_headers(token))
    listed_ids = [c["id"] for c in list_resp.get_json()["data"]["categories"] if c["id"] in new_order]
    assert listed_ids == new_order


def test_reorder_categories_rejects_foreign_category(client):
    token_a = _signup_household(client, mobile_number="9876543210", name="A")
    token_b = _signup_household(client, mobile_number="9111111111", name="B")

    categories_a = client.get("/categories", headers=auth_headers(token_a)).get_json()["data"]["categories"]
    foreign_id = categories_a[0]["id"]

    categories_b = client.get("/categories", headers=auth_headers(token_b)).get_json()["data"]["categories"]
    order = [c["id"] for c in categories_b]
    order[0] = foreign_id

    resp = client.patch("/categories/reorder", json={"order": order}, headers=auth_headers(token_b))
    assert resp.status_code == 400


def test_reorder_categories_requires_order(client):
    token = _signup_household(client)
    resp = client.patch("/categories/reorder", json={"order": []}, headers=auth_headers(token))
    assert resp.status_code == 400
