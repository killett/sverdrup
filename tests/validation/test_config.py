"""Tests for the validation-run .env configuration loader."""

import pytest

from sverdrup.validation.config import ValidationConfig


def test_authenticated_method_with_empty_creds_fails_loud(tmp_path):
    """thredds with empty creds must raise naming the missing vars.

    Catches a silent no-auth fallthrough that would later 401 deep in a fetch.
    """
    env = tmp_path / ".env"
    env.write_text("AVISO_ACCESS_METHOD=thredds\nAVISO_USERNAME=\nAVISO_PASSWORD=\n")
    with pytest.raises(ValueError, match="AVISO_USERNAME"):
        ValidationConfig.load(env_path=env)


def test_ftp_method_with_empty_creds_fails_loud(tmp_path):
    """ftp is also authenticated, so empty creds must raise too.

    Catches an auth-method allowlist that forgets ftp and lets it 401 later.
    """
    env = tmp_path / ".env"
    env.write_text("AVISO_ACCESS_METHOD=ftp\nAVISO_USERNAME=\nAVISO_PASSWORD=\n")
    with pytest.raises(ValueError, match="AVISO_PASSWORD"):
        ValidationConfig.load(env_path=env)


def test_meom_mirror_allows_empty_creds(tmp_path):
    """meom_mirror is unauthenticated, so empty creds must be accepted.

    Catches an over-eager validator that blocks the no-auth fallback path.
    """
    env = tmp_path / ".env"
    env.write_text(
        "AVISO_ACCESS_METHOD=meom_mirror\nAVISO_USERNAME=\nAVISO_PASSWORD=\n"
        "MEOM_OPENDAP_BASE_URL=https://example.org/thredds\n"
    )
    cfg = ValidationConfig.load(env_path=env)
    assert cfg.access_method == "meom_mirror"
    assert cfg.meom_opendap_base_url == "https://example.org/thredds"


def test_authenticated_method_with_filled_creds_succeeds(tmp_path):
    """thredds with both creds present loads and carries them through.

    Catches a validator that rejects a correctly-filled authenticated config.
    """
    env = tmp_path / ".env"
    env.write_text(
        "AVISO_ACCESS_METHOD=thredds\nAVISO_USERNAME=alice\nAVISO_PASSWORD=secret\n"
        "AVISO_THREDDS_BASE_URL=https://tds.example.fr\n"
    )
    cfg = ValidationConfig.load(env_path=env)
    assert cfg.access_method == "thredds"
    assert cfg.aviso_username == "alice"
    assert cfg.aviso_password == "secret"
    assert cfg.thredds_base_url == "https://tds.example.fr"


def test_default_access_method_is_thredds_and_requires_creds(tmp_path):
    """An absent AVISO_ACCESS_METHOD defaults to thredds and still gates creds.

    Catches a default that silently disables the authenticated-creds check.
    """
    env = tmp_path / ".env"
    env.write_text("AVISO_USERNAME=\nAVISO_PASSWORD=\n")
    with pytest.raises(ValueError, match="AVISO_USERNAME"):
        ValidationConfig.load(env_path=env)
