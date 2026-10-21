"""pytest: проверьте <Space>rt в Vim."""
from demo import greet


def test_greet() -> None:
    assert greet("Astra") == "Hello, Astra!"
