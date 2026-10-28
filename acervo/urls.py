from django.urls import path

from . import views

app_name = "acervo"

urlpatterns = [
    path("", views.PainelView.as_view(), name="painel"),

    path("retiradas/", views.RetiradaListView.as_view(), name="retirada_list"),
    path("retiradas/nova/", views.RetiradaCreateView.as_view(), name="retirada_create"),
    path("retiradas/<int:pk>/", views.RetiradaDetailView.as_view(), name="retirada_detail"),
    path("retiradas/<int:pk>/editar/", views.RetiradaUpdateView.as_view(), name="retirada_update"),
    path("retiradas/<int:pk>/devolver/", views.RetiradaDevolucaoView.as_view(), name="retirada_devolucao"),
    path("retiradas/<int:pk>/excluir/", views.RetiradaDeleteView.as_view(), name="retirada_delete"),

    path("servidores/", views.ServidorListView.as_view(), name="servidor_list"),
    path("servidores/novo/", views.ServidorCreateView.as_view(), name="servidor_create"),
    path("servidores/<int:pk>/", views.ServidorDetailView.as_view(), name="servidor_detail"),
    path("servidores/<int:pk>/editar/", views.ServidorUpdateView.as_view(), name="servidor_update"),
    path("servidores/<int:pk>/excluir/", views.ServidorDeleteView.as_view(), name="servidor_delete"),

    path("solicitantes/", views.SolicitanteListView.as_view(), name="solicitante_list"),
    path("solicitantes/novo/", views.SolicitanteCreateView.as_view(), name="solicitante_create"),
    path("solicitantes/<int:pk>/", views.SolicitanteDetailView.as_view(), name="solicitante_detail"),
    path("solicitantes/<int:pk>/editar/", views.SolicitanteUpdateView.as_view(), name="solicitante_update"),
    path("solicitantes/<int:pk>/excluir/", views.SolicitanteDeleteView.as_view(), name="solicitante_delete"),
]
