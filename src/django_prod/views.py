import django
from django.shortcuts import render


def prod_welcome_index(request):
    version = django.get_version()
    return render(request, "django_prod/welcome.html", {"version": version})
