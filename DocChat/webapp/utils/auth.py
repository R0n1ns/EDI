from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

UserModel = get_user_model()

class EmailBackend(ModelBackend):
    def authenticate(self, request, email=None, username=None, password=None, **kwargs):
        # Если email не передан, используем username, который в данном случае является email из формы
        if email is None:
            email = username
        try:
            user = UserModel.objects.get(email=email)

        except UserModel.DoesNotExist:
            return None
        else:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        return None


# from django.contrib.auth import get_user_model
#
# User = get_user_model()
# user = User.objects.get(username="test1")  # Укажите существующего пользователя
# user.set_password("test1@company.com")
# user.save()
#
# User = get_user_model()
# user = User.objects.get(username="test3")  # Укажите существующего пользователя
# user.set_password("test3@company.com")
# user.save()
#
# User = get_user_model()
# user = User.objects.get(username="test4")  # Укажите существующего пользователя
# user.set_password("test4@company.com")
# user.save()