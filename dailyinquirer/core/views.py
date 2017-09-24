# from django.shortcuts import render

from django.http import HttpResponse

from authentication.admin import UserCreationForm


def index(request):
    return HttpResponse("The Daily Inquirer.")
