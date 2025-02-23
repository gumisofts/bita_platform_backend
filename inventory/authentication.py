import requests
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions

token_verify_url = settings.AUTH_SERVICE_URL + "token/verify/"


class RemoteJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None

        try:
            scheme, token = auth_header.split()
        except ValueError:
            raise exceptions.AuthenticationFailed("Invalid authorization header.")

        if scheme.lower() != "bearer":
            return None

        headers = {"HTTP_X_API_KEY": settings.AUTH_SERVICE_API_KEY}
        response = requests.post(
            token_verify_url, data={"token": token}, headers=headers
        )
        if response.status_code != 200:
            raise exceptions.AuthenticationFailed("Invalid or expired token.")

        data = response.json()
        user_data = data.get("user")
        if not user_data:
            raise exceptions.AuthenticationFailed("Invalid token data.")

        # Create a simple user-like object with details from the auth service
        user = type("RemoteUser", (), {})()
        user.id = user_data.get("id")
        user.email = user_data.get("email")
        user.first_name = user_data.get("first_name")
        user.last_name = user_data.get("last_name")
        user.phone = user_data.get("phone")
        return (user, token)
