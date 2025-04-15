from django.db.models.signals import pre_save
from django.dispatch import receiver

from accounts.models import *


@receiver(pre_save, sender=User)
def on_user_created(sender, instance, **kwargs):

    if kwargs.get("send_verification"):
        pass
    # Send verification Token Here
