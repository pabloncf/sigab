from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from sigab.models import EquipmentType, Person, PersonRestriction, RestrictionEvent
from sigab.permissions import has_permission
from sigab.services import ConflictError, NotFoundError, RestrictedCheckout, audit


def require_manager(ctx):
    if not has_permission(ctx.actor, "restriction.manage", ctx.organization):
        raise PermissionDenied


def snapshot(restriction):
    return {
        "category": restriction.category,
        "summary": restriction.summary,
        "source": restriction.source,
        "reference": restriction.reference,
        "starts_at": restriction.starts_at.isoformat(),
        "ends_at": restriction.ends_at.isoformat() if restriction.ends_at else None,
        "equipment_type_ids": sorted(
            str(pk) for pk in restriction.equipment_types.values_list("pk", flat=True)
        ),
        "closed_at": restriction.closed_at.isoformat() if restriction.closed_at else None,
    }


def validate_fields(ctx, *, category, summary, source, starts_at, ends_at, equipment_type_ids):
    if category not in PersonRestriction.Category.values:
        raise ValidationError({"category": "Categoria inválida."})
    if not summary.strip() or not source.strip():
        raise ValidationError("Motivo resumido e fonte são obrigatórios.")
    if timezone.is_naive(starts_at) or (ends_at and timezone.is_naive(ends_at)):
        raise ValidationError("Informe instantes com fuso horário.")
    if ends_at and ends_at <= starts_at:
        raise ValidationError({"ends_at": "O fim deve ser posterior ao início."})
    types = list(
        EquipmentType.objects.filter(organization=ctx.organization, id__in=equipment_type_ids)
    )
    if len(types) != len(set(equipment_type_ids)):
        raise ValidationError({"equipment_type_ids": "Tipo de equipamento inválido."})
    return types


def record_event(ctx, restriction, action, before, reason):
    RestrictionEvent.objects.create(
        restriction=restriction,
        actor=ctx.actor,
        occurred_at=timezone.now(),
        action=action,
        reason=reason,
        before=before,
        after=snapshot(restriction),
    )
    # Free-text personal data stays in the restricted record, never in the audit feed.
    audit(
        ctx,
        f"restriction.{action}",
        restriction,
        {
            "person_id": str(restriction.person_id),
            "fields": sorted(snapshot(restriction)),
        },
    )


@transaction.atomic
def create_restriction(
    ctx,
    *,
    person_id,
    category,
    summary,
    source,
    reference,
    starts_at,
    ends_at,
    equipment_type_ids,
    confirmed,
):
    require_manager(ctx)
    if not confirmed:
        raise ValidationError("A confirmação explícita é obrigatória.")
    person = (
        Person.objects.select_for_update()
        .filter(pk=person_id, organization=ctx.organization)
        .first()
    )
    if not person:
        raise NotFoundError
    types = validate_fields(
        ctx,
        category=category,
        summary=summary,
        source=source,
        starts_at=starts_at,
        ends_at=ends_at,
        equipment_type_ids=equipment_type_ids,
    )
    restriction = PersonRestriction(
        organization=ctx.organization,
        person=person,
        category=category,
        summary=summary.strip(),
        source=source.strip(),
        reference=reference.strip(),
        starts_at=starts_at,
        ends_at=ends_at,
        created_by=ctx.actor,
    )
    restriction.full_clean()
    restriction.save()
    restriction.equipment_types.set(types)
    record_event(ctx, restriction, "registered", {}, summary.strip())
    return restriction


@transaction.atomic
def change_restriction(ctx, *, restriction_id, reason, confirmed, close=False, **fields):
    require_manager(ctx)
    restriction = PersonRestriction.objects.filter(
        pk=restriction_id, organization=ctx.organization
    ).first()
    if not restriction:
        raise NotFoundError
    Person.objects.select_for_update().get(pk=restriction.person_id)
    restriction.refresh_from_db()
    if not confirmed or not reason.strip():
        raise ValidationError("Alteração exige confirmação e motivo.")
    if restriction.closed_at:
        raise ConflictError("A restrição já foi encerrada.")
    before = snapshot(restriction)
    if close:
        restriction.closed_at = timezone.now()
        restriction.closed_by = ctx.actor
    else:
        types = validate_fields(
            ctx,
            **{
                key: fields[key]
                for key in (
                    "category",
                    "summary",
                    "source",
                    "starts_at",
                    "ends_at",
                    "equipment_type_ids",
                )
            },
        )
        for key in ("category", "summary", "source", "reference", "starts_at", "ends_at"):
            setattr(restriction, key, fields[key])
        restriction.full_clean()
        restriction.equipment_types.set(types)
    restriction.save()
    record_event(ctx, restriction, "closed" if close else "changed", before, reason.strip())
    return restriction


def assert_eligible(ctx, person, equipment_type_id):
    """Caller holds the person's row lock until the delivery transaction commits."""
    now = timezone.now()
    active = (
        PersonRestriction.objects.filter(
            organization=ctx.organization,
            person=person,
            closed_at__isnull=True,
            starts_at__lte=now,
        )
        .filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now))
        .filter(Q(equipment_types__isnull=True) | Q(equipment_types__pk=equipment_type_id))
    )
    restriction_id = active.values_list("pk", flat=True).first()
    if restriction_id:
        raise RestrictedCheckout(person.pk, restriction_id, equipment_type_id)
