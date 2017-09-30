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


def index(request):
    if request.user.is_authenticated():
        return render(request, 'core/index_logged_in.html')
    else:
        if request.method == 'POST':
            form = UserCreationForm(request.POST)
            if form.is_valid():
                user = form.save()
                send_activation_email(request, user)
                return HttpResponse('Please confirm your email address to complete the registration')
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
