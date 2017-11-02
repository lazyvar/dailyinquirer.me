from django.core.management.base import BaseCommand, CommandError
from authentication.models import User
from core.models import Prompt, Entry
from django.utils import timezone
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives

class Command(BaseCommand):

    def handle(self, *args, **options):
        todays_date = timezone.now()
        todays_day = todays_date.day
        todays_month = todays_date.month
        todays_year = todays_date.year

        try:
            todays_prompt = Prompt.objects.get(mail_day__day=todays_day, 
                mail_day__month=todays_month, mail_day__year=todays_year)
        except Prompt.DoesNotExist:
            todays_prompt = None

        if todays_prompt == None:
                mail_subject = "URGENT: NO PROMPT SET FOR TODAY"
                to_email = "big.mack.with.pies@gmail.com"
                email = EmailMessage(mail_subject, "YOU'RE A DUFFUS", 
                    "The Daily Inquirer <the@dailyinquirer.me>", [to_email])
                email.send()
        else:
            users = User.objects.all()
            for user in users:
                plain_text = todays_prompt.question
                html_content = render_to_string('core/daily_email.html', {
                    'prompt': todays_prompt,
                })
                mail_subject = todays_prompt.question
                to_email = user.email
                email = EmailMultiAlternatives(mail_subject, plain_text, 
                    "The Daily Inquirer <the@dailyinquirer.me>", [to_email])
                email.attach_alternative(html_content, "text/html")
                email.send()
