
from django.http import HttpResponse, Http404, FileResponse
from django.contrib.auth import authenticate, login, logout
from .models import CustomUser, AuditLog
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.utils.timezone import now
from .utils.otp_email import generate_otp, send_otp_email
from datetime import datetime

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Document, AuditLog
# from .utils.encryption import encrypt_data  # Импортируем функцию шифрования
from .utils.minio_client import *
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import Document
User = get_user_model()

def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    # Проверяем, на каком этапе регистрации находится пользователь
    show_otp_field = request.session.get("registration_email") is not None

    if request.method == "POST":
        if not show_otp_field:
            # Шаг 1: Пользователь заполняет форму регистрации
            email = request.POST.get("email")
            username = request.POST.get("username")
            password = request.POST.get("password")

            if CustomUser.objects.filter(email=email).exists():
                messages.error(request, "Этот email уже зарегистрирован.")
                return redirect("register")

            # Проверка корпоративного email
            if not (email.endswith("@company.com") or email.endswith("@corporate.org")):
                messages.error(request, "Пожалуйста, используйте корпоративный email.")
                return redirect("register")

            # Сохраняем данные пользователя в сессии
            request.session["registration_email"] = email
            request.session["registration_username"] = username
            request.session["registration_password"] = password

            # Генерируем и отправляем OTP
            otp_code = generate_otp()
            request.session["registration_otp"] = otp_code
            request.session["registration_otp_time"] = now().isoformat()
            send_otp_email(email, otp_code)

            messages.info(request, "Код подтверждения отправлен на ваш email.")
            return render(request, "register.html", {"show_otp_field": True})
        else:
            # Шаг 2: Пользователь вводит OTP
            otp_input = request.POST.get("otp")
            otp_stored = request.session.get("registration_otp")
            otp_time = request.session.get("registration_otp_time")

            # Проверяем, что OTP был отправлен и не истек
            if otp_stored and otp_time:
                otp_age = now() - timezone.datetime.fromisoformat(otp_time)
                if otp_age > timedelta(minutes=10):
                    messages.error(request, "Срок действия кода истек. Пожалуйста, зарегистрируйтесь снова.")
                    return redirect("register")

                if otp_input == otp_stored:
                    # Создаем нового пользователя
                    user = CustomUser.objects.create_user(
                        username=request.session["registration_username"],
                        email=request.session["registration_email"],
                        password=request.session["registration_password"],
                        is_email_verified=True
                    )
                    user.backend = 'django.contrib.auth.backends.ModelBackend'
                    login(request, user)

                    # Очищаем данные сессии
                    for key in ["registration_email", "registration_username", "registration_password", "registration_otp", "registration_otp_time"]:
                        request.session.pop(key, None)

                    messages.success(request, "Регистрация прошла успешно!")
                    return redirect("dashboard")
                else:
                    messages.error(request, "Неверный код подтверждения.")
            else:
                messages.error(request, "Код подтверждения не найден или истек.")
            return render(request, "register.html", {"show_otp_field": True})

    return render(request, "register.html", {"show_otp_field": show_otp_field})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    show_otp_field = request.session.get("login_email") is not None

    if request.method == "POST":
        if not show_otp_field:
            # Шаг 1: Ввод email и пароля
            email = request.POST.get("email")
            password = request.POST.get("password")
            user = authenticate(request, username=email, password=password)

            if user:
                # Генерируем и отправляем OTP
                otp_code = generate_otp()
                request.session["login_email"] = email
                request.session["login_otp"] = otp_code
                request.session["login_otp_time"] = now().isoformat()
                send_otp_email(email, otp_code)

                messages.info(request, "A verification code has been sent to your email.")
                return render(request, "login.html", {"show_otp_field": True})
            else:
                messages.error(request, "Invalid email or password.")
        else:
            # Шаг 2: Ввод OTP
            otp_input = request.POST.get("otp")
            otp_stored = request.session.get("login_otp")
            otp_time = request.session.get("login_otp_time")

            if otp_stored and otp_time:
                # Проверка срока действия OTP
                otp_time = request.session.get("login_otp_time")
                if otp_time:
                    otp_created_at = datetime.fromisoformat(otp_time)
                    if now() - otp_created_at > timedelta(minutes=10):  # Корректное сравнение
                        messages.error(request, "The verification code has expired. Please log in again.")
                        return redirect("login")

                if otp_input == otp_stored:
                    email = request.session.get("login_email")
                    user = CustomUser.objects.get(email=email)
                    user.backend = 'django.contrib.auth.backends.ModelBackend'

                    # Логиним пользователя
                    login(request, user)

                    # Логируем вход
                    AuditLog.objects.create(user=user, action="login")

                    # Очищаем данные сессии
                    for key in ["login_email", "login_otp", "login_otp_time"]:
                        request.session.pop(key, None)

                    messages.success(request, "Login successful.")
                    return redirect("dashboard")
                else:
                    messages.error(request, "Invalid verification code.")

    return render(request, "login.html", {"show_otp_field": show_otp_field})

@login_required
def logout_view(request):
    AuditLog.objects.create(user=request.user, action="logout")
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("login")

@login_required
def dashboard(request):
    """Отображает список документов, загруженных текущим пользователем."""
    documents = Document.objects.filter(owner=request.user)
    return render(request, "dashboard.html", {"documents": documents})

@login_required
def upload_document(request):
    """Загружает файл, шифрует его и сохраняет в MinIO, добавляя запись в базу данных."""
    if request.method == "POST":
        if "file" not in request.FILES:
            messages.error(request, "No file part.")
            return redirect("dashboard")

        file = request.FILES["file"]
        if file.name == "":
            messages.error(request, "No selected file.")
            return redirect("dashboard")

        # Генерируем уникальное имя файла
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_filename = f"{timestamp}_{file.name}"

        # Читаем содержимое файла
        file_content = file.read()
        # Шифруем данные с помощью AES-256
        # encrypted_content = encrypt_data(file_content, settings.ENCRYPTION_KEY)

        # Загружаем зашифрованный файл в MinIO
        upload_file_to_minio(saved_filename, file_content, file.content_type)

        # Сохраняем запись в БД
        document = Document.objects.create(
            filename=saved_filename,
            original_filename=file.name,
            content_type=file.content_type,
            owner=request.user,
            is_encrypted=True
        )

        # Логируем действие
        AuditLog.objects.create(
            user=request.user,
            action="upload",
            details=f"Uploaded document: {file.name}"
        )

        messages.success(request, "File uploaded and encrypted successfully!")
        return redirect("dashboard")

    return render(request, "dashboard.html")


@login_required
def download_document(request, doc_id):
    """Позволяет пользователю скачать свой документ из MinIO."""
    try:
        document = Document.objects.get(id=doc_id, owner=request.user)
    except Document.DoesNotExist:
        messages.error(request, "Access denied.")
        return redirect("dashboard")

    try:
        response = download_file_from_minio(document.filename)
    except Exception as e:
        messages.error(request, "File not found.")
        return redirect("dashboard")

    # Логируем скачивание
    AuditLog.objects.create(
        user=request.user,
        action="download",
        details=f"Downloaded document: {document.original_filename}"
    )

    return FileResponse(response, as_attachment=True, filename=document.original_filename)

@login_required
def delete_document(request, doc_id):
    document = get_object_or_404(Document, id=doc_id, owner=request.user)
    document.delete()
    delete_file_from_minio(document.filename)
    messages.success(request, "Document deleted successfully.")
    return redirect('dashboard')

@login_required
def view_document(request, doc_id):
    messages.success(request, "Document view_document")
    return redirect('dashboard')

@login_required
def send_document(request, doc_id):
    messages.success(request, "Document send_document")
    return redirect('dashboard')

