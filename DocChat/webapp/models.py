from django.db import models

# Create your models here.
# your_app/models.py

from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import secrets
from django.db import models
from django.contrib.auth.models import User

class Document(models.Model):
    STATUS_CHOICES = [
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    filename = models.CharField(max_length=255)
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=50)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    is_encrypted = models.BooleanField(default=False)
    upload_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')

class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    level = models.IntegerField(default=0)
    permissions = models.JSONField(default=dict, blank=True, null=True)
    # Для иерархии: ссылка на родительскую роль (self-ссылка)
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children'
    )

    def __str__(self):
        return self.name

    @classmethod
    def init_roles(cls):
        """
        Инициализирует роли, если они ещё не созданы.
        Можно вызывать, например, из management-команды или в signals.
        """
        roles = {
            'admin': {'level': 3, 'description': 'Administrator with full access'},
            'manager': {'level': 2, 'description': 'Manager with department access'},
            'user': {'level': 1, 'description': 'Regular user with basic access'}
        }
        for role_name, data in roles.items():
            if not cls.objects.filter(name=role_name).exists():
                cls.objects.create(
                    name=role_name,
                    level=data['level'],
                    description=data['description'],
                    permissions={}
                )

class CustomUser(AbstractUser):
    # Наследуем стандартные поля AbstractUser: username, password, first_name, last_name и т.д.
    email = models.EmailField(unique=True)
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )
    is_email_verified = models.BooleanField(default=False)
    otp = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(blank=True, null=True)
    # Поля для OAuth
    oauth_provider = models.CharField(max_length=20, blank=True, null=True)
    oauth_id = models.CharField(max_length=100, blank=True, null=True)

    def generate_otp(self):
        """Генерирует 6-значный OTP и сохраняет время создания"""
        self.otp = ''.join(secrets.choice('0123456789') for _ in range(6))
        self.otp_created_at = timezone.now()
        self.save(update_fields=['otp', 'otp_created_at'])
        return self.otp

    def verify_otp(self, otp):
        """Проверяет соответствие OTP и срок его действия (10 минут)"""
        if not self.otp or not self.otp_created_at:
            return False

        time_diff = timezone.now() - self.otp_created_at
        if time_diff.total_seconds() > 600:  # 10 минут = 600 секунд
            return False

        return self.otp == otp

    @classmethod
    def get_or_create_oauth_user(cls, email, username, provider, provider_id):
        """
        Находит пользователя по email или создаёт нового для OAuth-аутентификации.
        """
        user, created = cls.objects.get_or_create(email=email, defaults={
            'username': username,
            'oauth_provider': provider,
            'oauth_id': provider_id,
            'is_email_verified': True,  # OAuth-пользователи считаются проверенными
        })
        return user


class Document(models.Model):
    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('in_progress', 'В работе'),
        ('approved', 'Подтвержден'),
        ('rejected', 'Отказ'),
    ]

    filename = models.CharField(max_length=255)
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=50)
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    is_encrypted = models.BooleanField(default=False)
    upload_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')


class AuditLog(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=50)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField()

    def __str__(self):
        return f"{self.user} - {self.action} at {self.timestamp}"
