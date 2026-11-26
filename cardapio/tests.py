import io
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from .models import Oferta, Produto, SlideCarrossel

LANDING = "/"


class CoreModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser("adm", "a@a.com", "x")
        self.client.force_login(self.user)

    def _criar_pelo_admin(self, nome="Z"):
        return self.client.post("/admin/cardapio/produto/add/", {
            "nome": nome, "descricao": "", "preco": "5", "ativo": "on",
            "ofertas-TOTAL_FORMS": 0, "ofertas-INITIAL_FORMS": 0,
            "ofertas-MIN_NUM_FORMS": 0, "ofertas-MAX_NUM_FORMS": 1000,
        })

    def test_auditoria_preenchida_automaticamente(self):
        self._criar_pelo_admin()
        p = Produto.objects.get(nome="Z")
        self.assertEqual(p.criado_por, self.user)
        self.assertEqual(p.atualizado_por, self.user)

    def test_exclusao_pelo_admin_e_logica_e_some_do_front(self):
        self._criar_pelo_admin()
        p = Produto.objects.get(nome="Z")
        self.assertContains(self.client.get(LANDING), "cookie-card__name")

        r = self.client.post("/admin/cardapio/produto/", {
            "action": "delete_selected", "_selected_action": [p.pk], "post": "yes",
        })
        self.assertEqual(r.status_code, 302)
        p.refresh_from_db()
        self.assertFalse(p.ativo)
        self.assertEqual(p.atualizado_por, self.user)
        self.assertContains(self.client.get(LANDING), "Sem produtos registrados")

    def test_delete_de_instancia_e_queryset_sao_logicos(self):
        a = Produto.objects.create(nome="A", preco=1)
        b = Produto.objects.create(nome="B", preco=1)
        a.delete()
        Produto.objects.filter(pk=b.pk).delete()
        self.assertEqual(Produto.objects.filter(ativo=True).count(), 0)
        self.assertEqual(Produto.objects.count(), 2)

    def test_add_nao_exibe_campos_do_core_e_edicao_exibe_auditoria(self):
        r = self.client.get("/admin/cardapio/produto/add/")
        for campo in ("criado_em", "criado_por", "atualizado_em", "atualizado_por"):
            self.assertNotContains(r, f"id_{campo}")
            self.assertNotContains(r, f'name="{campo}"')
        self.assertNotContains(r, 'name="ativo"')

        p = Produto.objects.create(nome="E", preco=1)
        r = self.client.get(f"/admin/cardapio/produto/{p.pk}/change/")
        self.assertContains(r, "Criado em")
        self.assertContains(r, 'name="ativo"')


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class CarrosselTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser("adm", "a@a.com", "x")
        self.client.force_login(self.user)

    def _png(self, nome="a.png"):
        buf = io.BytesIO()
        Image.new("RGB", (10, 10), "red").save(buf, "PNG")
        return SimpleUploadedFile(nome, buf.getvalue(), content_type="image/png")

    def test_hero_sem_slides_nao_renderiza_carrossel(self):
        self.assertNotContains(self.client.get(LANDING), "hero__carrossel")

    def test_upload_pelo_admin_aparece_no_hero(self):
        r = self.client.post("/admin/cardapio/slidecarrossel/add/", {
            "imagem": self._png(), "alt": "x", "ordem": 0,
        })
        self.assertEqual(r.status_code, 302)
        slide = SlideCarrossel.objects.get()
        self.assertEqual(slide.criado_por, self.user)
        self.assertContains(self.client.get(LANDING), slide.imagem.url)

    def test_slide_excluido_some_do_hero(self):
        slide = SlideCarrossel.objects.create(imagem=self._png())
        slide.delete()
        self.assertNotContains(self.client.get(LANDING), "hero__carrossel")

    def test_extensao_invalida_e_rejeitada(self):
        r = self.client.post("/admin/cardapio/slidecarrossel/add/", {
            "imagem": SimpleUploadedFile("a.gif", b"GIF89a", content_type="image/gif"), "ordem": 0,
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(SlideCarrossel.objects.count(), 0)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ProdutoAdminTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser("adm", "a@a.com", "x")
        self.client.force_login(self.user)

    def _png(self):
        buf = io.BytesIO()
        Image.new("RGB", (10, 10), "red").save(buf, "PNG")
        return SimpleUploadedFile("a.png", buf.getvalue(), content_type="image/png")

    def test_card_usa_imagem_do_produto(self):
        p = Produto.objects.create(nome="C", preco=1, imagem=self._png())
        self.assertContains(self.client.get(LANDING), f'src="{p.imagem.url}"')

    def test_card_sem_imagem_usa_placeholder(self):
        Produto.objects.create(nome="C", preco=1)
        self.assertContains(self.client.get(LANDING), "cookie-card__placeholder-img")

    def test_upload_de_imagem_pelo_admin(self):
        r = self.client.post("/admin/cardapio/produto/add/", {
            "nome": "Z", "descricao": "", "preco": "5", "imagem": self._png(),
            "ofertas-TOTAL_FORMS": 0, "ofertas-INITIAL_FORMS": 0,
            "ofertas-MIN_NUM_FORMS": 0, "ofertas-MAX_NUM_FORMS": 1000,
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Produto.objects.get(nome="Z").imagem)

    def test_lista_tem_acoes_editar_e_excluir_por_linha(self):
        p = Produto.objects.create(nome="L", preco=1)
        r = self.client.get("/admin/cardapio/produto/")
        self.assertContains(r, "Editar")
        self.assertContains(r, "Excluir")
        # as ações redirecionam para as telas padrão do admin
        for nome, destino in (("editar", "change"), ("excluir", "delete")):
            r = self.client.get(f"/admin/cardapio/produto/{p.pk}/{nome}/")
            self.assertRedirects(
                r, f"/admin/cardapio/produto/{p.pk}/{destino}/", fetch_redirect_response=False
            )

    def test_pagina_do_produto_permite_add_e_delete_de_ofertas(self):
        from datetime import timedelta
        from django.utils import timezone

        p = Produto.objects.create(nome="L", preco=1)
        agora = timezone.now()
        Oferta.objects.create(produto=p, percentual=10, inicio=agora, fim=agora + timedelta(days=1))
        r = self.client.get(f"/admin/cardapio/produto/{p.pk}/change/")
        self.assertContains(r, "ofertas-TOTAL_FORMS")
        self.assertContains(r, "DELETE")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ExclusaoDefinitivaTests(TestCase):
    def _png(self):
        buf = io.BytesIO()
        Image.new("RGB", (10, 10), "red").save(buf, "PNG")
        return SimpleUploadedFile("a.png", buf.getvalue(), content_type="image/png")

    def test_slide_e_apagado_de_verdade_com_o_arquivo(self):
        slide = SlideCarrossel.objects.create(imagem=self._png())
        caminho = slide.imagem.path
        import os
        self.assertTrue(os.path.exists(caminho))
        slide.delete()
        self.assertEqual(SlideCarrossel.objects.count(), 0)
        self.assertFalse(os.path.exists(caminho))

    def test_oferta_e_apagada_de_verdade_inclusive_em_queryset(self):
        from datetime import timedelta
        from django.utils import timezone
        p = Produto.objects.create(nome="P", preco=1)
        agora = timezone.now()
        dados = dict(produto=p, percentual=10, inicio=agora, fim=agora + timedelta(days=1))
        Oferta.objects.create(**dados).delete()
        Oferta.objects.create(**dados)
        Oferta.objects.all().delete()
        self.assertEqual(Oferta.objects.count(), 0)

    def test_produto_continua_com_exclusao_logica(self):
        p = Produto.objects.create(nome="P", preco=1)
        p.delete()
        self.assertEqual(Produto.objects.count(), 1)
        self.assertFalse(Produto.objects.get().ativo)


class MascaraPrecoTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser("adm", "a@a.com", "x")
        self.client.force_login(self.user)

    def _post(self, preco):
        return self.client.post("/admin/cardapio/produto/add/", {
            "nome": "M", "descricao": "", "preco": preco,
            "ofertas-TOTAL_FORMS": 0, "ofertas-INITIAL_FORMS": 0,
            "ofertas-MIN_NUM_FORMS": 0, "ofertas-MAX_NUM_FORMS": 1000,
        })

    def test_campo_tem_mascara_e_script(self):
        r = self.client.get("/admin/cardapio/produto/add/")
        self.assertContains(r, 'data-mascara="moeda"')
        self.assertContains(r, "cardapio/js/moeda_mask.js")

    def test_valor_mascarado_e_salvo_corretamente(self):
        for entrada, esperado in (("R$ 1.400,00", "1400.00"), ("R$ 12,50", "12.50"), ("R$ 0,99", "0.99")):
            Produto.objects.all().hard_delete()
            self.assertEqual(self._post(entrada).status_code, 302, entrada)
            self.assertEqual(str(Produto.objects.get().preco), esperado)

    def test_valor_invalido_e_zero_sao_rejeitados(self):
        for entrada in ("abc", "R$ 0,00"):
            self.assertEqual(self._post(entrada).status_code, 200, entrada)
        self.assertEqual(Produto.objects.count(), 0)

    def test_edicao_mostra_valor_formatado(self):
        p = Produto.objects.create(nome="E", preco=1400)
        r = self.client.get(f"/admin/cardapio/produto/{p.pk}/change/")
        self.assertContains(r, "R$ 1.400,00")
