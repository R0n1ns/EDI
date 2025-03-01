# import os
# from cryptography.hazmat.primitives import padding
# from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
# from cryptography.hazmat.backends import default_backend

#
# def encrypt_data(data: bytes, key: bytes) -> bytes:
#     """
#     Шифрует данные с помощью AES-256 в режиме CBC.
#     Возвращает IV (16 байт) + зашифрованные данные.
#     """
#     # Генерируем случайный вектор инициализации (IV)
#     iv = os.urandom(16)
#     # Создаем объект шифра AES-256 в режиме CBC
#     cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
#     encryptor = cipher.encryptor()
#
#     # Паддинг по PKCS7 для приведения данных к кратности 16 байт
#     padder = padding.PKCS7(128).padder()
#     padded_data = padder.update(data) + padder.finalize()
#
#     encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
#     # Возвращаем IV + зашифрованные данные (при дешифровании IV необходимо)
#     return iv + encrypted_data
