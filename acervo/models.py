from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Case, CharField, Q, Value, When
from django.urls import reverse
from django.utils import timezone


class Servidor(models.Model):
    """Servidor cuja ficha física está guardada no acervo."""

    nome = models.CharField("nome do servidor", max_length=200)
    matricula = models.CharField("matrícula", max_length=50, blank=True, help_text="Opcional (se houver).")
    numero_caixa = models.PositiveIntegerField(
        "nº da caixa", null=True, blank=True, help_text="Caixa do acervo onde a ficha fica guardada."
    )
    observacoes = models.TextField("observações", blank=True)
    criado_em = models.DateTimeField("criado em", auto_now_add=True)
    atualizado_em = models.DateTimeField("atualizado em", auto_now=True)

    class Meta:
        verbose_name = "servidor"
        verbose_name_plural = "servidores"
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} ({self.matricula})" if self.matricula else self.nome

    def get_absolute_url(self):
        return reverse("acervo:servidor_detail", args=[self.pk])


class Solicitante(models.Model):
    """Pessoa (normalmente do RH) que solicita a retirada de fichas."""

    nome = models.CharField("nome", max_length=200)
    setor = models.CharField("setor", max_length=100, default="RH")
    email = models.EmailField("e-mail", blank=True)
    telefone = models.CharField("telefone / ramal", max_length=30, blank=True)
    criado_em = models.DateTimeField("criado em", auto_now_add=True)
    atualizado_em = models.DateTimeField("atualizado em", auto_now=True)

    class Meta:
        verbose_name = "solicitante"
        verbose_name_plural = "solicitantes"
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} ({self.setor})" if self.setor else self.nome

    def get_absolute_url(self):
        return reverse("acervo:solicitante_detail", args=[self.pk])


class RetiradaQuerySet(models.QuerySet):
    def com_situacao(self):
        """Anota a situação calculada (mesma regra da coluna 'Situação' da planilha)."""
        hoje = timezone.localdate()
        return self.annotate(
            situacao_calc=Case(
                When(data_devolucao__isnull=False, then=Value(Retirada.Situacao.DEVOLVIDO)),
                When(prazo_devolucao__lt=hoje, then=Value(Retirada.Situacao.ATRASADO)),
                default=Value(Retirada.Situacao.EMPRESTADO),
                output_field=CharField(),
            )
        )

    def devolvidas(self):
        return self.filter(data_devolucao__isnull=False)

    def atrasadas(self):
        return self.filter(data_devolucao__isnull=True, prazo_devolucao__lt=timezone.localdate())

    def emprestadas(self):
        return self.filter(data_devolucao__isnull=True).filter(
            Q(prazo_devolucao__isnull=True) | Q(prazo_devolucao__gte=timezone.localdate())
        )


class Retirada(models.Model):
    """Linha da aba 'Controle': retirada e devolução de uma ficha do acervo."""

    class Situacao(models.TextChoices):
        EMPRESTADO = "Emprestado", "Emprestado"
        DEVOLVIDO = "Devolvido", "Devolvido"
        ATRASADO = "Atrasado", "Atrasado"

    numero_caixa = models.PositiveIntegerField(
        "nº da caixa", null=True, blank=True,
        help_text="Caixa de onde a ficha foi retirada. Se vazio, usa a caixa cadastrada no servidor.",
    )
    servidor = models.ForeignKey(
        Servidor, verbose_name="servidor", on_delete=models.PROTECT, related_name="retiradas"
    )
    solicitante = models.ForeignKey(
        Solicitante, verbose_name="solicitante (RH)", on_delete=models.PROTECT, related_name="retiradas"
    )
    data_retirada = models.DateField("data de retirada", default=timezone.localdate)
    prazo_devolucao = models.DateField(
        "prazo de devolução", null=True, blank=True,
        help_text="Se vazio, é calculado automaticamente (data de retirada + prazo padrão).",
    )
    data_devolucao = models.DateField("data de devolução", null=True, blank=True)
    observacoes = models.TextField("observações", blank=True)
    anexo = models.FileField(
        "anexo", upload_to="retiradas/%Y/%m/", blank=True,
        help_text="Opcional: protocolo assinado, digitalização da ficha etc.",
    )
    criado_em = models.DateTimeField("criado em", auto_now_add=True)
    atualizado_em = models.DateTimeField("atualizado em", auto_now=True)

    objects = RetiradaQuerySet.as_manager()

    class Meta:
        verbose_name = "retirada de ficha"
        verbose_name_plural = "retiradas de fichas"
        ordering = ["-data_retirada", "-id"]

    def __str__(self):
        return f"Nº {self.pk} — {self.servidor.nome} ({self.data_retirada:%d/%m/%Y})"

    def get_absolute_url(self):
        return reverse("acervo:retirada_detail", args=[self.pk])

    def clean(self):
        if self.data_devolucao and self.data_retirada and self.data_devolucao < self.data_retirada:
            raise ValidationError({"data_devolucao": "A data de devolução não pode ser anterior à data de retirada."})
        if self.prazo_devolucao and self.data_retirada and self.prazo_devolucao < self.data_retirada:
            raise ValidationError({"prazo_devolucao": "O prazo não pode ser anterior à data de retirada."})

    def save(self, *args, **kwargs):
        if not self.prazo_devolucao and self.data_retirada:
            self.prazo_devolucao = self.data_retirada + timedelta(days=settings.PRAZO_DEVOLUCAO_DIAS)
        if self.numero_caixa is None and self.servidor_id and self.servidor.numero_caixa is not None:
            self.numero_caixa = self.servidor.numero_caixa
        super().save(*args, **kwargs)

    @property
    def situacao(self):
        if self.data_devolucao:
            return self.Situacao.DEVOLVIDO
        if self.prazo_devolucao and timezone.localdate() > self.prazo_devolucao:
            return self.Situacao.ATRASADO
        return self.Situacao.EMPRESTADO

    @property
    def situacao_cor(self):
        """Cores da planilha: laranja = emprestado, verde = devolvido, vermelho = atrasado."""
        return {
            self.Situacao.DEVOLVIDO: "success",
            self.Situacao.ATRASADO: "danger",
            self.Situacao.EMPRESTADO: "warning",
        }[self.situacao]

    @property
    def dias_em_atraso(self):
        if self.situacao == self.Situacao.ATRASADO:
            return (timezone.localdate() - self.prazo_devolucao).days
        return 0
