from django.conf import settings
from rest_framework import authentication, exceptions


class APIKeyAuthentication(authentication.BaseAuthentication):
    """
    Custom authentication that enforces the presence of a valid API key.
    If the API key is missing or invalid, it raises an AuthenticationFailed error.
    Otherwise, it returns None so that additional authentication (e.g. JWT) can run.
    Skips API key validation for Swagger, Redoc and schema endpoints.
    """

    def authenticate(self, request):
        # Skip API key check for Swagger, Redoc, and schema endpoints
        if (
            request.path.startswith("/swagger")
            or request.path.startswith("/redoc")
            or request.path.startswith("/schema")
        ):
            return None

        api_key = request.headers.get("X-API-Key")
        if not api_key:
            raise exceptions.AuthenticationFailed("Missing API key")

        allowed_keys = getattr(settings, "API_KEYS", {})
        if api_key not in allowed_keys:
            raise exceptions.AuthenticationFailed("Invalid API key")

        # API key is valid; let further authentication (JWT) occur.
        return None
