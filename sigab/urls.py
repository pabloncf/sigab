from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("itens/<uuid:pk>/", views.item_detail, name="item-detail"),
    path("itens/<uuid:pk>/saida/", views.checkout, name="checkout"),
    path("itens/<uuid:pk>/devolucao/", views.checkin, name="checkin"),
]
