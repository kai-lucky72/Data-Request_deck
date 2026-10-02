"""Tests for password hashing and verification."""

from app.core.security import hash_password, verify_password


def test_password_hash_round_trip():
    """Passwords hash once and verify using the supported bcrypt library API."""
    encoded_hash = hash_password("safe-demo-password")
    assert encoded_hash != "safe-demo-password"
    assert verify_password("safe-demo-password", encoded_hash)
    assert not verify_password("wrong-password", encoded_hash)
