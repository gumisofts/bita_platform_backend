from drf_spectacular.utils import OpenApiResponse, extend_schema

send_email_schema = extend_schema(
    summary="Send an Email to One/Multiple Recipients",
    description="This endpoint sends an email with a dynamic subject, message, and recipients. The recipients can be provided as a comma-separated list.",
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "subject": {
                    "type": "string",
                    "description": "The subject of the email.",
                    "example": "Password Reset Email",
                },
                "message": {
                    "type": "string",
                    "description": "The content/body of the email.",
                    "example": "Use the attached link to reset your password:\n <Link>",
                },
                "recipients": {
                    "type": "string",
                    "description": "A comma-separated list of email addresses.",
                    "example": "user1@example.com, user2@example.com",
                },
            },
            "required": ["subject", "message", "recipients"],
        }
    },
    responses={
        200: OpenApiResponse(
            description="Email sent successfully",
            examples={"application/json": {"status": "Email sent successfully"}},
        ),
        400: OpenApiResponse(
            description="Missing required fields (subject, message, or recipients)",
            examples={
                "application/json": {
                    "status": "Missing required fields",
                    "error": "subject, message, and recipients are required",
                }
            },
        ),
        500: OpenApiResponse(
            description="Failed to send email due to an internal server error",
            examples={
                "application/json": {
                    "status": "Failed to send email",
                    "error": "SMTP server not responding",
                }
            },
        ),
    },
)
