"""
Email utility for the GPSL Approvals Workflow.

Uses Python's built-in smtplib so no extra pip dependencies are needed.
Configure SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASSWORD in .env.
"""
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_reset_email(to_email: str, reset_link: str) -> None:
    """
    Send a password-reset email to *to_email* containing *reset_link*.

    Raises:
        RuntimeError: if SMTP credentials are not configured or sending fails.
    """
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        raise RuntimeError(
            "SMTP credentials are not configured. "
            "Set SMTP_USER and SMTP_PASSWORD in your .env file."
        )

    subject = "Reset your Greenpower SL password"
    expire_mins = settings.RESET_TOKEN_EXPIRE_MINUTES

    # -- Plain-text fallback --------------------------------------------------
    text_body = (
        f"Hi,\n\n"
        f"We received a request to reset the password for the Greenpower SL\n"
        f"Approvals Workflow account associated with this email address.\n\n"
        f"Click the link below to set a new password (valid for {expire_mins} minutes):\n\n"
        f"{reset_link}\n\n"
        f"If you did not request a password reset, you can safely ignore this\n"
        f"email -- your password will remain unchanged.\n\n"
        f"-- Greenpower SL Management (Private) Limited\n"
    )

    # -- HTML body ------------------------------------------------------------
    html_body = f"""\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f6f8;font-family:'Segoe UI',Arial,Helvetica,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f8;padding:40px 0;">
    <tr><td align="center">
      <table width="480" cellpadding="0" cellspacing="0"
             style="background:#ffffff;border-radius:8px;box-shadow:0 2px 12px rgba(0,0,0,.07);overflow:hidden;">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#06301f,#127a4e);padding:32px 40px;">
            <p style="margin:0;font-size:18px;font-weight:700;color:#ffffff;letter-spacing:-.2px;">
              Greenpower SL
              <span style="display:block;font-size:12px;font-weight:400;color:rgba(255,255,255,.72);
                           letter-spacing:.6px;text-transform:uppercase;margin-top:2px;">
                Approvals Workflow
              </span>
            </p>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:36px 40px 24px;">
            <h1 style="margin:0 0 14px;font-size:20px;font-weight:600;color:#101820;">
              Reset your password
            </h1>
            <p style="margin:0 0 10px;font-size:14px;color:#374151;line-height:1.6;">
              We received a request to reset the password for the Greenpower SL
              Approvals Workflow account associated with this address.
            </p>
            <p style="margin:0 0 28px;font-size:14px;color:#374151;line-height:1.6;">
              Click the button below to choose a new password.
              This link is valid for <strong>{expire_mins} minutes</strong>.
            </p>

            <!-- CTA button -->
            <table cellpadding="0" cellspacing="0">
              <tr>
                <td style="border-radius:6px;background:#0b5d3b;">
                  <a href="{reset_link}"
                     style="display:inline-block;padding:13px 28px;font-size:14px;
                            font-weight:600;color:#ffffff;text-decoration:none;border-radius:6px;">
                    Set new password
                  </a>
                </td>
              </tr>
            </table>

            <p style="margin:28px 0 0;font-size:12px;color:#6b7280;line-height:1.6;">
              If the button above does not work, copy and paste this link into your browser:<br>
              <a href="{reset_link}" style="color:#127a4e;word-break:break-all;">{reset_link}</a>
            </p>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="padding:20px 40px 32px;border-top:1px solid #e5e7eb;">
            <p style="margin:0;font-size:11.5px;color:#9ca3af;line-height:1.6;">
              If you did not request a password reset, you can safely ignore this
              email -- your password will not be changed.<br><br>
              Greenpower SL Management (Private) Limited, Colombo.
              Authorised users only. All activity is logged.
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>
"""

    # -- Build the MIME message -----------------------------------------------
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Greenpower SL Approvals <{settings.SMTP_USER}>"
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    # -- Send via STARTTLS ----------------------------------------------------
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USER, to_email, msg.as_string())
        logger.info("Password-reset email sent to %s", to_email)
    except smtplib.SMTPAuthenticationError as exc:
        logger.error("SMTP authentication failed: %s", exc)
        raise RuntimeError(
            "Email authentication failed. Check SMTP_USER and SMTP_PASSWORD in .env."
        ) from exc
    except Exception as exc:
        logger.error("Failed to send reset email to %s: %s", to_email, exc)
        raise RuntimeError(f"Failed to send reset email: {exc}") from exc
