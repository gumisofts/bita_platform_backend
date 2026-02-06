from django.contrib import admin, messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


@user_passes_test(lambda u: u.is_staff)
@never_cache
def impersonate_user(request, user_id):
    """
    Impersonate a specific user by ID.
    """
    # Check if already impersonating
    if request.session.get("impersonate_user_id"):
        messages.error(
            request,
            "You are already impersonating a user. Please stop impersonation first.",
        )
        return redirect("admin:accounts_user_changelist")

    # Get the user to impersonate
    user = get_object_or_404(User, id=user_id)

    # Prevent impersonating yourself
    if user.id == request.user.id:
        messages.error(request, "You cannot impersonate yourself.")
        return redirect("admin:accounts_user_changelist")

    # Store the original admin user ID in session
    request.session["impersonate_user_id"] = str(request.user.id)
    request.session["impersonate_original_user_id"] = str(user.id)
    request.session.save()

    # Log in as the selected user
    from django.contrib.auth.backends import ModelBackend

    login(request, user, backend="django.contrib.auth.backends.ModelBackend")

    # Show success message
    user_display = user.get_full_name() or user.email or user.phone_number or "User"
    user_identifier = user.email or user.phone_number or "N/A"
    messages.success(
        request,
        f"Now impersonating user: <strong>{user_display}</strong> ({user_identifier}). "
        f'<a href="{reverse("stop_impersonation")}">Stop impersonating</a>',
        extra_tags="safe",
    )

    # Redirect to admin index
    return redirect("admin:index")


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
    from django.contrib.auth.backends import ModelBackend

    login(request, original_user, backend="django.contrib.auth.backends.ModelBackend")

    # Show success message
    user_display = (
        original_user.get_full_name()
        or original_user.email
        or original_user.phone_number
        or "Admin"
    )
    messages.success(request, f"Stopped impersonating. Returned to {user_display}.")

    return redirect("admin:index")


@user_passes_test(lambda u: u.is_staff)
@never_cache
def get_user_jwt_token(request, user_id):
    """
    Get JWT access token for a specific user (for debugging purposes).
    """
    # Get the user
    user = get_object_or_404(User, id=user_id)

    # Generate JWT tokens
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)

    # Return JSON response with tokens
    return JsonResponse(
        {
            "user_id": str(user.id),
            "email": user.email or None,
            "phone_number": user.phone_number or None,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "message": f"JWT tokens generated for user: {user.get_full_name() or user.email or user.phone_number or 'N/A'}",
        }
    )
