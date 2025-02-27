# utils.py

import pyotp
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

def generate_otp():
    """
    Генерирует 6-значный одноразовый пароль (OTP).
    """
    totp = pyotp.TOTP(pyotp.random_base32(), digits=6, interval=600)
    return totp.now()

def send_otp_email(recipient_email, otp_code):
    """
    Отправляет одноразовый пароль (OTP) на указанный email.
    """
    subject = "Ваш одноразовый пароль (OTP)"
    message = f"Ваш одноразовый пароль: {otp_code}. Он действителен в течение 10 минут."
    from_email = settings.DEFAULT_FROM_EMAIL

    send_mail(subject, message, from_email, [recipient_email], fail_silently=False)
