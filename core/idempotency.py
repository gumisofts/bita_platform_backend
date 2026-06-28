import functools
import logging

from django.core.cache import cache
from django_redis import get_redis_connection
from rest_framework.response import Response

logger = logging.getLogger(__name__)

_TTL = 60 * 60 * 24  # 24 hours


def hash_request(request):
    """
    Returns a hash of the request body and query params.  This is used to
    ensure that the same idempotency key is not used for different requests.
    """
    import hashlib

    body = request.body or b""
    query_params = request.query_params.urlencode().encode("utf-8")
    return hashlib.sha256(body + query_params).hexdigest()


def get_idempotency_cache_key(request):
    """
    Returns the idempotency cache key for the request.
    """
    user_id = request.user.pk if request.user.is_authenticated else "anon"

    idempotency_key = request.headers.get("Idempotency-Key")

    request_hash = hash_request(request)

    logger.debug(
        "get_idempotency_key: user_id=%s, idempotency_key=%s, request_hash=%s",
        user_id,
        idempotency_key,
        request_hash,
    )

    return f"idempotency:{user_id}:{idempotency_key}:{request_hash}"


def idempotent(view_func=None, *, ttl=_TTL):
    """
    Makes a DRF ViewSet action idempotent when the client sends an
    ``Idempotency-Key`` header.

    Cache key: ``idempotency:<user_id>:<idempotency_key>:<request_hash>``

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

            logger.debug("idempotent: received request with key %s", idempotency_key)

            if not idempotency_key:
                return func(self, request, *args, **kwargs)

            idempotency_key = get_idempotency_cache_key(request)

            cache_key = idempotency_key

            cached = cache.get(cache_key)
            if cached is not None:
                logger.debug("idempotent: cache hit for key %s", cache_key)
                return Response(cached["data"], status=cached["status"])

            redis = get_redis_connection("default")

            cache_lock = redis.lock(
                cache_key, timeout=2
            )  # Lock to prevent duplicate processing

            if not cache_lock.acquire(blocking=False):
                return Response(
                    {"detail": "Request is already being processed."},
                    status=409,
                )

            response = func(self, request, *args, **kwargs)

            if hasattr(response, "data") and 200 <= response.status_code < 300:
                cache.set(
                    cache_key,
                    {"data": response.data, "status": response.status_code},
                    ttl,
                )

            cache_lock.release()

            return response

        return wrapper

    # Support both @idempotent and @idempotent(ttl=...)
    if view_func is not None:
        return decorator(view_func)
    return decorator
