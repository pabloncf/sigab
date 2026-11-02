from django.urls import path, re_path

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
    path("people/", views.person_list, name="person-list"),
    path("people/<uuid:pk>/", views.person_detail, name="person-detail"),
    path("people/<uuid:pk>/status/", views.person_status, name="person-status"),
    path("people/<uuid:pk>/memberships/", views.person_memberships, name="person-memberships"),
    path("people/<uuid:pk>/account/", views.person_account, name="person-account"),
    path("memberships/<uuid:pk>/status/", views.membership_status, name="membership-status"),
    *[
        path(
            f"accounts/<uuid:pk>/{action}/",
            views.account_action,
            {"action": action},
            name=f"account-{action}",
        )
        for action in views.ACCOUNT_ACTIONS
    ],
    path("units/", views.unit_list, name="unit-list"),
    re_path(r"^(?P<path>.*)$", views.not_found, name="not-found"),
]
