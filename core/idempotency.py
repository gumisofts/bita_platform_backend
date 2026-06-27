import functools
import logging

from django.core.cache import cache
from rest_framework.response import Response

logger = logging.getLogger(__name__)

_TTL = 60 * 60 * 24  # 24 hours


def idempotent(view_func=None, *, ttl=_TTL):
    """
    Makes a DRF ViewSet action idempotent when the client sends an
    ``Idempotency-Key`` header.

    Cache key: ``idempotency:<user_id>:<idempotency_key>``

    On the first request the action runs normally; the response (status + data)
    is stored in the cache.  Any repeat request with the same key returns the
    cached response immediately without re-executing the action.

    Only 2xx responses are cached — errors are never stored so the client can
    safely retry after a failure.

    Usage::

        @action(detail=True, methods=["post"])
        @idempotent
        def checkout(self, request, *args, **kwargs):
            ...

        # or with a custom TTL (seconds):
        @idempotent(ttl=3600)
        def some_action(self, request, *args, **kwargs):
            ...
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, request, *args, **kwargs):
            idempotency_key = request.headers.get("Idempotency-Key")
            if not idempotency_key:
                return func(self, request, *args, **kwargs)

            user_id = request.user.pk if request.user.is_authenticated else "anon"
            cache_key = f"idempotency:{user_id}:{idempotency_key}"

            cached = cache.get(cache_key)
            if cached is not None:
                logger.debug("idempotent: cache hit for key %s", cache_key)
                return Response(cached["data"], status=cached["status"])

            response = func(self, request, *args, **kwargs)

            if hasattr(response, "data") and 200 <= response.status_code < 300:
                cache.set(
                    cache_key,
                    {"data": response.data, "status": response.status_code},
                    ttl,
                )

            return response

        return wrapper

    # Support both @idempotent and @idempotent(ttl=...)
    if view_func is not None:
        return decorator(view_func)
    return decorator
