from django.test import RequestFactory, SimpleTestCase, override_settings

from dailyinquirer.middleware import RedirectWwwToNakedMiddleware


@override_settings(ALLOWED_HOSTS=['www.dailyinquirer.me', 'dailyinquirer.me'])
class RedirectWwwToNakedMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = RedirectWwwToNakedMiddleware(lambda request: 'passed-through')

    def test_www_host_redirects_to_naked_domain(self):
        request = self.factory.get('/entries/?page=2', HTTP_HOST='www.dailyinquirer.me')
        response = self.middleware(request)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], 'http://dailyinquirer.me/entries/?page=2')

    def test_naked_host_passes_through(self):
        request = self.factory.get('/', HTTP_HOST='dailyinquirer.me')
        response = self.middleware(request)
        self.assertEqual(response, 'passed-through')
