"""SMTP Email Sender module with accurate error diagnostics and attachment support."""

import time
import smtplib
import ssl
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from pathlib import Path
from typing import Tuple, Optional, Callable, List
import threading

from src.certapp.core.models import Participant, SendResult
from src.certapp.core.settings import SMTPSettings
from src.certapp.core.state_store import ManifestStore

logger = logging.getLogger("certapp.mailer")


class SMTPConnectionError(Exception):
    """Raised when SMTP connection or authentication cannot be established."""
    pass


class SMTPMailer:
    """Handles secure SMTP server connection and email sending with retries and diagnostics."""

    def __init__(self, settings: SMTPSettings, password: str):
        self.settings = settings
        self.password = password
        self._smtp_conn: Optional[smtplib.SMTP | smtplib.SMTP_SSL] = None

    def _authenticate(self, conn: smtplib.SMTP | smtplib.SMTP_SSL, user: str, password: str) -> None:
        """Authenticates securely while capturing exact server rejection codes.
        
        Prevents smtplib's default behavior of trying secondary auth mechanisms on a
        closed socket after 534/535 rejections, which masks the real error.
        """
        conn.ehlo_or_helo_if_needed()
        if not conn.has_extn("auth"):
            raise smtplib.SMTPNotSupportedError("SMTP AUTH extension not supported by server.")

        clean_pwd = password.strip()
        # Clean 16-character Google App Password if pasted with spaces e.g. "abcd efgh ijkl mnop"
        if " " in clean_pwd and len(clean_pwd.replace(" ", "")) == 16:
            clean_pwd = clean_pwd.replace(" ", "")

        advertised_authlist = conn.esmtp_features.get("auth", "").split()
        preferred_auths = ["PLAIN", "LOGIN"]
        authlist = [auth for auth in preferred_auths if auth in advertised_authlist]
        if not authlist:
            authlist = advertised_authlist

        conn.user, conn.password = user.strip(), clean_pwd
        last_err = None

        for authmethod in authlist:
            method_name = "auth_" + authmethod.lower().replace("-", "_")
            if not hasattr(conn, method_name):
                continue
            try:
                code, resp = conn.auth(authmethod, getattr(conn, method_name), initial_response_ok=True)
                if code in (235, 503):
                    return
            except smtplib.SMTPAuthenticationError as e:
                # Server explicitly rejected credentials (e.g. 534, 535)
                # Stop immediately! Google drops connection after 534/535, so trying next
                # method would raise SMTPServerDisconnected and lose this diagnostic info!
                raise e
            except smtplib.SMTPServerDisconnected as e:
                raise e
            except Exception as e:
                last_err = e
                break

        if last_err is not None:
            raise last_err

        # Fallback to standard login if authlist loop was bypassed
        conn.login(user.strip(), clean_pwd)

    def connect(self) -> Tuple[bool, str]:
        """Establishes connection and logs in to the SMTP server with accurate diagnostic messages."""
        self.disconnect()

        # Validate inputs before attempting network connection
        if not self.settings.smtp_host:
            return False, "SMTP host is empty. Please enter your mail server in Email Settings."
        if not self.settings.username:
            return False, "SMTP username/email is empty. Please enter your email in Email Settings."
        if not self.password:
            return False, (
                "SMTP password is empty.\n\n"
                "Please enter your password in Email Settings and click 'Save & Close'.\n\n"
                "• For Gmail: You MUST use a 16-character Google App Password (not your normal password).\n"
                "  Create one at: https://myaccount.google.com/apppasswords"
            )

        host = self.settings.smtp_host.strip()
        port = self.settings.smtp_port
        sec_mode = self.settings.security_mode.upper()
        is_gmail = "gmail" in host.lower() or "google" in host.lower()

        try:
            logger.info(f"Connecting to SMTP server {host}:{port} ({sec_mode})...")

            if sec_mode == "SSL":
                context = ssl.create_default_context()
                conn = smtplib.SMTP_SSL(host, port, timeout=20, context=context)
            else:
                conn = smtplib.SMTP(host, port, timeout=20)
                if sec_mode == "STARTTLS":
                    conn.ehlo()
                    context = ssl.create_default_context()
                    conn.starttls(context=context)
                    conn.ehlo()

            if self.settings.username and self.password:
                logger.info(f"Authenticating as {self.settings.username}...")
                self._authenticate(conn, self.settings.username, self.password)

            self._smtp_conn = conn
            logger.info("SMTP connection established successfully.")
            return True, "Successfully connected to SMTP server."

        except smtplib.SMTPAuthenticationError as e:
            self._smtp_conn = None
            code = getattr(e, "smtp_code", -1)
            resp_str = ""
            if hasattr(e, "smtp_error") and e.smtp_error:
                resp_str = e.smtp_error.decode("utf-8", errors="replace") if isinstance(e.smtp_error, bytes) else str(e.smtp_error)
            else:
                resp_str = str(e)

            if code == 534 or "application-specific password" in resp_str.lower() or "invalidsecondfactor" in resp_str.lower():
                err_msg = (
                    "🔑 Google App Password Required (Error 534)\n\n"
                    "Google does NOT allow using your regular Gmail password for automated apps.\n\n"
                    "How to fix (takes 1 minute):\n"
                    "1. Open https://myaccount.google.com/apppasswords in your browser\n"
                    "   (Ensure 2-Step Verification is turned ON in your Google Account)\n"
                    "2. Under 'App name', type 'CertApp' and click 'Create'\n"
                    "3. Copy the 16-letter password (e.g. abcd efgh ijkl mnop)\n"
                    "4. Paste it into the Password field in Email Settings and click 'Save & Close'!"
                )
            elif code == 535 or "badcredentials" in resp_str.lower() or "username and password not accepted" in resp_str.lower():
                if is_gmail:
                    err_msg = (
                        "❌ Gmail Login Failed (Error 535: Bad Credentials)\n\n"
                        "Google rejected the username or password.\n\n"
                        "Please check:\n"
                        f"• Username: Make sure '{self.settings.username}' is your full email address.\n"
                        "• Password: Must be an active 16-character App Password (https://myaccount.google.com/apppasswords).\n"
                        "  (Note: Regular Google account passwords will NOT work with Gmail SMTP)"
                    )
                else:
                    err_msg = (
                        f"❌ SMTP Authentication Failed (Error 535)\n\n"
                        f"Server rejected username '{self.settings.username}'.\n"
                        f"Details: {resp_str}\n"
                        "Please verify your username and password."
                    )
            else:
                err_msg = f"SMTP Authentication Failed (Code {code}):\n{resp_str or e}"

            logger.error(err_msg)
            return False, err_msg

        except smtplib.SMTPServerDisconnected as e:
            self._smtp_conn = None
            if is_gmail:
                err_msg = (
                    "🔑 Gmail Authentication Failed\n\n"
                    "Google disconnected because your account requires an App Password.\n"
                    "Regular Gmail account passwords are not accepted.\n\n"
                    "How to fix:\n"
                    "1. Open https://myaccount.google.com/apppasswords\n"
                    "2. Create an App Password for 'CertApp'\n"
                    "3. Paste the 16-character code into Email Settings."
                )
            else:
                err_msg = (
                    f"Server Disconnected: {host}:{port} closed the connection unexpectedly.\n"
                    "Verify your host, port, and security mode settings."
                )
            logger.error(err_msg)
            return False, err_msg

        except (ssl.SSLError, ssl.CertificateError) as e:
            self._smtp_conn = None
            err_str = str(e)
            if "wrong version number" in err_str.lower():
                err_msg = (
                    f"SSL/TLS Mode Mismatch:\n"
                    f"Port {port} does not match Security Mode '{sec_mode}'.\n\n"
                    f"• If using Port 587, set Security Mode to 'STARTTLS'.\n"
                    f"• If using Port 465, set Security Mode to 'SSL'."
                )
            else:
                err_msg = f"SSL/TLS Security Error: {e}"
            logger.error(err_msg)
            return False, err_msg

        except TimeoutError as e:
            self._smtp_conn = None
            err_msg = (
                f"Connection Timed Out: Could not reach {host}:{port} within 20 seconds.\n"
                "Please verify the host name, port, and network connection."
            )
            logger.error(err_msg)
            return False, err_msg

        except OSError as e:
            self._smtp_conn = None
            err_str = str(e)
            if "wrong version number" in err_str.lower():
                err_msg = (
                    f"SSL/TLS Mode Mismatch:\n"
                    f"Port {port} does not match Security Mode '{sec_mode}'.\n\n"
                    f"• If using Port 587, set Security Mode to 'STARTTLS'.\n"
                    f"• If using Port 465, set Security Mode to 'SSL'."
                )
            elif "connection refused" in err_str.lower():
                err_msg = f"Connection Refused: Server at {host}:{port} is not responding. Check port number."
            elif "name or service not known" in err_str.lower() or "nodename" in err_str.lower():
                err_msg = f"Host Not Found: Could not resolve '{host}'. Check the SMTP host name."
            else:
                err_msg = f"Network Error: {e}"
            logger.error(err_msg)
            return False, err_msg

        except Exception as e:
            self._smtp_conn = None
            err_msg = f"SMTP Connection Failed ({type(e).__name__}): {e}"
            logger.error(err_msg)
            return False, err_msg

    def disconnect(self) -> None:
        """Gracefully closes SMTP connection."""
        if self._smtp_conn:
            try:
                self._smtp_conn.quit()
            except Exception:
                pass
            self._smtp_conn = None

    @staticmethod
    def test_connection(settings: SMTPSettings, password: str) -> Tuple[bool, str]:
        """Static utility to test SMTP settings and login credentials."""
        mailer = SMTPMailer(settings, password)
        success, message = mailer.connect()
        mailer.disconnect()
        return success, message

    def _format_template(self, template_str: str, participant: Participant) -> str:
        """Formats email subject/body template with participant data."""
        try:
            return template_str.format(
                name=participant.name,
                email=participant.email,
                row_index=participant.row_index,
                **participant.extra_fields
            )
        except KeyError as ke:
            logger.warning(f"Missing template key {ke}, falling back to string replacement.")
            res = template_str.replace("{name}", participant.name).replace("{email}", participant.email)
            return res

    def send_single_email(
        self,
        participant: Participant,
        cert_path: str | Path,
        max_retries: int = 3
    ) -> SendResult:
        """Sends certificate email to a single participant with automatic retries."""
        cert_p = Path(cert_path)
        if not cert_p.exists():
            msg = f"Certificate file not found: {cert_path}"
            participant.send_status = "failed"
            participant.error_message = msg
            return SendResult(participant=participant, success=False, error=msg)

        subject = self._format_template(self.settings.subject_template, participant)
        body = self._format_template(self.settings.body_template, participant)

        # Build MIME Message
        msg = MIMEMultipart()
        sender_email = self.settings.sender_email or self.settings.username
        msg["From"] = f"{self.settings.sender_name} <{sender_email}>"
        msg["To"] = participant.email
        msg["Subject"] = subject

        # Body text (plain or HTML if contains tags)
        if "<html" in body.lower() or "<div" in body.lower() or "<p>" in body.lower():
            msg.attach(MIMEText(body, "html", "utf-8"))
        else:
            msg.attach(MIMEText(body, "plain", "utf-8"))

        # Attachment
        ext = cert_p.suffix.lower()
        with open(cert_p, "rb") as f:
            file_data = f.read()

        if ext in (".png", ".jpg", ".jpeg"):
            part = MIMEImage(file_data, name=cert_p.name)
        else:
            part = MIMEApplication(file_data, Name=cert_p.name)
            part["Content-Disposition"] = f'attachment; filename="{cert_p.name}"'

        msg.attach(part)

        # Send with retries
        last_error = ""
        for attempt in range(1, max_retries + 1):
            try:
                if not self._smtp_conn:
                    ok, conn_err = self.connect()
                    if not ok:
                        # Auth failure won't succeed on retry
                        last_error = conn_err
                        break

                self._smtp_conn.sendmail(
                    sender_email,
                    [participant.email],
                    msg.as_string()
                )

                participant.send_status = "sent"
                participant.error_message = None
                return SendResult(participant=participant, success=True, timestamp=time.strftime("%Y-%m-%d %H:%M:%S"))

            except smtplib.SMTPAuthenticationError as e:
                last_error = f"Authentication failed: {e}"
                logger.error(f"Auth error for {participant.email}: {last_error}")
                self.disconnect()
                break

            except (smtplib.SMTPException, OSError) as e:
                last_error = str(e)
                logger.warning(f"Attempt {attempt}/{max_retries} failed for {participant.email}: {last_error}")
                self.disconnect()  # Force reconnect next attempt
                if attempt < max_retries:
                    time.sleep(2 ** attempt)

        participant.send_status = "failed"
        participant.error_message = f"Failed: {last_error}"
        return SendResult(participant=participant, success=False, error=participant.error_message)

    def send_batch(
        self,
        participants: List[Participant],
        manifest_store: ManifestStore,
        progress_callback: Optional[Callable[[int, int, Participant, SendResult], None]] = None,
        stop_event: Optional[threading.Event] = None
    ) -> List[SendResult]:
        """Sends emails to a batch of participants with delay pacing and pause/cancel support.
        
        Raises SMTPConnectionError if initial connection fails.
        """
        results: List[SendResult] = []
        total = len(participants)

        # Establish connection FIRST and fail loudly if it doesn't work
        ok, conn_msg = self.connect()
        if not ok:
            raise SMTPConnectionError(conn_msg)

        try:
            for idx, p in enumerate(participants, 1):
                if stop_event and stop_event.is_set():
                    logger.info("Batch email sending cancelled.")
                    break

                # Skip invalid or missing certs
                if p.validation_status != "valid" or not p.certificate_path or not Path(p.certificate_path).exists():
                    p.send_status = "skipped"
                    p.error_message = "No valid certificate file generated."
                    manifest_store.update_participant(p)
                    res = SendResult(participant=p, success=False, error=p.error_message)
                    results.append(res)
                    if progress_callback:
                        progress_callback(idx, total, p, res)
                    continue

                res = self.send_single_email(p, p.certificate_path)
                manifest_store.update_participant(p)
                results.append(res)

                if progress_callback:
                    progress_callback(idx, total, p, res)

                # Delay pacing between emails
                if idx < total and self.settings.delay_seconds > 0:
                    time.sleep(self.settings.delay_seconds)

        finally:
            self.disconnect()

        return results
