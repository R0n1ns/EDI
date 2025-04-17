# Generated by Django 5.1.6 on 2025-04-16 19:12

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("webapp", "0008_remove_documentsignature_document_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="DigitalCertificate",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("serial_number", models.CharField(max_length=100, unique=True)),
                (
                    "certificate_pem",
                    models.TextField(help_text="Открытый сертификат в формате PEM"),
                ),
                (
                    "pkcs12_file",
                    models.FileField(
                        blank=True,
                        help_text="PKCS#12 контейнер (с расширением .p12/.pfx) с закрытым ключом",
                        null=True,
                        upload_to="certificates/",
                    ),
                ),
                ("issued_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("expires_at", models.DateTimeField()),
                ("is_revoked", models.BooleanField(default=False)),
                (
                    "encrypted_private_key",
                    models.TextField(
                        blank=True,
                        help_text="Зашифрованный закрытый ключ (если хранится в БД)",
                        null=True,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="certificates",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="PdfSignatureLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("signature_date", models.DateTimeField(auto_now_add=True)),
                (
                    "document_hash",
                    models.CharField(
                        help_text="Хэш подписанного документа", max_length=255
                    ),
                ),
                (
                    "signature_data",
                    models.TextField(
                        blank=True,
                        help_text="Данные подписи (например, в base64-формате)",
                        null=True,
                    ),
                ),
                ("notes", models.TextField(blank=True, null=True)),
                (
                    "certificate",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="webapp.digitalcertificate",
                    ),
                ),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pdf_signatures",
                        to="webapp.document",
                    ),
                ),
            ],
        ),
    ]
