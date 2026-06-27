import logging

from celery import shared_task

from core.celery.queues import CeleryQueue

logger = logging.getLogger(__name__)


@shared_task(queue=CeleryQueue.Definitions.FILE_PROCESSING)
def generate_order_receipt_task(order_id):
    from django.core.files.base import ContentFile

    from orders.models import Order
    from orders.receipt import generate_order_receipt

    try:
        order = (
            Order.objects.select_related(
                "business__address",
                "branch",
                "customer",
                "employee__user",
                "payment_method__payment",
            )
            .prefetch_related("items__variant__item")
            .get(pk=order_id)
        )
    except Order.DoesNotExist:
        logger.warning("generate_order_receipt_task: order %s not found", order_id)
        return

    try:
        pdf_bytes = generate_order_receipt(order)
    except Exception:
        logger.exception(
            "generate_order_receipt_task: PDF generation failed for order %s", order_id
        )
        return

    filename = f"order_{order.id}.pdf"

    if order.receipt:
        try:
            order.receipt.delete(save=False)
        except Exception:
            pass

    order.receipt.save(filename, ContentFile(pdf_bytes), save=True)
    logger.info("generate_order_receipt_task: receipt saved for order %s", order_id)
