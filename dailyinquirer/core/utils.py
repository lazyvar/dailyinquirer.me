from core.models import Prompt
from django.core.mail import EmailMessage, EmailMultiAlternatives

from django.template.loader import render_to_string

import pytz
from datetime import datetime


def mail_newsletter(user):
    todays_prompt = prompt_for_datetime(user.local_time())

    if todays_prompt is not None:
        plain_text = todays_prompt.question
        html_content = render_to_string('core/daily_email.html', {
            'prompt': todays_prompt,
        })
        mail_subject = todays_prompt.question
        to_email = user.email
        from_email = "The Daily Inquirer <the@dailyinquirer.me>"
        email = EmailMultiAlternatives(mail_subject, plain_text, from_email, [to_email])
        email.attach_alternative(html_content, "text/html")
        email.send()


def prompt_for_datetime(local_time):
    todays_day = local_time.day
    todays_month = local_time.month
    todays_year = local_time.year

    try:
        todays_prompt = Prompt.objects.get(mail_day__day=todays_day,
            mail_day__month=todays_month, mail_day__year=todays_year)
    except Prompt.DoesNotExist:
        todays_prompt = None

    return todays_prompt
