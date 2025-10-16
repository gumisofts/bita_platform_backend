import uuid
from datetime import datetime


def is_valid_uuid(value):
    try:
        val = uuid.UUID(str(value))
        return str(val) == value.lower()
    except ValueError:
        return False


def is_valid_date(date_str, date_format="%Y-%m-%d"):
    try:
        datetime.strptime(date_str, date_format)
        return True
    except ValueError:
        return False
