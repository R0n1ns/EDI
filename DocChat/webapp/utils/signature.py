import hashlib
import datetime
from io import BytesIO
from django.utils import timezone
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from webapp.models import DocumentSignature
from minio import Minio
from django.conf import settings
from webapp.utils.minio_client import (
    get_minio_file_url,
    download_file_from_minio,
    upload_new_version_file_to_minio
)
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


def hash_pdf(minio_filename):
    """
    Вычисляет хэш файла PDF, используя MinIO.
    """
    hasher = hashlib.sha256()
    file_stream = download_file_from_minio(minio_filename)

    while chunk := file_stream.read(4096):
        hasher.update(chunk)

    return hasher.digest()  # Возвращаем бинарный хэш


def sign_document(user, minio_filename, show_table=True):
    """
    Подписывает документ, хранящийся в MinIO.
    """
    doc_hash = hash_pdf(minio_filename)

    # Загрузка приватного ключа пользователя
    private_key = serialization.load_pem_private_key(
        user.certificate.private_key.encode(),
        password=None
    )

    # Подписание хэша документа
    signature = private_key.sign(
        doc_hash,
        padding.PKCS1v15(),
        hashes.SHA256()
    )

    # Сохраняем подпись в базе
    DocumentSignature.objects.create(
        document_filename=minio_filename,
        user=user,
        signature=signature.hex()
    )

    if show_table:
        add_signature_table(minio_filename, user, timezone.now())


def verify_signatures(minio_filename):
    """
    Проверяет подписи документа, хранящегося в MinIO.
    """
    doc_hash = hash_pdf(minio_filename)
    signatures = DocumentSignature.objects.filter(document_filename=minio_filename)
    verified_signers = []

    for sig in signatures:
        # Загружаем публичный ключ из сертификата пользователя
        certificate = sig.user.certificate
        public_key = serialization.load_pem_public_key(
            certificate.certificate_file.encode()
        )

        try:
            # Проверяем подпись
            public_key.verify(
                bytes.fromhex(sig.signature),
                doc_hash,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            verified_signers.append(sig.user.full_name)
        except Exception:
            continue  # Подпись недействительна

    return verified_signers


def add_signature_table(minio_filename, user, timestamp):
    """
    Добавляет таблицу подписей в PDF файл и сохраняет новую версию в MinIO.
    """
    file_stream = download_file_from_minio(minio_filename)

    # Преобразуем поток в BytesIO
    pdf_data = BytesIO(file_stream.read())
    pdf_data.seek(0)

    existing_pdf = PdfReader(pdf_data)
    output_pdf = PdfWriter()

    # Генерация страницы с информацией о подписи
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    can.drawString(100, 100, f"Подписано: {user.full_name} {timestamp}")
    can.save()
    packet.seek(0)
    new_pdf = PdfReader(packet)

    # Мерджинг старого и нового содержимого
    for page in existing_pdf.pages:
        page.merge_page(new_pdf.pages[0])
        output_pdf.add_page(page)

    # Сохранение новой версии подписанного файла в MinIO
    signed_pdf_content = BytesIO()
    output_pdf.write(signed_pdf_content)
    signed_pdf_content.seek(0)

    new_filename = upload_new_version_file_to_minio(
        minio_filename, signed_pdf_content.read(), 'application/pdf'
    )

    return new_filename