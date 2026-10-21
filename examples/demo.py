"""Демо-файл для проверки PyIDE."""
from __future__ import annotations


def greet(name: str) -> str:
    """Вернуть приветствие."""
    return f"Hello, {name}!"


def main() -> None:
    message = greet("Astra")
    print(message)
    numbers = [x * x for x in range(5)]
    print(sum(numbers))


if __name__ == "__main__":
    main()
