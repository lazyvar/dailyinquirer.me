from django import forms

class ResendConfirmationForm(forms.Form):
    email = forms.CharField(label='Email', max_length=100)