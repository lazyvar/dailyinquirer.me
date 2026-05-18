from django.shortcuts import render, redirect, get_object_or_404
from authentication.admin import UserCreationForm
from django.http import (HttpResponse, HttpResponseBadRequest,
                          HttpResponseForbidden, HttpResponseNotAllowed)
from django.conf import settings as django_settings
from authentication.models import User
from django.contrib.auth.decorators import login_required
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from authentication.tokens import account_activation_token, email_change_token
from django.contrib.auth import login, logout
from django.contrib.auth.forms import PasswordResetForm
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils.dateparse import parse_date

from core.models import Entry, Prompt
from core.forms import (HOUR_CHOICES, ChangeEmailForm, EntryEditForm,
                        OnboardingForm, ResendConfirmationForm, SettingsForm)
from core.utils import mail_newsletter, read_unsubscribe_token
from core.email import send_activation_email, send_email_change_emails

from datetime import datetime
import hmac

import json
import pytz


ENTRIES_PER_PAGE = 25


def index(request):
    return render(request, 'core/index.html')


def _dashboard(request):
    entries = Entry.objects.filter(
        author=request.user,
        archived_at__isnull=True).select_related('prompt')

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

    archived_count = Entry.objects.filter(
        author=request.user, archived_at__isnull=False).count()

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
        'archived_count': archived_count,
    }
    return render(request, 'core/index_logged_in.html', context)


@login_required
def dashboard(request):
    if not request.user.confirmed_email:
        logout(request)
        return redirect('unconfirmed_email')
    return _dashboard(request)


@login_required
def entry_detail(request, pk):
    if request.method not in ('GET', 'HEAD', 'POST'):
        return HttpResponseNotAllowed(['GET', 'POST'])

    entry = get_object_or_404(
        Entry.objects.select_related('prompt'),
        pk=pk, author=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'save':
            form = EntryEditForm(request.POST)
            if form.is_valid():
                entry.content = form.cleaned_data['content']
                entry.save()
                messages.success(request, 'Your entry was updated.')
                return redirect('entry_detail', pk=entry.pk)
            return render(request, 'core/entry_detail.html', {
                'entry': entry, 'mode': 'edit', 'form': form})
        if action == 'archive':
            entry.archived_at = timezone.now()
            entry.save()
            messages.success(request, 'Entry archived.')
            return redirect('dash')
        if action == 'restore':
            entry.archived_at = None
            entry.save()
            messages.success(request, 'Entry restored.')
            return redirect('entry_detail', pk=entry.pk)
        if action == 'delete':
            entry.delete()
            messages.success(request, 'Entry deleted.')
            return redirect('dash')
        return HttpResponseBadRequest('unknown action')

    mode = 'view'
    if request.GET.get('edit'):
        mode = 'edit'
    elif request.GET.get('confirm_delete'):
        mode = 'confirm_delete'

    context = {'entry': entry, 'mode': mode}
    if mode == 'edit':
        context['form'] = EntryEditForm(initial={'content': entry.content})
    return render(request, 'core/entry_detail.html', context)


@login_required
def archived_entries(request):
    entries = Entry.objects.filter(
        author=request.user, archived_at__isnull=False
    ).select_related('prompt').order_by('-archived_at')
    return render(request, 'core/archived.html', {'entries': entries})


@login_required
def settings(request):

    if request.method == 'POST':
        form = SettingsForm(request.POST)
        if form.is_valid():
            user = request.user
            user.is_subscribed = form.cleaned_data['subscribed']
            user.timezone = form.cleaned_data['timezone']
            user.mail_time = int(form.cleaned_data['mail_hour']) * 60
            user.save()

            context = {'success': True, 'timezones': pytz.common_timezones,
                       'hours': HOUR_CHOICES}
            return render(request, 'core/settings.html', context)
        else:
            template = 'core/settings.html'
            context = {'form': form, 'timezones': pytz.common_timezones,
                       'hours': HOUR_CHOICES}
            return render(request, template, context)
    else:
        context = {'timezones': pytz.common_timezones, 'hours': HOUR_CHOICES}
        email_change = request.GET.get('email_change')
        if email_change == 'confirmed':
            context['email_change_confirmed'] = True
        elif email_change == 'unavailable':
            context['email_change_error'] = (
                "We couldn't complete the email change — that address "
                "is no longer available.")

    return render(request, 'core/settings.html', context)


@login_required
def send_password_reset(request):
    """Email a password-reset link to the signed-in user without leaving
    the settings page."""
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    form = PasswordResetForm({'email': request.user.email})
    if form.is_valid():
        form.save(
            request=request,
            use_https=request.is_secure(),
            email_template_name='email/password_reset.txt',
            html_email_template_name='email/password_reset.html',
            subject_template_name='email/password_reset_subject.txt',
        )
    context = {'timezones': pytz.common_timezones, 'hours': HOUR_CHOICES,
               'password_reset_sent': True}
    return render(request, 'core/settings.html', context)


@login_required
def onboarding(request):
    if request.user.onboarded:
        return redirect('dash')

    if request.method == 'POST':
        form = OnboardingForm(request.POST)
        if form.is_valid():
            user = request.user
            user.is_subscribed = form.cleaned_data['subscribed']
            user.timezone = form.cleaned_data['timezone']
            user.mail_time = int(form.cleaned_data['mail_hour']) * 60
            user.onboarded = True
            user.save()
            return redirect('dash')
        context = {'form': form, 'timezones': pytz.common_timezones,
                   'hours': HOUR_CHOICES}
        return render(request, 'core/onboarding.html', context)

    context = {'timezones': pytz.common_timezones, 'hours': HOUR_CHOICES}
    return render(request, 'core/onboarding.html', context)


def register(request):
    if request.user.is_authenticated:
        return redirect('dash')
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
                context = {'form': form}
                return render(request, template, context)
        else:
            template = 'registration/register.html'
            return render(request, template, {})


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

        return redirect('dash')
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


@login_required
def manage_email_change(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    user = request.user
    action = request.POST.get('action', 'request')
    context = {'timezones': pytz.common_timezones}

    if action == 'cancel':
        if user.pending_email:
            user.pending_email = None
            user.save()
            context['email_change_canceled'] = True
        return render(request, 'core/settings.html', context)

    if action == 'resend':
        if user.pending_email:
            send_email_change_emails(request, user)
            context['email_change_requested'] = True
        return render(request, 'core/settings.html', context)

    form = ChangeEmailForm(request.POST)
    if not form.is_valid():
        context['email_change_error'] = 'Enter a valid email address.'
        context['submitted_email'] = request.POST.get('email', '')
        return render(request, 'core/settings.html', context)

    new_email = User.objects.normalize_email(form.cleaned_data['email'])
    # normalize_email only lowercases the domain; compare fully
    # case-insensitively so "OLD@x.com" still matches a stored "old@x.com".
    if new_email.lower() == user.email.lower():
        context['email_change_error'] = "That's already your email address."
        context['submitted_email'] = new_email
        return render(request, 'core/settings.html', context)

    taken = User.objects.filter(email__iexact=new_email) \
        .exclude(pk=user.pk).exists()
    if taken:
        context['email_change_error'] = 'That email address is already in use.'
        context['submitted_email'] = new_email
        return render(request, 'core/settings.html', context)

    user.pending_email = new_email
    user.save()
    send_email_change_emails(request, user)
    context['email_change_requested'] = True
    return render(request, 'core/settings.html', context)


def confirm_email_change(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if (user is None or not user.pending_email
            or not email_change_token.check_token(user, token)):
        return HttpResponse('Email change link is invalid!')

    new_email = user.pending_email
    taken = User.objects.filter(email__iexact=new_email) \
        .exclude(pk=user.pk).exists()
    if taken:
        user.pending_email = None
        user.save()
        return redirect('/settings/?email_change=unavailable')

    user.email = new_email
    user.pending_email = None
    user.save()
    return redirect('/settings/?email_change=confirmed')


def privacy(request):
    return render(request, 'core/privacy.html')


def terms(request):
    return render(request, 'core/terms.html')


def about(request):
    return render(request, 'core/about.html')


def unsubscribe(request):
    token = request.POST.get('token') or request.GET.get('token', '')
    user = read_unsubscribe_token(token)
    if user is None:
        return render(request, 'core/unsubscribe.html', {'state': 'error'})

    if request.method == 'POST':
        if user.is_subscribed:
            user.is_subscribed = False
            user.save()
        return render(request, 'core/unsubscribe.html',
                      {'state': 'done', 'email': user.email})

    state = 'confirm' if user.is_subscribed else 'done'
    return render(request, 'core/unsubscribe.html',
                  {'state': state, 'email': user.email, 'token': token})


@csrf_exempt
def unsubscribe_one_click(request):
    """RFC 8058 List-Unsubscribe one-click endpoint. Mail clients POST here
    directly; the token is in the query string."""
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    user = read_unsubscribe_token(request.GET.get('token', ''))
    if user is None:
        return HttpResponseBadRequest('invalid token')

    if user.is_subscribed:
        user.is_subscribed = False
        user.save()
    return HttpResponse('unsubscribed', status=200)
