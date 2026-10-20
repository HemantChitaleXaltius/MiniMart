"""Edge-case tests: bad prices, a duplicate username, shoppers at admin pages, wrong passwords."""

import sqlite3

import pytest
from werkzeug.security import generate_password_hash

ADMIN_LOGIN = {"username": "admin", "password": "admin-test-password"}
SHOPPER_PASSWORD = "shopper-test-password"


def product_form(name, price):
    return {"name": name, "description": "Edge-case product", "price": price}


# ------------------------------------------------------- negative / odd prices


# If this fails: the shop accepts products with a price below zero, so checkout totals can go negative.
@pytest.mark.parametrize("price", ["-5", "-0.01", "-1000000"])
def test_admin_form_rejects_a_negative_price_with_a_clear_message(admin_client, price):
    response = admin_client.post("/admin/add", data=product_form("Negative Mug", price))

    assert response.status_code == 400
    assert b"Price must be more than 0 and no more than 100000." in response.data


# If this fails: a rejected negative-price product still ends up on sale in the shop.
def test_product_with_a_negative_price_is_not_saved(client, admin_client):
    admin_client.post("/admin/add", data=product_form("Negative Mug", "-5"))

    home = client.get("/")

    assert b"Notebook" in home.data  # the shop page really loaded
    assert b"Negative Mug" not in home.data


# If this fails: a free (zero-price) product can be added by accident.
def test_admin_form_rejects_a_price_of_zero(admin_client):
    response = admin_client.post("/admin/add", data=product_form("Free Mug", "0"))

    assert response.status_code == 400
    assert b"Price must be more than 0 and no more than 100000." in response.data


# If this fails: "nan" or "inf" (which Python reads as numbers) get stored as prices and break every cart total.
@pytest.mark.parametrize("price", ["nan", "inf", "-inf"])
def test_admin_form_rejects_nan_and_infinity_as_a_price(admin_client, price):
    response = admin_client.post("/admin/add", data=product_form("Odd Mug", price))

    assert response.status_code == 400
    assert b"Price must be more than 0 and no more than 100000." in response.data


# ---------------------------------------------------- prices that are not numbers


# If this fails: text that is not a number is accepted or crashes the page instead of showing an error.
@pytest.mark.parametrize("price", ["", "five", "4,50", "$4.50", "4.5.0"])
def test_admin_form_rejects_a_price_that_is_not_a_number(admin_client, price):
    response = admin_client.post("/admin/add", data=product_form("Text Mug", price))

    assert response.status_code == 400
    assert b"Price must be a number, for example 4.50." in response.data


# If this fails: a product with a bad price is saved anyway, and the shop shows a broken price.
def test_product_with_a_price_that_is_not_a_number_is_not_saved(client, admin_client):
    admin_client.post("/admin/add", data=product_form("Text Mug", "five"))

    home = client.get("/")

    assert b"Notebook" in home.data  # the shop page really loaded
    assert b"Text Mug" not in home.data


# If this fails: after a mistake the admin has to retype everything, because the form forgets what they typed.
def test_rejected_form_keeps_what_the_admin_typed(admin_client):
    response = admin_client.post("/admin/add", data=product_form("Keep My Name", "five"))

    assert b'value="Keep My Name"' in response.data
    assert b'value="five"' in response.data


# ------------------------------------------------------------ duplicate usernames
# MiniMart has no sign-up page, so these tests check the database rule that a
# sign-up (or create_user.py) would run into: a username can exist only once.


# If this fails: two accounts can share one username, so a login could open someone else's account.
def test_database_refuses_a_second_user_with_an_existing_username(app):
    connection = sqlite3.connect(app.config["DATABASE"])
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        connection.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            ("admin", generate_password_hash("attacker-password"), "admin"),
        )
    connection.close()


# If this fails: a duplicate-username attempt overwrites the real admin's password.
def test_duplicate_username_attempt_leaves_the_original_password_working(app, client):
    connection = sqlite3.connect(app.config["DATABASE"])
    try:
        connection.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            ("admin", generate_password_hash("attacker-password"), "admin"),
        )
        connection.commit()
    except sqlite3.IntegrityError:
        pass  # expected: the database refuses the duplicate
    finally:
        connection.close()

    original = client.post("/login", data=ADMIN_LOGIN)
    attacker = client.post(
        "/login", data={"username": "admin", "password": "attacker-password"}
    )

    assert original.status_code == 302
    assert b"Wrong username or password." in attacker.data


# --------------------------------------------- shopper against every admin route


# If this fails: a shopper can reach some admin page, including one added later that nobody remembered to protect.
def test_shopper_is_refused_on_every_admin_route_and_method(app, shopper_client):
    admin_routes = []
    for rule in app.url_map.iter_rules():
        if rule.rule.startswith("/admin"):
            for method in sorted(rule.methods - {"HEAD", "OPTIONS"}):
                admin_routes.append((method, rule.rule))

    # Guard against a vacuous pass: the three routes that exist today must be found.
    assert ("GET", "/admin") in admin_routes
    assert ("GET", "/admin/add") in admin_routes
    assert ("POST", "/admin/add") in admin_routes

    not_refused = []
    for method, path in admin_routes:
        response = shopper_client.open(path, method=method, data={})
        if response.status_code != 403:
            not_refused.append((method, path, response.status_code))

    assert not_refused == []


# If this fails: a shopper's refused request still changes the shop, even though they saw "forbidden".
def test_shopper_refused_on_admin_add_changes_nothing(client, shopper_client):
    shopper_client.post("/admin/add", data=product_form("Shopper Mug", "5.00"))

    home = client.get("/")

    assert b"Notebook" in home.data  # the shop page really loaded
    assert b"Shopper Mug" not in home.data


# ------------------------------------------------------------- wrong passwords


# If this fails: an extra space at the end of the password is ignored, so near-matches get in.
def test_password_with_a_trailing_space_is_rejected(client):
    response = client.post(
        "/login", data={"username": "admin", "password": "admin-test-password "}
    )

    assert b"Wrong username or password." in response.data
    with client.session_transaction() as sess:
        assert "username" not in sess


# If this fails: one account's password opens another account, so a shopper's password would log in as admin.
def test_another_users_correct_password_does_not_log_in_the_admin(client):
    response = client.post(
        "/login", data={"username": "admin", "password": SHOPPER_PASSWORD}
    )

    assert b"Wrong username or password." in response.data
    with client.session_transaction() as sess:
        assert "role" not in sess
