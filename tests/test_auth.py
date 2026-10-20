"""Tests for logging in, logging out, and who is allowed to see which page."""

import pytest
from werkzeug.security import generate_password_hash

# Test-only login details. They match the admin user that tests/conftest.py creates.
ADMIN_LOGIN = {"username": "admin", "password": "admin-test-password"}

WRONG_LOGIN_MESSAGE = b"Wrong username or password."


# ---------------------------------------------------------------- logging in


# If this fails: the login page is missing a box, or shows the password as plain text.
def test_login_page_has_username_box_and_hidden_password_box(client):
    response = client.get("/login")

    assert b'name="username"' in response.data
    assert b'name="password"' in response.data
    assert b'type="password"' in response.data


# If this fails: people with the right password are sent to the wrong page after logging in.
def test_correct_password_redirects_to_the_home_page(client):
    response = client.post("/login", data=ADMIN_LOGIN)

    assert response.status_code == 302
    assert response.headers["Location"] == "/"


# If this fails: the app forgets who the admin is, so every admin page would refuse them.
def test_login_remembers_the_admin_username_and_role(admin_client):
    with admin_client.session_transaction() as sess:
        assert sess["username"] == "admin"
        assert sess["role"] == "admin"


# If this fails: shoppers are not recorded as shoppers, so role checks cannot tell them apart.
def test_login_remembers_the_shopper_username_and_role(shopper_client):
    with shopper_client.session_transaction() as sess:
        assert sess["username"] == "shopper"
        assert sess["role"] == "shopper"


# If this fails: someone typing a wrong password gets no error message and is left confused.
def test_wrong_password_shows_the_error_message(client):
    response = client.post(
        "/login", data={"username": "admin", "password": "not-the-password"}
    )

    assert response.status_code == 200
    assert WRONG_LOGIN_MESSAGE in response.data


# If this fails: a wrong password still logs the person in, so passwords protect nothing.
def test_wrong_password_does_not_log_the_user_in(client):
    client.post("/login", data={"username": "admin", "password": "not-the-password"})

    with client.session_transaction() as sess:
        assert "username" not in sess


# If this fails: the login page reveals which usernames exist, helping attackers guess accounts.
def test_unknown_username_gets_exactly_the_same_page_as_a_wrong_password(client):
    wrong_password = client.post(
        "/login", data={"username": "admin", "password": "not-the-password"}
    )
    unknown_user = client.post(
        "/login", data={"username": "ghost", "password": "not-the-password"}
    )

    assert unknown_user.status_code == wrong_password.status_code
    assert unknown_user.data == wrong_password.data


# If this fails: an empty form gets through, or crashes instead of showing an error.
def test_blank_username_and_password_are_rejected(client):
    response = client.post("/login", data={"username": "", "password": ""})

    assert WRONG_LOGIN_MESSAGE in response.data
    with client.session_transaction() as sess:
        assert "username" not in sess


# If this fails: a classic trick string lets someone log in without a valid password.
@pytest.mark.parametrize(
    "username, password",
    [
        ("admin' --", "anything"),
        ("admin", "' OR '1'='1"),
        ("' OR '1'='1' --", "anything"),
    ],
)
def test_common_injection_strings_do_not_log_anyone_in(client, username, password):
    response = client.post("/login", data={"username": username, "password": password})

    assert WRONG_LOGIN_MESSAGE in response.data
    with client.session_transaction() as sess:
        assert "username" not in sess


# If this fails: typed text reaches the database as a command, so an attacker can forge an admin login.
def test_injected_query_cannot_forge_an_admin_login(client):
    # The attacker makes their own password hash, then smuggles it into the query as a
    # fake "admin" row. This only works if the login query joins typed text into the SQL.
    attacker_hash = generate_password_hash("attacker-password")
    username = f"nobody' UNION SELECT 'admin', '{attacker_hash}', 'admin' --"

    response = client.post(
        "/login", data={"username": username, "password": "attacker-password"}
    )

    assert WRONG_LOGIN_MESSAGE in response.data
    with client.session_transaction() as sess:
        assert "username" not in sess


# --------------------------------------------------------------- logging out


# If this fails: the Logout link leaves people stranded on a page that is not the shop.
def test_logout_redirects_to_the_home_page(admin_client):
    response = admin_client.get("/logout")

    assert response.status_code == 302
    assert response.headers["Location"] == "/"


# If this fails: logging out does not forget the user, so the next person is still signed in.
def test_logout_removes_the_username_and_role(admin_client):
    admin_client.get("/logout")

    with admin_client.session_transaction() as sess:
        assert "username" not in sess
        assert "role" not in sess


# If this fails: an admin who logs out can still open the admin pages.
def test_admin_page_is_closed_again_after_logout(admin_client):
    admin_client.get("/logout")

    response = admin_client.get("/admin")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


# ------------------------------------------------- who is allowed where (POST)

NEW_PRODUCT = {"name": "Sneaky Mug", "description": "Should not exist", "price": "1.00"}


# If this fails: a shopper can change the catalogue, such as adding products or setting prices.
def test_shopper_cannot_post_a_new_product(shopper_client):
    response = shopper_client.post("/admin/add", data=NEW_PRODUCT)

    assert response.status_code == 403


# If this fails: the "forbidden" answer is only for show and the shopper's product is saved anyway.
def test_shopper_post_to_admin_add_saves_nothing(client, shopper_client):
    shopper_client.post("/admin/add", data=NEW_PRODUCT)

    home = client.get("/")
    assert b"Notebook" in home.data  # the shop page really loaded
    assert b"Sneaky Mug" not in home.data


# If this fails: a logged-out visitor is not sent to log in when they try to add a product.
def test_logged_out_post_to_admin_add_redirects_to_login(client):
    response = client.post("/admin/add", data=NEW_PRODUCT)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


# If this fails: a visitor who is not logged in at all can add products to the shop.
def test_logged_out_post_to_admin_add_saves_nothing(client):
    client.post("/admin/add", data=NEW_PRODUCT)

    home = client.get("/")
    assert b"Notebook" in home.data  # the shop page really loaded
    assert b"Sneaky Mug" not in home.data


# If this fails: a shopper is refused with a blank or confusing page instead of a clear message.
def test_forbidden_page_tells_the_shopper_they_lack_permission(shopper_client):
    response = shopper_client.get("/admin")

    assert b"You do not have permission to view this page." in response.data


# If this fails: an odd or missing role (for example "Admin" or "superuser") counts as an admin.
@pytest.mark.parametrize("role", [None, "", "Admin", "superuser"])
def test_session_role_other_than_exactly_admin_is_forbidden(client, role):
    with client.session_transaction() as sess:
        sess["username"] = "someone"
        if role is not None:
            sess["role"] = role

    response = client.get("/admin")

    assert response.status_code == 403


# ------------------------------------------------------------------ checkout


# If this fails: a visitor who is not logged in can start checking out.
def test_logged_out_visitor_is_redirected_from_checkout(client):
    response = client.get("/checkout")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


# If this fails: a logged-out visitor can place an order and wipe the cart.
def test_logged_out_checkout_post_does_not_empty_the_cart(client):
    client.post("/cart/add/1")

    client.post("/checkout")

    with client.session_transaction() as sess:
        assert sess["cart"] == [1]


# If this fails: a logged-in shopper cannot reach checkout, so nobody can buy anything.
def test_logged_in_shopper_can_open_checkout(shopper_client):
    response = shopper_client.get("/checkout")

    assert b"You are about to order 0 item(s)." in response.data
