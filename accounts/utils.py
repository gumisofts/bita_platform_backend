import secrets

from django.conf import settings
from google.auth.transport import requests
from google.oauth2 import id_token


def get_required_user_actions(user):
    actions = []

    if user.phone_number and not user.is_phone_verified:
        actions.append("verify_phone")
    if user.email and not user.is_email_verified:
        actions.append("verify_email")

    return actions


def verify_google_id_token(token):
    try:
        # Specify the WEB_CLIENT_ID of the app that accesses the backend:
        idinfo = id_token.verify_oauth2_token(token, requests.Request())
        # Or, if multiple clients access the backend server:
        # idinfo = id_token.verify_oauth2_token(token, requests.Request())
        # if idinfo['aud'] not in [WEB_CLIENT_ID_1, WEB_CLIENT_ID_2, WEB_CLIENT_ID_3]:
        #     raise ValueError('Could not verify audience.')

        # If the request specified a Google Workspace domain
        # if idinfo['hd'] != DOMAIN_NAME:
        #     raise ValueError('Wrong domain name.')

        # ID token is valid. Get the user's Google Account ID from the decoded token.

        return idinfo
    except ValueError:
        # Invalid token
        pass


def generate_secure_six_digits():
    return str(secrets.randbelow(900000) + 100000)
