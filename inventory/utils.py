import requests
from django.core.exceptions import ValidationError


def upload_to_file_service(file):
    file_service_url = "http://file-service/api/files/upload"
    files = {"file": file}  # The file is passed directly
    response = requests.post(file_service_url, files=files)

    if response.status_code != 200:
        raise ValidationError("Failed to upload file to the file service.")

    file_id = response.json().get("file_id")
    if not file_id:
        raise ValidationError("File ID not found in the response.")

    return file_id


def validate_image_file(value):
    valid_extensions = [
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".webp",
        ".ico",
        ".ppm",
    ]
    ext = value.name.lower().rsplit(".", 1)[-1]  # Get the file extension
    if f".{ext}" not in valid_extensions:
        raise ValidationError(
            "Unsupported file extension. Only image files are allowed."
        )
