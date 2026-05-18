from datetime import time

from django import forms


# (hour 0-23, human label) — e.g. (8, "8:00 AM"). Shared by the
# onboarding and settings send-time selectors.
HOUR_CHOICES = [
    (h, time(h).strftime('%-I:00 %p')) for h in range(24)
]


class ResendConfirmationForm(forms.Form):
    email = forms.CharField(label='Email', max_length=100)


class OnboardingForm(forms.Form):
    subscribed = forms.BooleanField(required=False, initial=False)
    timezone = forms.CharField(max_length=64)
    mail_hour = forms.ChoiceField(choices=HOUR_CHOICES)


class SettingsForm(forms.Form):
    subscribed = forms.BooleanField(required=False, initial=False)
    timezone = forms.CharField(max_length=64)
    mail_hour = forms.ChoiceField(choices=HOUR_CHOICES)


class ChangeEmailForm(forms.Form):
    email = forms.EmailField(max_length=255)
