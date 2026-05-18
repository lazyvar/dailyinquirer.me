from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse


class OnboardingRequiredMiddleware:
    """Redirect confirmed users who have not finished onboarding.

    Any authenticated user with ``confirmed_email`` set but ``onboarded``
    still False is sent to the onboarding page, except on a small set of
    exempt paths (the onboarding page itself, logout, admin, the inbound
    webhook, and static files).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if (user.is_authenticated and user.confirmed_email
                and not user.onboarded
                and not self._is_exempt(request.path)):
            return redirect('onboarding')
        return self.get_response(request)

    def _is_exempt(self, path):
        exempt = [
            reverse('onboarding'),
            '/logout/',
            '/admin/',
            '/messages/',
            settings.STATIC_URL,
        ]
        return any(prefix and path.startswith(prefix) for prefix in exempt)
