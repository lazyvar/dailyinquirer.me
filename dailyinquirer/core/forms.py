from django import forms


class ResendConfirmationForm(forms.Form):
    email = forms.CharField(label='Email', max_length=100)


class SettingsForm(forms.Form):
    subscribed = forms.BooleanField(required=False, initial=False)
    timezone = forms.CharField(max_length=64)
