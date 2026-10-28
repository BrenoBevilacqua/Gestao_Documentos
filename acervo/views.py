from django.conf import settings
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count, ProtectedError, Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView

from .forms import DevolucaoForm, RetiradaForm, ServidorForm, SolicitanteForm
from .models import Retirada, Servidor, Solicitante


# ---------------------------------------------------------------- utilidades
class SearchListMixin:
    """Busca simples (?q=) sobre os campos de `search_fields` + paginação."""

    search_fields = ()
    paginate_by = settings.PAGINATE_BY

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:
            cond = Q()
            for f in self.search_fields:
                cond |= Q(**{f"{f}__icontains": q})
            cond |= self.extra_search_q(q)
            qs = qs.filter(cond)
        return qs

    def extra_search_q(self, q):
        """Condições adicionais de busca (ex.: campos numéricos)."""
        return Q(pk__in=[])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        params = self.request.GET.copy()
        params.pop("page", None)
        ctx["querystring"] = params.urlencode()
        return ctx


class ModelContextMixin:
    """Disponibiliza nomes do modelo e URLs para os templates genéricos."""

    url_prefix = ""

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["verbose_name"] = self.model._meta.verbose_name
        ctx["verbose_name_plural"] = self.model._meta.verbose_name_plural
        ctx["list_url"] = f"acervo:{self.url_prefix}_list"
        return ctx


class ProtectedDeleteMixin:
    """Mostra mensagem amigável quando o registro está em uso (on_delete=PROTECT)."""

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                f"Não é possível excluir “{self.object}”: existem retiradas vinculadas a este registro.",
            )
            return redirect(self.object.get_absolute_url())
        messages.success(self.request, f"{self.model._meta.verbose_name.capitalize()} excluído(a) com sucesso.")
        return response


# ---------------------------------------------------------------- painel
class PainelView(TemplateView):
    """Equivalente à aba 'Painel' da planilha."""

    template_name = "acervo/painel.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = Retirada.objects.all()
        ctx.update(
            total=qs.count(),
            emprestadas=qs.emprestadas().count(),
            devolvidas=qs.devolvidas().count(),
            atrasadas=qs.atrasadas().count(),
            lista_atrasadas=qs.atrasadas().select_related("servidor", "solicitante").order_by("prazo_devolucao")[:10],
            ultimas=qs.select_related("servidor", "solicitante")[:10],
            total_servidores=Servidor.objects.count(),
            total_solicitantes=Solicitante.objects.count(),
            prazo_dias=settings.PRAZO_DEVOLUCAO_DIAS,
            hoje=timezone.localdate(),
        )
        return ctx


# ---------------------------------------------------------------- retiradas
class RetiradaListView(SearchListMixin, ModelContextMixin, ListView):
    model = Retirada
    url_prefix = "retirada"
    search_fields = ("servidor__nome", "servidor__matricula", "solicitante__nome", "observacoes")

    def get_queryset(self):
        qs = super().get_queryset().select_related("servidor", "solicitante")
        situacao = self.request.GET.get("situacao")
        if situacao == Retirada.Situacao.DEVOLVIDO:
            qs = qs.devolvidas()
        elif situacao == Retirada.Situacao.ATRASADO:
            qs = qs.atrasadas()
        elif situacao == Retirada.Situacao.EMPRESTADO:
            qs = qs.emprestadas()
        return qs

    def extra_search_q(self, q):
        if q.isdigit():
            return Q(pk=int(q)) | Q(numero_caixa=int(q))
        return Q(pk__in=[])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["situacao"] = self.request.GET.get("situacao", "")
        ctx["situacoes"] = Retirada.Situacao.choices
        return ctx


class RetiradaDetailView(ModelContextMixin, DetailView):
    model = Retirada
    url_prefix = "retirada"


class RetiradaCreateView(SuccessMessageMixin, ModelContextMixin, CreateView):
    model = Retirada
    form_class = RetiradaForm
    url_prefix = "retirada"
    template_name = "acervo/form.html"
    success_message = "Retirada registrada com sucesso."

    def get_initial(self):
        initial = super().get_initial()
        for key in ("servidor", "solicitante"):
            if self.request.GET.get(key):
                initial[key] = self.request.GET[key]
        return initial


class RetiradaUpdateView(SuccessMessageMixin, ModelContextMixin, UpdateView):
    model = Retirada
    form_class = RetiradaForm
    url_prefix = "retirada"
    template_name = "acervo/form.html"
    success_message = "Retirada atualizada com sucesso."


class RetiradaDevolucaoView(SuccessMessageMixin, ModelContextMixin, UpdateView):
    model = Retirada
    form_class = DevolucaoForm
    url_prefix = "retirada"
    template_name = "acervo/devolucao_form.html"
    success_message = "Devolução registrada com sucesso."

    def get_initial(self):
        initial = super().get_initial()
        if not self.object.data_devolucao:
            initial["data_devolucao"] = timezone.localdate()
        return initial


class RetiradaDeleteView(ProtectedDeleteMixin, ModelContextMixin, DeleteView):
    model = Retirada
    url_prefix = "retirada"
    template_name = "acervo/confirm_delete.html"
    success_url = reverse_lazy("acervo:retirada_list")


# ---------------------------------------------------------------- servidores
class ServidorListView(SearchListMixin, ModelContextMixin, ListView):
    model = Servidor
    url_prefix = "servidor"
    search_fields = ("nome", "matricula")

    def get_queryset(self):
        return super().get_queryset().annotate(qtd_retiradas=Count("retiradas"))

    def extra_search_q(self, q):
        return Q(numero_caixa=int(q)) if q.isdigit() else Q(pk__in=[])


class ServidorDetailView(ModelContextMixin, DetailView):
    model = Servidor
    url_prefix = "servidor"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["retiradas"] = self.object.retiradas.select_related("solicitante")
        return ctx


class ServidorCreateView(SuccessMessageMixin, ModelContextMixin, CreateView):
    model = Servidor
    form_class = ServidorForm
    url_prefix = "servidor"
    template_name = "acervo/form.html"
    success_message = "Servidor cadastrado com sucesso."


class ServidorUpdateView(SuccessMessageMixin, ModelContextMixin, UpdateView):
    model = Servidor
    form_class = ServidorForm
    url_prefix = "servidor"
    template_name = "acervo/form.html"
    success_message = "Servidor atualizado com sucesso."


class ServidorDeleteView(ProtectedDeleteMixin, ModelContextMixin, DeleteView):
    model = Servidor
    url_prefix = "servidor"
    template_name = "acervo/confirm_delete.html"
    success_url = reverse_lazy("acervo:servidor_list")


# ---------------------------------------------------------------- solicitantes
class SolicitanteListView(SearchListMixin, ModelContextMixin, ListView):
    model = Solicitante
    url_prefix = "solicitante"
    search_fields = ("nome", "setor", "email", "telefone")

    def get_queryset(self):
        return super().get_queryset().annotate(qtd_retiradas=Count("retiradas"))


class SolicitanteDetailView(ModelContextMixin, DetailView):
    model = Solicitante
    url_prefix = "solicitante"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["retiradas"] = self.object.retiradas.select_related("servidor")
        return ctx


class SolicitanteCreateView(SuccessMessageMixin, ModelContextMixin, CreateView):
    model = Solicitante
    form_class = SolicitanteForm
    url_prefix = "solicitante"
    template_name = "acervo/form.html"
    success_message = "Solicitante cadastrado com sucesso."


class SolicitanteUpdateView(SuccessMessageMixin, ModelContextMixin, UpdateView):
    model = Solicitante
    form_class = SolicitanteForm
    url_prefix = "solicitante"
    template_name = "acervo/form.html"
    success_message = "Solicitante atualizado com sucesso."


class SolicitanteDeleteView(ProtectedDeleteMixin, ModelContextMixin, DeleteView):
    model = Solicitante
    url_prefix = "solicitante"
    template_name = "acervo/confirm_delete.html"
    success_url = reverse_lazy("acervo:solicitante_list")
