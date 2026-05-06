import pytest


TEST_USER_PASSWORD = "test-pass-with-digits-12345"


@pytest.fixture()
def test_password() -> str:
    return TEST_USER_PASSWORD
