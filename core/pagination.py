from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    # Upper bound for the client-supplied ``page_size``. Any larger value is
    # silently clamped to this (so ``page_size=300`` returns 300, but a runaway
    # ``page_size=100000`` is capped). Raised from 100 to support bulk reads /
    # sync clients that pull large batches of records in one request.
    max_page_size = 1000
