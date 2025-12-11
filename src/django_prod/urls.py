from django.urls import path
from .views import prod_welcome_index

urlpatterns = [
    path('', prod_welcome_index, name='prod_welcome_index'),
]