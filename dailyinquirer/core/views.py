from django.shortcuts import render, redirect
from authentication.admin import UserCreationForm
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpResponse
from django.template.loader import render_to_string
from authentication.models import User
from django.contrib.auth.decorators import login_required
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from authentication.tokens import account_activation_token
from django.core.mail import EmailMessage
from django.contrib.auth import login, logout
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from core.models import Entry, Prompt
from core.forms import ResendConfirmationForm
from core.utils import mail_newsletter

from datetime import datetime

import json
import pytz


def index(request):
    if request.user.is_authenticated():
        if request.user.confirmed_email:
            entries = Entry.objects.filter(author=request.user).\
                order_by("-pub_date")
            return render(request, 'core/index_logged_in.html',
                          {'entries': entries})
        else:
            logout(request)
            return redirect('unconfirmed_email')
    else:
        return render(request, 'core/index.html')


@login_required
def settings(request):
    return render(request, 'core/settings.html')


def register(request):
    if request.user.is_authenticated():
        return redirect('index')
    else:
        if request.method == 'POST':
            form = UserCreationForm(request.POST)
            if form.is_valid():
                user = form.save()
                send_activation_email(request, user)
                template = 'registration/activation_email_sent.html'
                context = {'email': user.email}
                return render(request, template, context)
            else:
                template = 'registration/register.html'
                context = {'form': form, 'timezones': pytz.common_timezones}
                return render(request, template, context)
        else:
            template = 'registration/register.html'
            context = {'timezones': pytz.common_timezones}
            return render(request, template, context)


def unconfirmed_email(request):
    return render(request, 'registration/user_unconfirmed.html')


def resend_confirmation(request):
    if request.method == 'POST':
        form = ResendConfirmationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                user = None

            if user is not None:
                send_activation_email(request, user)

            template = 'registration/activation_email_sent.html'
            context = {'email': email}
            return render(request, template, context)
        else:
            template = 'registration/resend_confirmation.html'
            context = {'form': form}
            return render(request, template, context)
    else:
        return render(request, 'registration/resend_confirmation.html')


def send_activation_email(request, user):
    current_site = get_current_site(request)
    message = render_to_string('registration/confirm_email.html', {
        'user': user,
        'domain': current_site.domain,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': account_activation_token.make_token(user),
    })
    mail_subject = 'Activate your Daily Inquirer Account'
    to_email = user.email
    email = EmailMessage(mail_subject,
                         message,
                         "Beep Boop <beep-boop@dailyinquirer.me>",
                         [to_email])
    email.send()


def activate(request, uidb64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        user.confirmed_email = True
        user.save()
        login(request, user)
        try:
            mail_newsletter(user)
        except:
            pass

        return redirect('index')
    else:
        return HttpResponse('Activation link is invalid!')


@csrf_exempt
def on_incoming_message(request):
    if request.method == 'POST':

        try:
            data = json.loads(request.body)
        except:
            data = request.POST

        try:
            sender = data['sender']
            stripped_text = data['stripped-text']
        except:
            sender = None
            stripped_text = None

        if stripped_text is not None:

            try:
                user = User.objects.get(email=sender)
            except User.DoesNotExist:
                user = None

            if user is not None:
                user_tz = pytz.timezone(user.timezone)
                local_time = datetime.now(user_tz)

                todays_day = local_time.day
                todays_month = local_time.month
                todays_year = local_time.year

            try:
                todays_prompt = Prompt.objects.get(mail_day__day=todays_day,
                                                   mail_day__month=todays_month,
                                                   mail_day__year=todays_year)
            except Prompt.DoesNotExist:
                todays_prompt = None

            try:
                entry_exists = Entry.objects.get(pub_date__day=todays_day,
                                                 pub_date__month=todays_month,
                                                 pub_date__year=todays_year,
                                                 author=user)
            except Entry.DoesNotExist:
                entry_exists = None

            if entry_exists is None:
                entry = Entry(content=stripped_text,
                              author=user,
                              prompt=todays_prompt,
                              pub_date=timezone.now())
                entry.save()

    return HttpResponse('OK')


def privacy(request):
    return render(request, 'core/privacy.html')


def terms(request):
    return render(request, 'core/terms.html')
