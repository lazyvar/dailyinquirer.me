from django.core.management.base import BaseCommand

from authentication.models import User
from core.utils import send_prompt_to_user


class Command(BaseCommand):
    help = ("Send today's prompt to every confirmed, subscribed user "
            "whose local time is at or past 8am and who has not yet "
            "received it. Intended to run hourly.")

    def handle(self, *args, **options):
        for user in User.objects.filter(confirmed_email=True,
                                        is_subscribed=True):
            local_time = user.local_time()
            if local_time is None or local_time.hour < user.mail_hour:
                continue
            try:
                send_prompt_to_user(user)
            except Exception as exc:
                self.stderr.write(
                    f"Failed to send prompt to {user.email}: {exc}")
