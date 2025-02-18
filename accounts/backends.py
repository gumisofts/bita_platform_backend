from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailOrPhoneBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        user = None
        if "@" in username:
            try:
                user = UserModel.objects.get(email=username)
            except UserModel.DoesNotExist:
                return None
        else:
            try:
                user = UserModel.objects.get(phone=username)
            except UserModel.DoesNotExist:
                return None

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
