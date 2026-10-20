import uuid

from django import forms

from .models import Item, Person


class CheckoutForm(forms.Form):
    recipient = forms.ModelChoiceField(queryset=Person.objects.none(), label="Destinatário")
    confirmed = forms.BooleanField(label="Confirmo a saída após conferir o resumo")
    idempotency_key = forms.UUIDField(widget=forms.HiddenInput)

    def __init__(self, *args, organization, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["recipient"].queryset = Person.objects.filter(
            organization=organization, is_active=True, memberships__is_active=True
        ).distinct()
        self.fields["idempotency_key"].initial = uuid.uuid4()


class ReturnForm(forms.Form):
    condition = forms.ChoiceField(choices=Item.Condition, label="Condição na devolução")
    reason = forms.CharField(
        max_length=200, required=False, label="Motivo de inapto (obrigatório se inapto)"
    )
    confirmed = forms.BooleanField(label="Confirmo a devolução após conferir o item")
    idempotency_key = forms.UUIDField(widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["idempotency_key"].initial = uuid.uuid4()

    def clean(self):
        data = super().clean()
        if data.get("condition") == Item.Condition.UNFIT and not data.get("reason", "").strip():
            self.add_error("reason", "Informe o motivo de inapto.")
        return data


class ConditionForm(forms.Form):
    reason = forms.CharField(max_length=200)
    confirmed = forms.BooleanField(label="Confirmo a alteração após conferir o item")
    idempotency_key = forms.UUIDField(widget=forms.HiddenInput)

    def __init__(self, *args, target, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["reason"].label = (
            "Motivo de inapto"
            if target == Item.Condition.UNFIT
            else "Referência da conferência que libera o item"
        )
        self.fields["idempotency_key"].initial = uuid.uuid4()
