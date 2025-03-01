import io
from minio import Minio
from django.conf import settings


def get_minio_client():
    """
    Инициализирует и возвращает экземпляр Minio клиента.
    """
    client = Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )
    return client


def ensure_bucket_exists(bucket_name: str):
    """
    Проверяет наличие бакета и создает его, если он отсутствует.
    """
    client = get_minio_client()
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)


def upload_file_to_minio(saved_filename: str, file_content: bytes, content_type: str):
    """
    Загружает файл в MinIO.

    :param saved_filename: Уникальное имя файла в MinIO.
    :param file_content: Содержимое файла (байты).
    :param content_type: MIME-тип файла.
    """
    client = get_minio_client()
    bucket_name = settings.MINIO_BUCKET_NAME
    ensure_bucket_exists(bucket_name)

    data_stream = io.BytesIO(file_content)
    data_length = len(file_content)

    client.put_object(
        bucket_name,
        saved_filename,
        data_stream,
        data_length,
        content_type=content_type
    )


def download_file_from_minio(saved_filename: str):
    """
    Скачивает файл из MinIO.

    :param saved_filename: Имя файла в MinIO.
    :return: Объект-ответ, поддерживающий метод read() (поток).
    """
    client = get_minio_client()
    bucket_name = settings.MINIO_BUCKET_NAME
    response = client.get_object(bucket_name, saved_filename)
    return response

def delete_file_from_minio(saved_filename: str):
    """
    Скачивает файл из MinIO.

    :param saved_filename: Имя файла в MinIO.
    :return: Объект-ответ, поддерживающий метод read() (поток).
    """
    client = get_minio_client()
    bucket_name = settings.MINIO_BUCKET_NAME
    response = client.remove_object(bucket_name, saved_filename)
    return response