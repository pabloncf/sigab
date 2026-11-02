from django.urls import path, re_path

from . import views

app_name = "api"

urlpatterns = [
    path("session/", views.session_detail, name="session-detail"),
    path("session/logout/", views.session_logout, name="session-logout"),
    path("items/", views.item_list, name="item-list"),
    path("items/<uuid:pk>/", views.item_detail, name="item-detail"),
    path("items/<uuid:pk>/events/", views.item_events, name="item-events"),
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
    path("accounts/<uuid:pk>/grants/", views.account_grants, name="account-grants"),
    path("grants/<uuid:pk>/revoke/", views.grant_revoke, name="grant-revoke"),
    path("roles/", views.role_list, name="role-list"),
    path("units/", views.unit_list, name="unit-list"),
    path("units/<uuid:pk>/", views.unit_detail, name="unit-detail"),
    path("units/<uuid:pk>/status/", views.unit_status, name="unit-status"),
    path("units/<uuid:pk>/locations/", views.unit_locations, name="unit-locations"),
    path("locations/<uuid:pk>/status/", views.location_status, name="location-status"),
    path("equipment-types/", views.equipment_type_list, name="equipment-type-list"),
    path("equipment-types/<uuid:pk>/", views.equipment_type_detail, name="equipment-type-detail"),
    path(
        "equipment-types/<uuid:pk>/status/",
        views.equipment_type_status,
        name="equipment-type-status",
    ),
    re_path(r"^(?P<path>.*)$", views.not_found, name="not-found"),
]
