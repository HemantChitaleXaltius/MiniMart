"""Smoke tests: a small starting gate that runs on every push."""


def test_wrong_password_is_rejected(client):
    response = client.post("/login", data={"username": "admin", "password": "not-the-password"})

    assert response.status_code == 200
    assert b"Wrong username or password." in response.data


def test_admin_pages_are_only_for_admins(client, shopper_client, admin_client):
    for path in ("/admin", "/admin/add"):
        logged_out = client.get(path)
        assert logged_out.status_code == 302
        assert logged_out.headers["Location"].endswith("/login")

        assert shopper_client.get(path).status_code == 403
        assert admin_client.get(path).status_code == 200


def test_admin_add_rejects_a_bad_price_and_saves_a_good_one(admin_client):
    bad = admin_client.post(
        "/admin/add", data={"name": "Mug", "description": "Blue", "price": "abc"}
    )
    assert bad.status_code == 400
    assert b"Price must be a number" in bad.data
    assert b"Mug" not in admin_client.get("/").data  # nothing was saved

    good = admin_client.post(
        "/admin/add", data={"name": "Mug", "description": "Blue", "price": "6.50"}
    )
    assert good.status_code == 302
    assert b"Mug" in admin_client.get("/").data


def test_search_treats_sql_as_plain_text(client):
    response = client.get("/search", query_string={"q": "' OR '1'='1"})

    assert response.status_code == 200
    assert b"No products found." in response.data
    assert b"Notebook" not in response.data


def test_search_shows_html_as_plain_text(client):
    response = client.get("/search", query_string={"q": "<b>hello</b>"})

    assert b"<b>hello</b>" not in response.data
    assert b"&lt;b&gt;hello&lt;/b&gt;" in response.data


def test_home_page_lists_the_four_starter_products(client):
    # This runs after the test that adds a "Mug". If a database ever leaked
    # from one test into the next, the setup or this count would break.
    response = client.get("/")

    assert response.status_code == 200
    assert response.data.count(b"Add to cart") == 4
