from django.contrib import admin

from .models import Retirada, Servidor, Solicitante


@admin.register(Servidor)
class ServidorAdmin(admin.ModelAdmin):
    list_display = ("nome", "matricula", "numero_caixa")
    search_fields = ("nome", "matricula")
    list_filter = ("numero_caixa",)


@admin.register(Solicitante)
class SolicitanteAdmin(admin.ModelAdmin):
    list_display = ("nome", "setor", "email", "telefone")
    search_fields = ("nome", "setor", "email")
    list_filter = ("setor",)


@admin.register(Retirada)
class RetiradaAdmin(admin.ModelAdmin):
    list_display = ("id", "numero_caixa", "servidor", "solicitante", "data_retirada",
                    "prazo_devolucao", "data_devolucao", "situacao")
    list_display_links = ("id", "servidor")
    search_fields = ("servidor__nome", "servidor__matricula", "solicitante__nome", "observacoes")
    list_filter = ("data_retirada", "data_devolucao", "solicitante")
    autocomplete_fields = ("servidor", "solicitante")
    date_hierarchy = "data_retirada"

    @admin.display(description="situação")
    def situacao(self, obj):
        return obj.situacao
