class PrincipalMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not hasattr(request, "principal"):
            request.principal = None
        response = self.get_response(request)
        return response
