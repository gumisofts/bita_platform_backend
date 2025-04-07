from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()


class EmailOrPhoneBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None):
        user = None
        if "@" in username:
            try:
                user = User.objects.get(email=username)
            except User.DoesNotExist:
                return None
        else:
            try:
                user = User.objects.get(phone_number=username)
            except User.DoesNotExist:
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None


class EmailBackend(ModelBackend):

    def user_can_authenticate(self, user):
        return super().user_can_authenticate(user) and user.is_email_verified

    def authenticate(self, request, email, password, **kwargs):
        user = User.objects.filter(email=email).first()

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user


class PhoneBackend(ModelBackend):
    def user_can_authenticate(self, user):
        return super().user_can_authenticate(user) and user.is_phone_verified

    def authenticate(self, request, phone_number, password, **kwargs):
        user = User.objects.filter(
            phone_number=User.normalize_phone(phone_number)
        ).first()

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
