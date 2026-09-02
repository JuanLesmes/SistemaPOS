import pytest

from utils.passwords import hash_password, verify_password


def test_hash_roundtrip_and_unique_salts():
    first = hash_password("clave123")
    second = hash_password("clave123")
    assert first != second, "cada hash lleva su propia sal"
    assert first.startswith("scrypt$")
    assert verify_password("clave123", first)
    assert verify_password("clave123", second)


def test_wrong_password_and_garbage_are_rejected():
    stored = hash_password("correcta")
    assert not verify_password("incorrecta", stored)
    assert not verify_password("correcta", "basura")
    assert not verify_password("correcta", "")


def test_short_passwords_are_rejected():
    with pytest.raises(ValueError):
        hash_password("123")
