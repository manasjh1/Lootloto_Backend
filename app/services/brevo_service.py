import smtplib
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

_SMTP_HOST = "smtp-relay.brevo.com"
_SMTP_PORT = 587


def _send(to_email: str, to_name: str, subject: str, html: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{settings.BREVO_SENDER_NAME} <{settings.BREVO_SENDER_EMAIL}>"
    msg["To"]      = f"{to_name} <{to_email}>"
    msg.attach(MIMEText(html, "html"))
    try:
        with smtplib.SMTP(_SMTP_HOST, _SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.BREVO_SMTP_LOGIN, settings.BREVO_SMTP_PASSWORD)
            server.sendmail(settings.BREVO_SENDER_EMAIL, to_email, msg.as_string())
            print(f"[brevo] sent OK to {to_email}")
    except smtplib.SMTPAuthenticationError as e:
        print(f"[brevo] auth failed: {e}")
    except Exception as e:
        print(f"[brevo] error: {e}")


def _otp_digits(otp: str) -> str:
    """Build individual digit cells for the email template."""
    cells = ""
    for i, d in enumerate(otp):
        # space gap between digit 3 and 4
        gap = 18 if i == 3 else 8
        color = "#ff4438" if i >= 3 else "#f2eeec"
        border = "#ff4438" if i >= 3 else "#2a2624"
        if i > 0:
            cells += f'<td width="{gap}" style="width:{gap}px;">&nbsp;</td>'
        cells += f"""
        <td width="46" height="60" align="center" valign="middle" bgcolor="#141212"
            style="width:46px;height:60px;background-color:#141212;border:1px solid {border};
                   border-radius:10px;font-family:'Courier New',Courier,monospace;
                   font-size:30px;font-weight:bold;color:{color};line-height:60px;
                   mso-line-height-rule:exactly;">{d}</td>"""
    return cells


async def send_verification_email(to_email: str, first_name: str, otp: str) -> None:
    expires_ist = datetime.now(timezone.utc) + timedelta(minutes=10)
    expires_str = expires_ist.strftime("%-d %b %Y, %-I:%M %p UTC")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Your LootLooto verification code</title>
<style>
  @media only screen and (max-width:620px){{
    .pad{{padding-left:22px !important;padding-right:22px !important}}
    .digit{{width:40px !important;height:52px !important;font-size:26px !important;line-height:52px !important}}
  }}
</style>
</head>
<body style="margin:0;padding:0;background-color:#141212;">
<span style="display:none !important;visibility:hidden;opacity:0;color:transparent;height:0;width:0;overflow:hidden;font-size:1px;line-height:1px;">Your LootLooto code is {otp[:3]} {otp[3:]}. It expires in 10 minutes. Don't share it with anyone.</span>

<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color:#141212;">
<tr><td align="center" style="padding:28px 12px;">
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="600" style="width:600px;max-width:600px;background-color:#1c1918;border-radius:16px;">

  <!-- header -->
  <tr>
    <td class="pad" style="padding:26px 32px;border-bottom:1px solid #2a2624;">
      <table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
        <td width="34" height="34" align="center" valign="middle" bgcolor="#ff4438"
            style="width:34px;height:34px;border-radius:9px;font-family:Arial,Helvetica,sans-serif;
                   font-size:13px;font-weight:bold;color:#141212;line-height:34px;">LT</td>
        <td width="10">&nbsp;</td>
        <td style="font-family:Arial,Helvetica,sans-serif;font-size:15px;font-weight:bold;color:#f2eeec;">LootLooto</td>
      </tr></table>
    </td>
  </tr>

  <!-- icon -->
  <tr>
    <td class="pad" align="left" style="padding:40px 32px 8px;">
      <table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
        <td width="56" height="56" align="center" valign="middle" bgcolor="#2a1210"
            style="width:56px;height:56px;border-radius:14px;font-family:Arial,Helvetica,sans-serif;
                   font-size:26px;line-height:56px;color:#ff4438;">&#128274;</td>
      </tr></table>
    </td>
  </tr>

  <!-- heading -->
  <tr><td class="pad" align="left" style="padding:20px 32px 6px;">
    <div style="font-family:Arial,Helvetica,sans-serif;font-size:28px;line-height:34px;font-weight:bold;color:#f2eeec;letter-spacing:-0.6px;">
      Confirm it's you, {first_name}
    </div>
  </td></tr>
  <tr><td class="pad" align="left" style="padding:0 32px 24px;">
    <div style="font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:23px;color:#a89f9c;">
      Enter the 6-digit code below on the LootLooto verification screen. This code expires in <strong style="color:#f2eeec;">10 minutes</strong>.
    </div>
  </td></tr>

  <!-- OTP digits -->
  <tr><td class="pad" align="center" style="padding:0 32px 12px;">
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" bgcolor="#242020"
           style="background-color:#242020;border-radius:14px;">
    <tr><td align="center" style="padding:32px 16px 22px;">
      <div style="font-family:Arial,Helvetica,sans-serif;font-size:11px;letter-spacing:1.6px;color:#ff4438;font-weight:bold;margin-bottom:14px;">YOUR CODE</div>
      <table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center">
        <tr>{_otp_digits(otp)}</tr>
      </table>
      <div style="font-family:Arial,Helvetica,sans-serif;font-size:12px;color:#8c8380;padding-top:18px;">
        Expires <strong style="color:#f2eeec;">{expires_str}</strong>
      </div>
    </td></tr>
    </table>
  </td></tr>

  <!-- security note -->
  <tr><td class="pad" style="padding:16px 32px 30px;">
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" bgcolor="#2a1210"
           style="background-color:#2a1210;border-radius:12px;">
    <tr>
      <td width="46" valign="top" align="center" style="width:46px;padding:16px 0 16px 16px;font-family:Arial,Helvetica,sans-serif;font-size:20px;color:#ff4438;line-height:20px;">&#9888;</td>
      <td valign="top" style="padding:16px;font-family:Arial,Helvetica,sans-serif;font-size:13px;line-height:20px;color:#e8b8b3;">
        <strong style="color:#ff4438;">Never share this code.</strong> LootLooto will never ask you for it over phone, chat, or email.
      </td>
    </tr>
    </table>
  </td></tr>

  <!-- footer -->
  <tr><td class="pad" style="padding:22px 32px 28px;border-top:1px solid #2a2624;">
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
    <tr><td style="font-family:Arial,Helvetica,sans-serif;font-size:12px;line-height:19px;color:#6b6360;padding-bottom:12px;">
      You're getting this because someone (hopefully you) tried to sign up to LootLooto.<br>
      LootLooto, India
    </td></tr>
    </table>
  </td></tr>

</table>
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="600" style="width:600px;max-width:600px;">
<tr><td align="center" style="padding:20px 12px 0;font-family:Arial,Helvetica,sans-serif;font-size:11px;color:#5c5552;">
  &copy; 2026 LootLooto &middot; This is a transactional email
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""

    _send(to_email, first_name, "Your LootLooto verification code", html)


async def send_welcome_email(to_email: str, first_name: str) -> None:
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;padding:32px;background:#1c1918;border-radius:16px;color:#f2eeec;">
      <div style="background:#ff4438;color:#141212;width:34px;height:34px;border-radius:9px;font-weight:bold;font-size:13px;display:inline-flex;align-items:center;justify-content:center;margin-bottom:24px;">LT</div>
      <h2 style="margin:0 0 12px;font-size:26px;">You're in, {first_name}!</h2>
      <p style="color:#a89f9c;margin:0 0 24px;">Your account is verified. Get first pick of every drop.</p>
      <a href="{settings.FRONTEND_URL}" style="display:inline-block;background:#ff4438;color:#141212;padding:13px 28px;border-radius:10px;text-decoration:none;font-weight:bold;">Start shopping</a>
    </div>
    """
    _send(to_email, first_name, "Welcome to LootLooto!", html)