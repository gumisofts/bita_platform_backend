from django.contrib import admin, messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache

User = get_user_model()


@user_passes_test(lambda u: u.is_staff)
@never_cache
def stop_impersonation(request):
    """
    Stop impersonating a user and return to the original admin user.
    """
    original_user_id = request.session.get("impersonate_user_id")

    if not original_user_id:
        # Not impersonating, redirect to admin
        messages.info(request, "You are not currently impersonating any user.")
        return redirect("admin:index")

    try:
        original_user = User.objects.get(id=original_user_id)
    except User.DoesNotExist:
        # Original user doesn't exist, clear session and redirect
        request.session.pop("impersonate_user_id", None)
        request.session.pop("impersonate_original_user_id", None)
        messages.warning(
            request, "Original admin user not found. Impersonation session cleared."
        )
        return redirect("admin:index")

    # Clear impersonation session data
    request.session.pop("impersonate_user_id", None)
    request.session.pop("impersonate_original_user_id", None)
    request.session.save()

    # Log back in as the original admin user
    login(request, original_user)

    # Show success message
    user_display = (
        original_user.get_full_name()
        or original_user.email
        or original_user.phone_number
        or "Admin"
    )
    messages.success(request, f"Stopped impersonating. Returned to {user_display}.")

    return redirect("admin:index")
