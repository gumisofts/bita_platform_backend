import logging
import secrets

from django.conf import settings
from google.auth.transport import requests
from google.oauth2 import id_token

logger = logging.getLogger(__name__)


def get_required_user_actions(user):
    actions = []

    if user.phone_number and not user.is_phone_verified:
        actions.append("verify_phone")
    if user.email and not user.is_email_verified:
        actions.append("verify_email")

    return actions


def verify_google_id_token(token):
    """Verify a Google ID token and return the decoded payload, or ``None``.

    The audience is validated against ``settings.GOOGLE_WEB_CLIENT_ID`` when
    configured. Without an audience check Google's library will accept tokens
    issued for *any* OAuth client, which is a critical security gap for the
    /auth/google/login endpoint.
    """
    audience = getattr(settings, "GOOGLE_WEB_CLIENT_ID", None) or None
    try:
        if audience:
            idinfo = id_token.verify_oauth2_token(token, requests.Request(), audience)
        else:
            logger.warning(
                "GOOGLE_WEB_CLIENT_ID not configured; verifying Google ID token "
                "without audience validation."
            )
            idinfo = id_token.verify_oauth2_token(token, requests.Request())

        # Reject tokens not issued by Google.
        if idinfo.get("iss") not in (
            "accounts.google.com",
            "https://accounts.google.com",
        ):
            logger.warning("Rejected Google ID token with invalid issuer")
            return None

        return idinfo
    except ValueError as exc:
        logger.info("Google ID token verification failed: %s", exc)
        return None


def generate_secure_six_digits():
    return str(secrets.randbelow(900000) + 100000)
