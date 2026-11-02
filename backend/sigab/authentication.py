"""Authentication hardening (SIGAB-021): throttling, login audit and session revocation."""

import hashlib
import hmac
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.core.exceptions import PermissionDenied
from django.dispatch import receiver
from django.utils import timezone

from .models import Account, AuditEvent, AuthenticationFailure

USERNAME_FAILURE_LIMIT = 5
IP_FAILURE_LIMIT = 20
FAILURE_WINDOW = timedelta(minutes=15)
FAILURE_RETENTION = timedelta(days=1)
SESSION_VERSION_KEY = "sigab_session_version"


def username_digest(username):
    key = settings.SECRET_KEY.encode()
    return hmac.new(key, (username or "").strip().lower().encode(), hashlib.sha256).hexdigest()


def client_ip(request):
    # REMOTE_ADDR only: X-Forwarded-For is client-controlled until a trusted proxy is defined.
    return request.META.get("REMOTE_ADDR") if request is not None else None


def is_throttled(username, ip_address):
    since = timezone.now() - FAILURE_WINDOW
    recent = AuthenticationFailure.objects.filter(occurred_at__gte=since)
    if recent.filter(username_digest=username_digest(username)).count() >= USERNAME_FAILURE_LIMIT:
        return True
    return bool(ip_address) and recent.filter(ip_address=ip_address).count() >= IP_FAILURE_LIMIT


class ThrottledModelBackend(ModelBackend):
    """ModelBackend that refuses throttled attempts and accounts of suspended organizations."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(Account.USERNAME_FIELD)
        if is_throttled(username, client_ip(request)):
            # PermissionDenied stops authentication; the form shows the generic message.
            raise PermissionDenied
        return super().authenticate(request, username=username, password=password, **kwargs)

    def user_can_authenticate(self, user):
        organization = getattr(user, "organization", None)
        if organization is not None and organization.status != "active":
            return False
        return super().user_can_authenticate(user)


def _correlation_id(request):
    return getattr(request, "correlation_id", "") or str(uuid.uuid4())


@receiver(user_login_failed)
def record_login_failure(sender, credentials, request=None, **kwargs):
    username = credentials.get(Account.USERNAME_FIELD, "")
    digest = username_digest(username)
    now = timezone.now()
    AuthenticationFailure.objects.filter(occurred_at__lt=now - FAILURE_RETENTION).delete()
    AuthenticationFailure.objects.create(
        username_digest=digest, ip_address=client_ip(request), occurred_at=now
    )
    account = Account.objects.filter(username=username).select_related("organization").first()
    AuditEvent.objects.create(
        organization=account.organization if account else None,
        actor=None,
        action="auth.login",
        object_type=Account._meta.label_lower if account else "auth.login",
        # Unknown usernames are referenced by a digest prefix, never by the typed text.
        object_id=str(account.pk) if account else digest[:16],
        occurred_at=now,
        correlation_id=_correlation_id(request),
        result="failure",
        changes={},
    )


@receiver(user_logged_in)
def record_login_success(sender, request, user, **kwargs):
    AuthenticationFailure.objects.filter(username_digest=username_digest(user.username)).delete()
    request.session[SESSION_VERSION_KEY] = user.session_version
    AuditEvent.objects.create(
        organization=user.organization,
        actor=user,
        action="auth.login",
        object_type=Account._meta.label_lower,
        object_id=str(user.pk),
        occurred_at=timezone.now(),
        correlation_id=_correlation_id(request),
        result="success",
        changes={},
    )


class SessionVersionMiddleware:
    """End sessions opened before the account's session_version was incremented."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (
            user is not None
            and user.is_authenticated
            and request.session.get(SESSION_VERSION_KEY) != user.session_version
        ):
            logout(request)
        return self.get_response(request)
