import pytest


TEST_USER_PASSWORD = "TestPassWithDigits12345"


@pytest.fixture()
def test_password() -> str:
    return TEST_USER_PASSWORD
