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

from .models import Account, AuditEvent, AuthenticationFailure, Organization

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


def login_identity(username, organization=None):
    # There is one installation identity space; a supplied organization cannot evade throttling.
    return (username or "").strip()


class ThrottledModelBackend(ModelBackend):
    """Authenticate against this installation only, by registration or technical username."""

    def authenticate(self, request, username=None, password=None, organization=None, **kwargs):
        if username is None:
            username = kwargs.get(Account.USERNAME_FIELD)
        if is_throttled(login_identity(username), client_ip(request)):
            raise PermissionDenied
        local = Organization.objects.filter(installation_key=1).first()
        # Legacy callers may repeat the local id, but can never select another organization.
        if organization and (local is None or str(organization) != str(local.id)):
            Account().set_password(password)
            return None
        from django.db.models import Q

        candidates = Account.objects.filter(
            Q(person__isnull=True, username=username)
            | Q(
                organization=local,
                person__is_active=True,
                person__memberships__registration=username,
                person__memberships__is_active=True,
                person__memberships__organization=local,
            ),
            revoked_at__isnull=True,
        ).distinct()
        users = [user for user in candidates if self.user_can_authenticate(user)]
        if len(users) != 1:
            Account().set_password(password)
            return None
        user = users[0]
        return user if user.check_password(password) else None

    def user_can_authenticate(self, user):
        if not super().user_can_authenticate(user):
            return False
        if user.organization_id is None:
            return user.is_superuser
        organization = user.organization
        return organization.installation_key == 1 and organization.status == "active"


def _correlation_id(request):
    return getattr(request, "correlation_id", "") or str(uuid.uuid4())


@receiver(user_login_failed)
def record_login_failure(sender, credentials, request=None, **kwargs):
    username = credentials.get(Account.USERNAME_FIELD, "")
    digest = username_digest(login_identity(username))
    now = timezone.now()
    AuthenticationFailure.objects.filter(occurred_at__lt=now - FAILURE_RETENTION).delete()
    AuthenticationFailure.objects.create(
        username_digest=digest, ip_address=client_ip(request), occurred_at=now
    )
    account = (
        Account.objects.filter(
            username=username, person__isnull=True, organization__installation_key=1
        )
        .select_related("organization")
        .first()
    )
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
    identifier = login_identity(request.POST.get("username", user.username))
    AuthenticationFailure.objects.filter(username_digest=username_digest(identifier)).delete()
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
