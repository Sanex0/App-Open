import os, smtplib
try:
    from dotenv import load_dotenv
    # Load .env from project root
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    dotenv_path = os.path.join(base, '.env')
    load_dotenv(dotenv_path)
except Exception:
    # If python-dotenv is not available, assume env vars are already set
    pass
from email.message import EmailMessage

MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
MAIL_USER = os.environ.get('MAIL_USERNAME')
MAIL_PASS = os.environ.get('MAIL_PASSWORD')
MAIL_TLS = os.environ.get('MAIL_USE_TLS', '1') == '1'
MAIL_SSL = os.environ.get('MAIL_USE_SSL', '0') == '1'
TO = MAIL_USER  # te envía el test a la misma cuenta para comprobar

msg = EmailMessage()
msg['Subject'] = 'Prueba SMTP'
msg['From'] = MAIL_USER
msg['To'] = TO
msg.set_content('Test de conexión SMTP desde smtp_test.py')

try:
    print('Using SMTP server:', MAIL_SERVER, 'port:', MAIL_PORT)
    print('MAIL_USERNAME set?:', bool(MAIL_USER))
    print('MAIL_PASSWORD set?:', bool(MAIL_PASS))
    if MAIL_SSL or MAIL_PORT == 465:
        with smtplib.SMTP_SSL(MAIL_SERVER, MAIL_PORT) as s:
            s.set_debuglevel(1)
            if MAIL_USER and MAIL_PASS: s.login(MAIL_USER, MAIL_PASS)
            s.send_message(msg)
    else:
        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT, timeout=10) as s:
            s.set_debuglevel(1)
            s.ehlo()
            if MAIL_TLS: s.starttls()
            s.ehlo()
            if MAIL_USER and MAIL_PASS: s.login(MAIL_USER, MAIL_PASS)
            s.send_message(msg)
    print('OK: correo enviado')
except Exception as e:
    print('ERROR:', repr(e))