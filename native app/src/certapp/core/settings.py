"""Settings Manager with OS Keyring integration and reliable file fallback."""

import json
import logging
import base64
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Any, Optional

from src.certapp.core.utils import get_app_dir

logger = logging.getLogger("certapp.settings")

KEYRING_SERVICE_NAME = "CertApp_SMTP"


@dataclass
class SMTPSettings:
    """SMTP Server and Email Sending Configuration."""
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    security_mode: str = "STARTTLS"  # "SSL", "STARTTLS", "None"
    username: str = ""
    sender_name: str = "Certificate Automation"
    sender_email: str = ""
    subject_template: str = "Your Certificate of Completion for {name}"
    body_template: str = (
        "Dear {name},\n\n"
        "Congratulations! Please find your official certificate attached to this email.\n\n"
        "Best regards,\n"
        "Certificate Team"
    )
    delay_seconds: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SMTPSettings":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


def _try_keyring_available() -> bool:
    """Check if a usable keyring backend is available."""
    try:
        import keyring
        backend = keyring.get_keyring()
        backend_name = type(backend).__name__
        if "Fail" in backend_name or "fail" in backend_name.lower():
            return False
        if "ChainerBackend" in backend_name:
            try:
                keyring.get_password("__certapp_test__", "__probe__")
                return True
            except Exception:
                return False
        return True
    except Exception:
        return False


class SettingsManager:
    """Manages application settings and secure password storage.
    
    Uses OS keyring when available, with reliable file-based fallback storage.
    """

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or (get_app_dir() / "config.json")
        self._cred_path = self.config_path.parent / ".credentials"
        self.smtp_settings = SMTPSettings()
        self._keyring_ok = _try_keyring_available()
        self.load()

    def load(self) -> SMTPSettings:
        """Loads settings from config.json if it exists."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                smtp_data = data.get("smtp", {})
                self.smtp_settings = SMTPSettings.from_dict(smtp_data)
            except Exception as e:
                logger.error(f"Failed to load settings: {e}")
        return self.smtp_settings

    def save(self) -> None:
        """Saves non-sensitive settings to config.json."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"smtp": self.smtp_settings.to_dict()}
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def set_password(self, password: str) -> bool:
        """Stores password — cleans App Password spacing, writes to keyring and fallback file."""
        if not self.smtp_settings.username:
            return False

        # Normalize password: strip leading/trailing whitespace
        clean_pwd = password.strip()
        # Clean 16-character Google App Password if pasted with spaces e.g. "abcd efgh ijkl mnop"
        if " " in clean_pwd and len(clean_pwd.replace(" ", "")) == 16:
            clean_pwd = clean_pwd.replace(" ", "")

        saved = False
        if self._keyring_ok:
            try:
                import keyring
                keyring.set_password(KEYRING_SERVICE_NAME, self.smtp_settings.username, clean_pwd)
                saved = True
            except Exception as e:
                logger.warning(f"Keyring set_password failed: {e}")
                self._keyring_ok = False

        # Always maintain fallback file storage
        file_saved = self._set_password_file(clean_pwd)
        return saved or file_saved

    def get_password(self) -> str:
        """Retrieves password — checks keyring first, falls back to file."""
        if not self.smtp_settings.username:
            return ""

        if self._keyring_ok:
            try:
                import keyring
                pwd = keyring.get_password(KEYRING_SERVICE_NAME, self.smtp_settings.username)
                if pwd:
                    # Clean App Password spaces if present
                    pwd = pwd.strip()
                    if " " in pwd and len(pwd.replace(" ", "")) == 16:
                        pwd = pwd.replace(" ", "")
                    return pwd
            except Exception as e:
                logger.warning(f"Keyring get_password failed: {e}")
                self._keyring_ok = False

        pwd = self._get_password_file()
        if pwd:
            pwd = pwd.strip()
            if " " in pwd and len(pwd.replace(" ", "")) == 16:
                pwd = pwd.replace(" ", "")
        return pwd

    def _set_password_file(self, password: str) -> bool:
        """Store password in fallback file with user-only permissions."""
        try:
            self._cred_path.parent.mkdir(parents=True, exist_ok=True)
            creds = self._load_cred_file()
            creds[self.smtp_settings.username] = base64.b64encode(password.encode("utf-8")).decode("ascii")
            with open(self._cred_path, "w", encoding="utf-8") as f:
                json.dump(creds, f)
            try:
                self._cred_path.chmod(0o600)
            except Exception:
                pass
            return True
        except Exception as e:
            logger.error(f"Failed to store password in file: {e}")
            return False

    def _get_password_file(self) -> str:
        """Retrieve password from fallback file."""
        try:
            creds = self._load_cred_file()
            encoded = creds.get(self.smtp_settings.username, "")
            if encoded:
                return base64.b64decode(encoded.encode("ascii")).decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to retrieve password from file: {e}")
        return ""

    def _load_cred_file(self) -> Dict[str, str]:
        if self._cred_path.exists():
            try:
                with open(self._cred_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def clear_password(self) -> None:
        """Clears stored password from keyring and file."""
        if self.smtp_settings.username:
            if self._keyring_ok:
                try:
                    import keyring
                    keyring.delete_password(KEYRING_SERVICE_NAME, self.smtp_settings.username)
                except Exception:
                    pass
            try:
                creds = self._load_cred_file()
                creds.pop(self.smtp_settings.username, None)
                with open(self._cred_path, "w", encoding="utf-8") as f:
                    json.dump(creds, f)
            except Exception:
                pass
