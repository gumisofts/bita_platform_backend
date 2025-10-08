# Signal for creating a transaction when an order is completed
from django.db.models.signals import Signal, post_save
from django.dispatch import receiver

from orders.models import Order

order_completed = Signal()
