from django.shortcuts import render, redirect
from authentication.admin import UserCreationForm
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpResponse
from django.template.loader import render_to_string
from authentication.models import User
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from authentication.tokens import account_activation_token
from django.core.mail import EmailMessage
from django.contrib.auth import login
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json

from core.models import Entry, Prompt

def index(request):
    if request.user.is_authenticated():
        entries = Entry.objects.filter(author=request.user)
        return render(request, 'core/index_logged_in.html', {'entries': entries})
    else:
        if request.method == 'POST':
            form = UserCreationForm(request.POST)
            if form.is_valid():
                user = form.save()
                send_activation_email(request, user)
                return render(request, 'registration/activation_email_sent.html')
            else:
                return render(request, 'core/index.html', {'form': form})
        else:
            return render(request, 'core/index.html')


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
    email = EmailMessage(mail_subject, message, to=[to_email])
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
        message = "Email confrimation success"
        messages.success(request, message)
        return redirect('index')
    else:
        return HttpResponse('Activation link is invalid!')


@csrf_exempt
def on_incoming_message(request):
     if request.method == 'POST':

        try:
            data = json.loads(request.body)
        except ValueError:
            data = request.POST

        try :
            sender = data['sender']
            stripped_text = data['stripped-text']
        except ValueError:
            sender = None
            stripped_text = None

        if stripped_text != None:

            todays_date = timezone.now()
            todays_day = todays_date.day
            todays_month = todays_date.month
            todays_year = todays_date.year

            try:
                todays_prompt = Prompt.objects.get(mail_day__day=todays_day, 
                mail_day__month=todays_month, mail_day__year=todays_year)
            except Prompt.DoesNotExist:
                todays_prompt = None

            try:
                entry_exists = Entry.objects.get(pub_date__day=todays_day, 
                pub_date__month=todays_month, pub_date__year=todays_year)
            except Entry.DoesNotExist:
                entry_exists = None

            try:
                user = User.objects.get(email=sender)
            except User.DoesNotExist:
                user = None

            if user != None and todays_prompt != None and entry_exists == None:
                entry = Entry(content=stripped_text, author=user,
                prompt=todays_prompt, pub_date=todays_date)
                entry.save()

     return HttpResponse('OK')
