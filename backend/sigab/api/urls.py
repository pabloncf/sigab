from django.urls import path

from . import views

app_name = "api"

urlpatterns = [
    path("session/", views.session_detail, name="session-detail"),
    path("session/logout/", views.session_logout, name="session-logout"),
    path("items/", views.item_list, name="item-list"),
    path("items/<uuid:pk>/", views.item_detail, name="item-detail"),
    path("items/<uuid:pk>/checkout/", views.item_checkout, name="item-checkout"),
    path("items/<uuid:pk>/return/", views.item_return, name="item-return"),
    path("items/<uuid:pk>/condition/", views.item_condition, name="item-condition"),
    path("items/<uuid:pk>/recipients/", views.recipient_list, name="recipient-list"),
]
