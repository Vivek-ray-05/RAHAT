import pytest
from pydantic import ValidationError

from app.config import Settings


def _settings(**overrides):
    defaults = dict(DATABASE_URL="postgresql://x", JWT_SECRET="test-secret")
    defaults.update(overrides)
    return Settings(**defaults)


def test_dev_mode_with_localhost_cors_is_allowed():
    s = _settings(DEV_MODE=True, CORS_ORIGINS="http://localhost:5173")
    assert s.DEV_MODE is True


def test_dev_mode_with_127_0_0_1_cors_is_allowed():
    s = _settings(DEV_MODE=True, CORS_ORIGINS="http://127.0.0.1:5173")
    assert s.DEV_MODE is True


def test_dev_mode_with_a_real_domain_refuses_to_start():
    with pytest.raises(ValidationError, match="Refusing to start"):
        _settings(DEV_MODE=True, CORS_ORIGINS="https://rahat.example.com")


def test_dev_mode_with_a_mix_of_localhost_and_real_domain_refuses_to_start():
    with pytest.raises(ValidationError):
        _settings(DEV_MODE=True, CORS_ORIGINS="http://localhost:5173,https://rahat.example.com")


def test_dev_mode_false_allows_any_cors_origin():
    s = _settings(DEV_MODE=False, CORS_ORIGINS="https://rahat.example.com")
    assert s.DEV_MODE is False
