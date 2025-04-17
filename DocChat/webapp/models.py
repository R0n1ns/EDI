from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import secrets

class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    level = models.IntegerField(default=0)
    permissions = models.JSONField(default=dict, blank=True, null=True)
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
    oauth_provider = models.CharField(max_length=20, blank=True, null=True)
    oauth_id = models.CharField(max_length=100, blank=True, null=True)

    # Дополнительные данные пользователя
    full_name = models.CharField("ФИО", max_length=255, blank=True, null=True)
    job_title = models.CharField("Должность", max_length=100, blank=True, null=True)

    # Права пользователя (каждое можно включать/выключать)
    can_manage_documents = models.BooleanField(default=True)      # загрузка/выгрузка/удаление своих документов
    can_forward_documents = models.BooleanField(default=False)      # отправка/перенаправление документов
    can_create_documents = models.BooleanField(default=True)        # создание документов
    can_sign_documents = models.BooleanField(default=False)         # подпись документов
    can_view_statistics = models.BooleanField(default=False)        # доступ к статистической информации
    can_modify_groups = models.BooleanField(default=False)          # доступ к изменению групп
    can_modify_users = models.BooleanField(default=False)           # выдача прав

    def generate_otp(self):
        self.otp = ''.join(secrets.choice('0123456789') for _ in range(6))
        self.otp_created_at = timezone.now()
        self.save(update_fields=['otp', 'otp_created_at'])
        return self.otp

    def verify_otp(self, otp):
        if not self.otp or not self.otp_created_at:
            return False
        time_diff = timezone.now() - self.otp_created_at
        if time_diff.total_seconds() > 600:
            return False
        return self.otp == otp

    @classmethod
    def get_or_create_oauth_user(cls, email, username, provider, provider_id):
        user, created = cls.objects.get_or_create(email=email, defaults={
            'username': username,
            'oauth_provider': provider,
            'oauth_id': provider_id,
            'is_email_verified': True,
        })
        return user

class UserGroup(models.Model):
    name = models.CharField(max_length=100, unique=True)
    members = models.ManyToManyField(CustomUser, related_name='custom_groups', blank=True)
    leader = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='leading_groups'
    )

    def __str__(self):
        return self.name

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
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='owned_documents')
    is_encrypted = models.BooleanField(default=False)
    upload_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')

    # Параметры отправки/общего доступа:
    shared_users = models.ManyToManyField(CustomUser, related_name='shared_documents', blank=True)
    shared_groups = models.ManyToManyField(UserGroup, related_name='shared_documents', blank=True)

    def __str__(self):
        return self.original_filename

class DocumentTransferHistory(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='transfer_history')
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_document_transfers')
    recipient_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='received_document_transfers')
    recipient_group = models.ForeignKey(UserGroup, on_delete=models.CASCADE, null=True, blank=True, related_name='received_document_transfers')
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Transfer of {self.document} from {self.sender} at {self.timestamp}"

class AuditLog(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='audit_logs')
    action = models.CharField(max_length=50)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField()

    def __str__(self):
        return f"{self.user} - {self.action} at {self.timestamp}"


class DocumentVersionHistory(models.Model):
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='version_history'
    )
    version_id = models.CharField(max_length=255)
    file_size = models.BigIntegerField(null=True, blank=True)
    etag = models.CharField(max_length=100, blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Version {self.version_id} of {self.document.original_filename} at {self.timestamp}"


# Модель для хранения цифровых сертификатов (ЭЦП)
class DigitalCertificate(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='certificates')
    serial_number = models.CharField(max_length=100, unique=True)
    certificate_pem = models.TextField(help_text="Открытый сертификат в формате PEM")
    pkcs12_file = models.FileField(
        upload_to='certificates/', blank=True, null=True,
        help_text="PKCS#12 контейнер (с расширением .p12/.pfx) с закрытым ключом"
    )
    issued_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    is_revoked = models.BooleanField(default=False)
    # Если храните закрытый ключ в БД – обязательно шифруйте его
    encrypted_private_key = models.TextField(
        blank=True, null=True,
        help_text="Зашифрованный закрытый ключ (если хранится в БД)"
    )

    def __str__(self):
        return f"Certificate {self.serial_number} for {self.user}"

# Модель для логирования операций подписания PDF
class PdfSignatureLog(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='pdf_signatures')
    certificate = models.ForeignKey(DigitalCertificate, on_delete=models.SET_NULL, null=True, blank=True)
    signature_date = models.DateTimeField(auto_now_add=True)
    document_hash = models.CharField(max_length=255, help_text="Хэш подписанного документа")
    signature_data = models.TextField(
        blank=True, null=True,
        help_text="Данные подписи (например, в base64-формате)"
    )
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Signature for {self.document} on {self.signature_date}"