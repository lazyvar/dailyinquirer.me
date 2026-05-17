from django.http import HttpResponsePermanentRedirect


class RedirectWwwToNakedMiddleware:
    """Permanently redirect ``www.`` requests to the naked (apex) domain.

    ``dailyinquirer.me`` is the canonical host; this 301-redirects any
    ``www.`` hostname to its apex equivalent, preserving scheme, path, and
    query string.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host()
        if host.startswith("www."):
            naked_host = host[len("www."):]
            return HttpResponsePermanentRedirect(
                f"{request.scheme}://{naked_host}{request.get_full_path()}"
            )
        return self.get_response(request)
