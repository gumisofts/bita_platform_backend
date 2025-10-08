from django.db.models.signals import post_save
from django.dispatch import Signal, receiver
from guardian.shortcuts import assign_perm

user_verified = Signal()


@receiver(user_verified)
def on_user_verified(sender, user, mode, **kwargs):
    if (not user.is_phone_verified and mode == "email") or (
        not user.is_email_verified and mode == "phone_number"
    ):
        assign_perm("business.add_business", user)
