# Signal for creating a transaction when an order is completed
from django.db.models.signals import post_save, Signal
from django.dispatch import receiver

from orders.models import Order

order_completed = Signal()
