from django.core.files import File
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    OpenApiTypes,
    extend_schema,
)

from .serializers import FileUploadSerializer

file_upload_schema = extend_schema(
    summary="Upload a file",
    description="Upload a file to the server. Images are optimized automatically.",
    request={"multipart/form-data": FileUploadSerializer},
    responses={
        201: OpenApiResponse(
            description="File uploaded successfully",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    name="Success Response",
                    value={
                        "message": "File uploaded successfully",
                        "stored_as": "abc123xyz",
                    },
                ),
            ],
        ),
        400: OpenApiResponse(
            description="Invalid request",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    name="Error Response",
                    value={
                        "message": "Invalid request",
                        "errors": {"file": ["This field is required."]},
                    },
                ),
            ],
        ),
    },
)


file_download_schema = extend_schema(
    summary="Download a file",
    description="Download a file by its unique `stored_as` identifier.",
    parameters=[
        OpenApiParameter(
            name="stored_as",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.PATH,
            description="Unique identifier for the file",
        ),
    ],
    responses={
        200: OpenApiResponse(
            description="File is available for viewing or download",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    name="Success Response (Media File)",
                    value={
                        "message": "File is available for viewing",
                        "file_url": "http://example.com/media/files/image.jpg",
                        "alt_text": "An example image",
                    },
                ),
                OpenApiExample(
                    name="Success Response (Non-Media File)",
                    description="Returns a file for download",
                    value=None,  # No JSON response for file downloads
                ),
            ],
        ),
        404: OpenApiResponse(
            description="File not found",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    name="Error Response",
                    value={
                        "message": "File not found",
                        "error": "The requested file does not exist on the server.",
                    },
                ),
            ],
        ),
    },
)
