from django.contrib.auth import get_user_model

User = get_user_model()


def impersonation_status(request):
    """
    Context processor to add impersonation status to all templates.
    """
    is_impersonating = False
    original_user = None
    impersonated_user = None

    if request.user.is_authenticated:
        original_user_id = request.session.get("impersonate_user_id")
        if original_user_id:
            is_impersonating = True
            try:
                original_user = User.objects.get(id=original_user_id)
                impersonated_user = request.user
            except User.DoesNotExist:
                pass

    return {
        "is_impersonating": is_impersonating,
        "original_user": original_user,
        "impersonated_user": impersonated_user,
    }
