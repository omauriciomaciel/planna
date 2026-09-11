import pytest

from app.bootstrap import parse_people


def test_parse_people_normalizes_and_validates_email() -> None:
    assert parse_people([" Pessoa :PESSOA@EXAMPLE.COM "]) == [
        ("Pessoa", "PESSOA@example.com")
    ]

    with pytest.raises(ValueError):
        parse_people(["Pessoa:email-invalido"])
