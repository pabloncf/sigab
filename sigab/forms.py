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
    confirmed = forms.BooleanField(label="Confirmo a devolução após conferir o item")
    idempotency_key = forms.UUIDField(widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["idempotency_key"].initial = uuid.uuid4()
