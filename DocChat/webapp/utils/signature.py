# import base64
# import os
# from hashlib import sha256
#
# from cryptography.hazmat.backends import default_backend
# from django.utils.timezone import make_aware
# from pyhanko.keys import load_cert_from_pemder, load_certs_from_pemder
# from pyhanko.sign import signers
# from pyhanko.pdf_utils.reader import PdfFileReader
# from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
# from pyhanko.sign.signers.pdf_signer import PdfSignatureMetadata, PdfSigner
# from pyhanko.sign.fields import append_signature_field, SigFieldSpec
# from pyhanko.sign.validation import validate_pdf_signature
# from pyhanko_certvalidator import ValidationContext
# from pyhanko_certvalidator.registry import SimpleCertificateStore
# from webapp.models import Document, DigitalCertificate, PdfSignatureLog
# from cryptography.hazmat.primitives.asymmetric import rsa
# from cryptography.hazmat.primitives import hashes, serialization
# from cryptography import x509
# from cryptography.x509.oid import NameOID
# from cryptography.hazmat.primitives.serialization import pkcs12
# import io
# from datetime import datetime, timedelta
# from webapp.utils.minio_client import upload_file_to_minio, download_file_from_minio
#
# def create_and_save_certificate(user, pkcs12_password: bytes, validity_days=365):
#     private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
#     subject = issuer = x509.Name([
#         x509.NameAttribute(NameOID.COUNTRY_NAME, u"RU"),
#         x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Moscow"),
#         x509.NameAttribute(NameOID.LOCALITY_NAME, u"Moscow"),
#         x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Your Organization"),
#         x509.NameAttribute(NameOID.COMMON_NAME, user.username),
#     ])
#     valid_from = datetime.utcnow()
#     valid_to = valid_from + timedelta(days=10)
#     certificate = (x509.CertificateBuilder()
#         .subject_name(subject)
#         .issuer_name(issuer)
#         .public_key(private_key.public_key())
#         .serial_number(x509.random_serial_number())
#         .not_valid_before(valid_from)
#         .not_valid_after(valid_to)
#         .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
#         .sign(private_key, hashes.SHA256()))
#     certificate_pem = certificate.public_bytes(serialization.Encoding.PEM).decode('utf-8')
#     friendly_name = user.username.encode('utf-8')
#     pkcs12_data = pkcs12.serialize_key_and_certificates(
#         name=friendly_name, key=private_key, cert=certificate, cas=None,
#         encryption_algorithm=serialization.BestAvailableEncryption(pkcs12_password))
#     encrypted_private_key_b64 = base64.b64encode(pkcs12_data).decode('utf-8')
#     digital_cert = DigitalCertificate.objects.create(
#         user=user, serial_number=str(certificate.serial_number), certificate_pem=certificate_pem,
#         issued_at=make_aware(valid_from), expires_at=make_aware(valid_to),
#         encrypted_private_key=encrypted_private_key_b64, is_revoked=False)
#     return digital_cert
#
# def load_signer(cert: DigitalCertificate, pkcs12_password: bytes) -> signers.SimpleSigner:
#     """
#     Загружает подписывающий объект (SimpleSigner) из PKCS#12 контейнера
#     или из зашифрованного закрытого ключа (если файл отсутствует).
#
#     :param cert: Экземпляр DigitalCertificate.
#     :param pkcs12_password: Пароль для PKCS#12 файла (в байтах).
#     :return: Объект SimpleSigner.
#     :raises ValueError: если нет подходящих данных.
#     """
#     # Вариант 1: Есть файл PKCS#12
#     if cert.pkcs12_file:
#         pfx_path = cert.pkcs12_file.path
#         signer = signers.SimpleSigner.load_pkcs12(
#             pfx_path,
#             pkcs12_password
#         )
#         return signer
#
#     # Вариант 2: Есть зашифрованный ключ в базе
#     elif cert.encrypted_private_key and cert.certificate_pem:
#         try:
#             # Расшифровка PKCS#12 контейнера
#             encrypted_bytes = base64.b64decode(cert.encrypted_private_key)
#             private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
#                 encrypted_bytes,
#                 pkcs12_password,
#                 backend=default_backend()
#             )
#
#             # Создаем cert_registry
#             cert_registry = SimpleCertificateStore()
#
#             # Загружаем сертификат из PEM-формата (cert.certificate_pem)
#             pem_bytes = cert.certificate_pem.encode('utf-8')
#             pyhanko_certs = list(load_certs_from_pemder(pem_bytes))
#             for pyhanko_cert in pyhanko_certs:
#                 cert_registry.register(pyhanko_cert)
#
#             # Если есть дополнительные сертификаты, добавляем их
#             if additional_certs:
#                 for add_cert in additional_certs:
#                     # Конвертируем сертификат cryptography в PEM и загружаем
#                     add_cert_pem = add_cert.public_bytes(serialization.Encoding.PEM)
#                     add_pyhanko_certs = list(load_certs_from_pemder(add_cert_pem))
#                     for add_pyhanko_cert in add_pyhanko_certs:
#                         cert_registry.register(add_pyhanko_cert)
#
#             # Создаем SimpleSigner с cert_registry
#             signer = signers.SimpleSigner(
#                 signing_cert=certificate,
#                 signing_key=private_key,
#                 cert_registry=cert_registry
#             )
#             return signer
#         except Exception as e:
#             raise ValueError(f"Ошибка загрузки PKCS#12 из базы: {e}")
#
#     else:
#         raise ValueError("Нет доступных данных для загрузки подписи (ни файла, ни ключа в базе)")
#
# def sign_pdf_document(document: Document, certificate: DigitalCertificate, pkcs12_password: bytes,
#                      signature_field_name: str = "Signature1", notes: str = None) -> str:
#     resp = download_file_from_minio(document)
#     orig_bytes = resp.read()
#     reader = io.BytesIO(orig_bytes)
#     writer = IncrementalPdfFileWriter(reader)
#     spec = SigFieldSpec(sig_field_name=signature_field_name)
#     append_signature_field(writer, spec)
#     signer = load_signer(certificate, pkcs12_password)
#     meta = PdfSignatureMetadata(field_name=signature_field_name)
#     pdf_signer = PdfSigner(signature_meta=meta, signer=signer, new_field_spec=spec)
#     signed_io = io.BytesIO()
#     pdf_signer.sign_pdf(writer, output=signed_io)
#     signed_bytes = signed_io.getvalue()
#     doc_hash = sha256(signed_bytes).hexdigest()
#     version_id = upload_file_to_minio(document, signed_bytes, document.content_type,
#                                      notes or f"Signed by {certificate.user.username}")
#     PdfSignatureLog.objects.create(document=document, certificate=certificate, document_hash=doc_hash,
#                                  signature_data="", notes=notes)
#     return version_id
#
# def verify_pdf_bytes(input_bytes: bytes, trust_roots_pem: list[str]) -> list[str]:
#     roots = [load_cert_from_pemder(cr.encode('utf-8')) for cr in trust_roots_pem]
#     vc = ValidationContext(trust_roots=roots)
#     reader = PdfFileReader(io.BytesIO(input_bytes))
#     verified_cn = []
#     for sig in reader.embedded_signatures:
#         status = validate_pdf_signature(sig, vc)
#         if status.trusted and status.signer_cert:
#             attrs = status.signer_cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
#             if attrs:
#                 verified_cn.append(attrs[0].value)
#     return verified_cn
#
