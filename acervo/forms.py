from django import forms

from .models import Retirada, Servidor, Solicitante


class BootstrapMixin:
    """Aplica classes do Bootstrap 5 a todos os widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, (forms.CheckboxInput,)):
                widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault("class", "form-select")
            else:
                widget.attrs.setdefault("class", "form-control")


class DateInput(forms.DateInput):
    input_type = "date"

    def __init__(self, **kwargs):
        kwargs.setdefault("format", "%Y-%m-%d")
        super().__init__(**kwargs)


class ServidorForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Servidor
        fields = ["nome", "matricula", "numero_caixa", "observacoes"]
        widgets = {"observacoes": forms.Textarea(attrs={"rows": 3})}


class SolicitanteForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Solicitante
        fields = ["nome", "setor", "email", "telefone"]


class RetiradaForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Retirada
        fields = ["servidor", "numero_caixa", "solicitante", "data_retirada", "prazo_devolucao",
                  "data_devolucao", "observacoes", "anexo"]
        widgets = {
            "data_retirada": DateInput(),
            "prazo_devolucao": DateInput(),
            "data_devolucao": DateInput(),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }


class DevolucaoForm(BootstrapMixin, forms.ModelForm):
    """Formulário rápido para registrar a devolução da ficha."""

    class Meta:
        model = Retirada
        fields = ["data_devolucao", "observacoes"]
        widgets = {"data_devolucao": DateInput(), "observacoes": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["data_devolucao"].required = True
