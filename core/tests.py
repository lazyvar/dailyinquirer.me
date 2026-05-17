from django.test import TestCase


class HomePageTests(TestCase):
    def test_homepage_returns_200(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/index.html')
