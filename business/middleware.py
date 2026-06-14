import logging

from business.models import Branch, Business
from core.utils import is_valid_uuid

logger = logging.getLogger(__name__)


class BusinessContextMiddleWare:
    """
    Middleware to set the business / branch context for each request.

    Resolution order for both ids:
      1. ``?business`` / ``?branch`` query parameter
      2. ``?business_id`` / ``?branch_id`` query parameter alias
      3. ``X-Business-Id`` / ``X-Branch-Id`` request headers (useful for POSTs
         that don't carry the id in the URL or body)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def _first(*values):
        for value in values:
            if value:
                return value
        return None

    def __call__(self, request):
        business_id = self._first(
            request.GET.get("business"),
            request.GET.get("business_id"),
            request.headers.get("X-Business-Id"),
        )
        branch_id = self._first(
            request.GET.get("branch"),
            request.GET.get("branch_id"),
            request.headers.get("X-Branch-Id"),
        )

        request.business = None
        if business_id and is_valid_uuid(business_id):
            try:
                request.business = Business.objects.get(id=business_id)
            except Business.DoesNotExist:
                request.business = None
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("BusinessContextMiddleWare: %s", exc)
                request.business = None

        request.branch = None
        if branch_id and is_valid_uuid(branch_id):
            try:
                if request.business is not None:
                    request.branch = Branch.objects.get(
                        id=branch_id, business=request.business
                    )
                else:
                    request.branch = Branch.objects.get(id=branch_id)
                    # If the branch was found but no business was provided,
                    # backfill so downstream views can rely on `request.business`.
                    request.business = request.branch.business
            except Branch.DoesNotExist:
                request.branch = None
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("BusinessContextMiddleWare: %s", exc)
                request.branch = None

        return self.get_response(request)
