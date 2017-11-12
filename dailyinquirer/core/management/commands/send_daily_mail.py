from django.core.management.base import BaseCommand
from authentication.models import User

from core.utils import mail_newsletter


class Command(BaseCommand):

    def handle(self, *args, **options):
        for user in User.objects.filter(confirmed_email=True):
            local_time = user.local_time()
            if local_time is not None and local_time.hour == 5:
                mail_newsletter(user)
