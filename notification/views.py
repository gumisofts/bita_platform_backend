from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import EmailMessage
from django.conf import settings
from .spectacular_schemas import send_email_schema


@csrf_exempt
@send_email_schema
@api_view(("POST",))
def send_single_email(request):
    try:
        subject = request.data.get("subject")
        message = request.data.get("message")
        recipients = request.data.get("recipients")

        if not subject or not message or not recipients:

            return Response(
                {
                    "status": "Missing required fields",
                    "error": "subject, message, and recipients are required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Ensure recipients is a list (it can be a comma-separated string)
        if isinstance(recipients, str):
            recipients = [email.strip() for email in recipients.split(",")]

        # Build email
        html_message = render_to_string(
            "email_template.html", {"subject": subject, "message": message}
        )

        email = EmailMessage(
            subject=subject,
            body=html_message,
            from_email=settings.EMAIL_HOST_USER,
            to=recipients,
        )
        email.content_subtype = "html"

        email.send(fail_silently=False)

        return Response(
            {"status": "Email sent successfully"}, status=status.HTTP_200_OK
        )

    except Exception as e:
        return Response(
            {"status": "Failed to send email", "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# {
#     "subject": "mono sub",
#     "message": "message",
#     "recipients": "nathnaelyirga@gmail.com"
# }
