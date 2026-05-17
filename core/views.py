from django.shortcuts import render, redirect
from authentication.admin import UserCreationForm
from django.contrib.sites.shortcuts import get_current_site
from django.http import (HttpResponse, HttpResponseBadRequest,
                          HttpResponseForbidden, HttpResponseNotAllowed)
from django.conf import settings as django_settings
from django.template.loader import render_to_string
from authentication.models import User
from django.contrib.auth.decorators import login_required
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from authentication.tokens import account_activation_token
from django.core.mail import EmailMessage
from django.contrib.auth import login, logout
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils.dateparse import parse_date

from core.models import Entry, Prompt
from core.forms import ResendConfirmationForm, SettingsForm
from core.utils import mail_newsletter

from datetime import datetime
import hmac

import json
import pytz


ENTRIES_PER_PAGE = 25


def index(request):
    if request.user.is_authenticated:
        if request.user.confirmed_email:
            return _dashboard(request)
        else:
            logout(request)
            return redirect('unconfirmed_email')
    else:
        return render(request, 'core/index.html')


def _dashboard(request):
    entries = Entry.objects.filter(author=request.user).select_related('prompt')

    q = request.GET.get('q', '').strip()
    date_from = request.GET.get('from', '').strip()
    date_to = request.GET.get('to', '').strip()
    category = request.GET.get('category', '').strip()
    sort = request.GET.get('sort', 'newest').strip()

    if q:
        entries = entries.filter(
            Q(content__icontains=q) | Q(prompt__question__icontains=q))

    parsed_from = parse_date(date_from) if date_from else None
    if parsed_from:
        entries = entries.filter(pub_date__date__gte=parsed_from)

    parsed_to = parse_date(date_to) if date_to else None
    if parsed_to:
        entries = entries.filter(pub_date__date__lte=parsed_to)

    if category:
        entries = entries.filter(prompt__category=category)

    if sort == 'oldest':
        entries = entries.order_by('pub_date')
    else:
        sort = 'newest'
        entries = entries.order_by('-pub_date')

    paginator = Paginator(entries, ENTRIES_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get('page'))

    categories = Entry.objects.filter(author=request.user) \
        .exclude(prompt__category__isnull=True) \
        .exclude(prompt__category='') \
        .values_list('prompt__category', flat=True) \
        .distinct().order_by('prompt__category')

    params = request.GET.copy()
    params.pop('page', None)
    for key in list(params.keys()):
        if not params.get(key):
            del params[key]
    querystring = params.urlencode()

    context = {
        'entries': page_obj.object_list,
        'page_obj': page_obj,
        'total_count': paginator.count,
        'categories': categories,
        'filters_active': bool(q or parsed_from or parsed_to or category),
        'querystring': querystring,
        'q': q,
        'date_from': date_from,
        'date_to': date_to,
        'category': category,
        'sort': sort,
    }
    return render(request, 'core/index_logged_in.html', context)


@login_required
def settings(request):

    if request.method == 'POST':
        form = SettingsForm(request.POST)
        if form.is_valid():
            user = request.user
            user.is_subscribed = form.cleaned_data['subscribed']
            user.timezone = form.cleaned_data['timezone']
            user.save()

            context = {'success': True, 'timezones': pytz.common_timezones}
            return render(request, 'core/settings.html', context)
        else:
            template = 'core/settings.html'
            context = {'form': form, 'timezones': pytz.common_timezones}
            return render(request, template, context)
    else:
        context = {'timezones': pytz.common_timezones}

    return render(request, 'core/settings.html', context)


def register(request):
    if request.user.is_authenticated:
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
        uid = force_str(urlsafe_base64_decode(uidb64))
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
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    expected = django_settings.INBOUND_SHARED_SECRET or ''
    provided = request.headers.get('X-Inbound-Secret', '')
    if not expected or not hmac.compare_digest(provided, expected):
        return HttpResponseForbidden('invalid secret')

    try:
        data = json.loads(request.body)
    except (ValueError, TypeError):
        data = request.POST

    sender = data.get('sender')
    stripped_text = data.get('stripped-text')
    if not sender or not stripped_text:
        return HttpResponseBadRequest('missing sender or stripped-text')

    try:
        user = User.objects.get(email=sender)
    except User.DoesNotExist:
        return HttpResponse('ignored: unknown sender', status=200)

    local_time = user.local_time()
    if local_time is None:
        return HttpResponse('ignored: user has no valid timezone', status=200)

    todays_prompt = Prompt.objects.filter(
        mail_day__day=local_time.day,
        mail_day__month=local_time.month,
        mail_day__year=local_time.year,
    ).first()
    if todays_prompt is None:
        return HttpResponse('ignored: no prompt for today', status=200)

    Entry.objects.create(
        content=stripped_text,
        author=user,
        prompt=todays_prompt,
        pub_date=timezone.now(),
    )
    return HttpResponse('created', status=201)


def privacy(request):
    return render(request, 'core/privacy.html')


def terms(request):
    return render(request, 'core/terms.html')
