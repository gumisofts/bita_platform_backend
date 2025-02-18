from drf_spectacular.extensions import OpenApiAuthenticationExtension
from accounts.api_key_auth import APIKeyAuthentication


class APIKeyAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "accounts.api_key_auth.APIKeyAuthentication"  # full import path to your auth class
    name = "ApiKey"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
        }
