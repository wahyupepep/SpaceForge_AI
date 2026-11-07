from app.services.auth import _password_hash, _password_matches, token_hash


def test_password_hash_is_salted_and_verifiable() -> None:
    first = _password_hash("correct horse battery staple")
    second = _password_hash("correct horse battery staple")

    assert first != second
    assert "correct horse battery staple" not in first
    assert _password_matches("correct horse battery staple", first)
    assert not _password_matches("wrong password", first)


def test_session_token_hash_is_deterministic_without_storing_token() -> None:
    token = "private-session-token"

    assert token_hash(token) == token_hash(token)
    assert token not in token_hash(token)
