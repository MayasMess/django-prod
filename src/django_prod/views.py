from django.shortcuts import render


def prod_welcome_index(request):
    return render(request, 'django_prod/welcome.html')