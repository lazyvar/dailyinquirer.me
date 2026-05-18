from core.models import Prompt, PromptSend
from authentication.models import User
from django.conf import settings
from django.core import signing
from django.urls import reverse
from django.utils import timezone

from core.email import send_templated_email


def mail_newsletter(user):
    local_time = user.local_time()
    if local_time is None:
        return None

    todays_prompt = prompt_for_datetime(local_time)
    if todays_prompt is None:
        return None

    token = make_unsubscribe_token(user)
    unsubscribe_url = (f"{settings.SITE_URL}{reverse('unsubscribe')}"
                       f"?token={token}")
    one_click_url = (f"{settings.SITE_URL}"
                     f"{reverse('unsubscribe_one_click')}?token={token}")
    manage_url = f"{settings.SITE_URL}{reverse('settings')}"

    send_templated_email(
        subject=todays_prompt.question,
        to=user.email,
        template='daily_prompt',
        from_email='The Daily Inquirer <the@dailyinquirer.me>',
        context={
            'prompt': todays_prompt,
            'unsubscribe_url': unsubscribe_url,
            'manage_url': manage_url,
        },
        headers={
            'List-Unsubscribe': f'<{one_click_url}>',
            'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click',
        },
    )
    return todays_prompt


def prompt_for_datetime(local_time):
    todays_day = local_time.day
    todays_month = local_time.month
    todays_year = local_time.year

    try:
        todays_prompt = Prompt.objects.get(mail_day__day=todays_day,
                                           mail_day__month=todays_month,
                                           mail_day__year=todays_year)
    except Prompt.DoesNotExist:
        todays_prompt = None

    return todays_prompt


def send_prompt_to_user(user, force=False):
    """Send today's prompt to one user, recording the delivery.

    Skips the user if they have already received today's prompt, unless
    ``force`` is True. Returns the Prompt that was sent, or None when there
    is nothing to send (no valid timezone, no prompt for today, or already
    sent and not forced).
    """
    local_time = user.local_time()
    if local_time is None:
        return None

    todays_prompt = prompt_for_datetime(local_time)
    if todays_prompt is None:
        return None

    already_sent = PromptSend.objects.filter(
        user=user, prompt=todays_prompt).exists()
    if already_sent and not force:
        return None

    sent_prompt = mail_newsletter(user)
    if sent_prompt is None:
        return None

    PromptSend.objects.update_or_create(
        user=user, prompt=sent_prompt,
        defaults={'sent_at': timezone.now()})
    return sent_prompt


UNSUBSCRIBE_SALT = 'daily-prompt-unsubscribe'


def make_unsubscribe_token(user):
    """Return a signed, non-expiring token identifying the user."""
    return signing.dumps(user.pk, salt=UNSUBSCRIBE_SALT)


def read_unsubscribe_token(token):
    """Return the User for a valid token, or None if it is invalid."""
    try:
        pk = signing.loads(token, salt=UNSUBSCRIBE_SALT)
    except signing.BadSignature:
        return None
    try:
        return User.objects.get(pk=pk)
    except User.DoesNotExist:
        return None
