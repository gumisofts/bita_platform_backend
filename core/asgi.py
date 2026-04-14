import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

from django.core.asgi import get_asgi_application

asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.urls import path

from accounts.urls import auth_router

app = ProtocolTypeRouter(
    {
        "http": asgi_app,
        "websocket": AllowedHostsOriginValidator(
            URLRouter(
                [
                    path("test/", auth_router),
                    path(
                        "dev",
                        AuthMiddlewareStack(
                            URLRouter(
                                [
                                    path("auth/", auth_router),
                                ]
                            )
                        ),
                    ),
                ]
            )
        ),
    }
)
