import os
import sys

import pytest


TEST_USER_PASSWORD = "TestPassWithDigits12345"


@pytest.fixture()
def test_password() -> str:
    return TEST_USER_PASSWORD


@pytest.fixture(autouse=True)
def clean_in_memory_app_database_between_tests():
    yield
    if os.environ.get("MARKETAI_DATABASE_URL") != "sqlite:///:memory:":
        return
    if "app.db" not in sys.modules:
        return

    from app.db import Base, engine

    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())
