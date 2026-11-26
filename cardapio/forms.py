from decimal import Decimal, InvalidOperation

from django import forms
from django.core.exceptions import ValidationError
from unfold.widgets import UnfoldAdminTextInputWidget

from .models import Produto


def formatar_moeda(valor):
    """Decimal -> 'R$ 1.234,56'."""
    texto = f"{Decimal(valor):,.2f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


class MoedaWidget(UnfoldAdminTextInputWidget):
    class Media:
        js = ("cardapio/js/moeda_mask.js",)

    def __init__(self, attrs=None):
        super().__init__({"data-mascara": "moeda", "placeholder": "R$ 0,00", **(attrs or {})})

    def format_value(self, value):
        if value in (None, ""):
            return ""
        if isinstance(value, Decimal):
            return formatar_moeda(value)
        return value


class MoedaField(forms.DecimalField):
    """Aceita 'R$ 1.234,56' (valor mascarado) e converte para Decimal."""

    widget = MoedaWidget

    def to_python(self, value):
        if isinstance(value, str):
            limpo = value.replace("R$", "").replace(".", "").replace(" ", "").replace(",", ".")
            if not limpo:
                return None
            try:
                value = Decimal(limpo)
            except InvalidOperation:
                raise ValidationError("Informe um valor válido, como R$ 12,50.", code="invalid")
        return super().to_python(value)


class ProdutoForm(forms.ModelForm):
    preco = MoedaField(max_digits=7, decimal_places=2, min_value=Decimal("0.01"), label="Preço")

    class Meta:
        model = Produto
        fields = "__all__"
