from django.urls import path
from .views import HomeView, FichaInscricaoView, BalanceteView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('ficha/', FichaInscricaoView.as_view(), name='ficha'),
    path('balancete/', BalanceteView.as_view(), name='balancete'),
]
