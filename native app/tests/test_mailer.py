"""Unit tests for settings manager and mailer."""

import pytest
from pathlib import Path
from src.certapp.core.models import Participant
from src.certapp.core.settings import SettingsManager, SMTPSettings
from src.certapp.core.mailer import SMTPMailer


def test_settings_manager_load_save(tmp_path):
    cfg_file = tmp_path / "config.json"
    mgr = SettingsManager(config_path=cfg_file)
    mgr.smtp_settings.smtp_host = "smtp.custom.org"
    mgr.smtp_settings.smtp_port = 465
    mgr.smtp_settings.security_mode = "SSL"
    mgr.save()

    mgr2 = SettingsManager(config_path=cfg_file)
    assert mgr2.smtp_settings.smtp_host == "smtp.custom.org"
    assert mgr2.smtp_settings.smtp_port == 465
    assert mgr2.smtp_settings.security_mode == "SSL"


def test_app_password_whitespace_normalization(tmp_path):
    cfg_file = tmp_path / "config.json"
    mgr = SettingsManager(config_path=cfg_file)
    mgr.smtp_settings.username = "tester@gmail.com"
    # Google app password format with spaces
    mgr.set_password(" abcd efgh ijkl mnop ")
    saved = mgr.get_password()
    assert saved == "abcdefghijklmnop"


def test_mailer_validates_empty_inputs():
    # Empty host
    m1 = SMTPMailer(SMTPSettings(smtp_host=""), "pwd")
    ok1, msg1 = m1.connect()
    assert not ok1 and "host is empty" in msg1.lower()

    # Empty user
    m2 = SMTPMailer(SMTPSettings(smtp_host="smtp.gmail.com", username=""), "pwd")
    ok2, msg2 = m2.connect()
    assert not ok2 and "username/email is empty" in msg2.lower()

    # Empty password
    m3 = SMTPMailer(SMTPSettings(smtp_host="smtp.gmail.com", username="user@gmail.com"), "")
    ok3, msg3 = m3.connect()
    assert not ok3 and "password is empty" in msg3.lower()


def test_template_formatting():
    settings = SMTPSettings(
        subject_template="Certificate for {name} ({email})",
        body_template="Hello {name}, your role is {Role}."
    )
    mailer = SMTPMailer(settings, "fake_pass")

    p = Participant(
        row_index=1,
        name="Alice Walker",
        email="alice@example.com",
        extra_fields={"Role": "Speaker"}
    )

    subj = mailer._format_template(settings.subject_template, p)
    body = mailer._format_template(settings.body_template, p)

    assert subj == "Certificate for Alice Walker (alice@example.com)"
    assert body == "Hello Alice Walker, your role is Speaker."
