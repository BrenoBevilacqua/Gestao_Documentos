from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Retirada, Servidor, Solicitante


class CrudTests(TestCase):
    def setUp(self):
        self.servidor = Servidor.objects.create(nome="Jefferson", matricula="1", numero_caixa=1)
        self.solicitante = Solicitante.objects.create(nome="Pedro")

    def test_paginas_respondem(self):
        r = Retirada.objects.create(servidor=self.servidor, solicitante=self.solicitante)
        nomes = ["acervo:painel", "acervo:retirada_list", "acervo:retirada_create", "acervo:servidor_list",
                 "acervo:servidor_create", "acervo:solicitante_list", "acervo:solicitante_create"]
        for nome in nomes:
            self.assertEqual(self.client.get(reverse(nome)).status_code, 200, nome)
        for prefixo, obj in (("retirada", r), ("servidor", self.servidor), ("solicitante", self.solicitante)):
            for acao in ("detail", "update", "delete"):
                url = reverse(f"acervo:{prefixo}_{acao}", args=[obj.pk])
                self.assertEqual(self.client.get(url).status_code, 200, url)
        self.assertEqual(self.client.get(reverse("acervo:retirada_devolucao", args=[r.pk])).status_code, 200)

    def test_prazo_e_situacao(self):
        hoje = timezone.localdate()
        r = Retirada.objects.create(servidor=self.servidor, solicitante=self.solicitante, data_retirada=hoje)
        self.assertEqual(r.prazo_devolucao, hoje + timedelta(days=5))
        self.assertEqual(r.numero_caixa, 1)
        self.assertEqual(r.situacao, "Emprestado")
        antiga = Retirada.objects.create(servidor=self.servidor, solicitante=self.solicitante,
                                         data_retirada=hoje - timedelta(days=10))
        self.assertEqual(antiga.situacao, "Atrasado")
        antiga.data_devolucao = hoje
        antiga.save()
        self.assertEqual(antiga.situacao, "Devolvido")
        self.assertEqual(Retirada.objects.emprestadas().count(), 1)
        self.assertEqual(Retirada.objects.devolvidas().count(), 1)
        self.assertEqual(Retirada.objects.atrasadas().count(), 0)

    @override_settings(MEDIA_ROOT="/tmp/test_media_acervo")
    def test_crud_via_post(self):
        # Create
        resp = self.client.post(reverse("acervo:retirada_create"), {
            "servidor": self.servidor.pk, "solicitante": self.solicitante.pk,
            "data_retirada": "2026-10-20", "observacoes": "teste",
            "anexo": SimpleUploadedFile("protocolo.txt", b"ok"),
        })
        self.assertEqual(resp.status_code, 302)
        r = Retirada.objects.get()
        self.assertTrue(r.anexo.name.endswith(".txt"))
        # Update (devolução)
        resp = self.client.post(reverse("acervo:retirada_devolucao", args=[r.pk]),
                                {"data_devolucao": "2026-10-21", "observacoes": "devolvida"})
        self.assertEqual(resp.status_code, 302)
        r.refresh_from_db()
        self.assertEqual(r.situacao, "Devolvido")
        # Busca e filtro
        self.assertContains(self.client.get(reverse("acervo:retirada_list") + "?q=Jeff&situacao=Devolvido"), "Jefferson")
        # Delete protegido
        resp = self.client.post(reverse("acervo:servidor_delete", args=[self.servidor.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Servidor.objects.filter(pk=self.servidor.pk).exists())
        # Delete
        self.client.post(reverse("acervo:retirada_delete", args=[r.pk]))
        self.assertFalse(Retirada.objects.exists())
        self.client.post(reverse("acervo:servidor_delete", args=[self.servidor.pk]))
        self.assertFalse(Servidor.objects.exists())

    def test_validacao_datas(self):
        resp = self.client.post(reverse("acervo:retirada_create"), {
            "servidor": self.servidor.pk, "solicitante": self.solicitante.pk,
            "data_retirada": "2026-10-20", "data_devolucao": "2026-10-01",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "não pode ser anterior")


class ImportacaoTests(TestCase):
    def test_importar_planilha(self):
        from django.core.management import call_command
        call_command("importar_planilha", verbosity=0)
        r = Retirada.objects.get()
        self.assertEqual(r.servidor.nome, "Jefferson")
        self.assertEqual(str(r.data_retirada), "2026-08-24")
        call_command("importar_planilha", verbosity=0)
        self.assertEqual(Retirada.objects.count(), 1)
