from business.models import Branch, Business


class BusinessContextMiddleWare:
    """
    Middleware to set the business context for each request.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Set the business context based on the request
        business_id = request.GET.get("business")
        branch_id = request.GET.get("branch")
        if not business_id:
            business_id = request.GET.get("business_id")
        if not branch_id:
            branch_id = request.GET.get("branch_id")

        if business_id:
            try:
                request.business = Business.objects.get(id=business_id)
            except:
                request.business = None

        else:
            request.business = None

        if branch_id:
            try:
                request.branch = Branch.objects.get(
                    id=branch_id, business=request.business
                )
            except:
                request.branch = None
        else:
            request.branch = None

        response = self.get_response(request)
        return response
