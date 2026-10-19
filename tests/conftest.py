"""Shared test setup. pytest loads this file automatically.

Every test that asks for `app`, `client`, `admin_client` or `shopper_client`
gets its own brand-new app and its own empty database file.
"""

import pytest
from werkzeug.security import generate_password_hash

from app import create_app, get_db, init_db

# Test-only values. They are not real credentials and are used nowhere else.
TEST_SECRET_KEY = "test-only-secret-key-not-used-anywhere-else"
ADMIN = ("admin", "admin-test-password")
SHOPPER = ("shopper", "shopper-test-password")


@pytest.fixture
def app(tmp_path):
    """A fresh MiniMart app whose database lives in a folder only this test uses.

    `tmp_path` is a built-in pytest fixture. pytest creates a new, empty folder
    for every single test, so the database file in it starts empty each time and
    nothing one test saves can be seen by another. Passing the settings straight
    to create_app() also means the real .env, minimart.db and minimart.log are
    never read or written.
    """
    app = create_app(
        {
            "SECRET_KEY": TEST_SECRET_KEY,
            "DATABASE": str(tmp_path / "test.db"),
            "LOG_FILE": None,
        }
    )
    app.config["TESTING"] = True

    with app.app_context():
        init_db()  # creates the tables and the four starter products
        connection = get_db()
        connection.executemany(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            [
                (ADMIN[0], generate_password_hash(ADMIN[1]), "admin"),
                (SHOPPER[0], generate_password_hash(SHOPPER[1]), "shopper"),
            ],
        )
        connection.commit()
        connection.close()
    return app


@pytest.fixture
def client(app):
    """A visitor who is not logged in."""
    return app.test_client()


def _logged_in_client(app, credentials):
    client = app.test_client()
    username, password = credentials
    response = client.post("/login", data={"username": username, "password": password})
    assert response.status_code == 302, "test setup failed: login did not succeed"
    return client


@pytest.fixture
def admin_client(app):
    """A visitor logged in as an admin."""
    return _logged_in_client(app, ADMIN)


@pytest.fixture
def shopper_client(app):
    """A visitor logged in as an ordinary shopper."""
    return _logged_in_client(app, SHOPPER)
