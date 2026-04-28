import uuid
from datetime import datetime


def is_valid_uuid(value):
    if value is None:
        return False
    try:
        # Accept any well-formed UUID string in any case (with or without dashes,
        # urn:uuid:, braces, etc.); uuid.UUID() handles those formats. The
        # previous implementation incorrectly rejected uppercase UUIDs and
        # raised AttributeError for non-string inputs.
        uuid.UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def is_valid_date(date_str, date_format="%Y-%m-%d"):
    try:
        datetime.strptime(date_str, date_format)
        return True
    except ValueError:
        return False
