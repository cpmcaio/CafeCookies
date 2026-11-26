from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html

from unfold.decorators import action
from unfold.enums import ActionVariant

from core.admin import CoreModelAdmin, CoreTabularInline

from .forms import ProdutoForm
from .models import Oferta, Produto, SlideCarrossel


class OfertaInline(CoreTabularInline):
    model = Oferta
    extra = 0
    fields = ("percentual", "rotulo", "inicio", "fim")


@admin.register(Produto)
class ProdutoAdmin(CoreModelAdmin):
    form = ProdutoForm
    list_display = ("miniatura", "nome", "preco", "destaque", "ativo", "atualizado_em")
    list_display_links = ("nome",)
    list_filter = ("destaque", "ativo")
    search_fields = ("nome",)

    @admin.display(description="imagem")
    def miniatura(self, obj):
        if not obj.imagem:
            return "—"
        return format_html(
            '<img src="{}" style="height:48px;width:48px;border-radius:6px;object-fit:cover">', obj.imagem.url
        )
    inlines = [OfertaInline]
    actions_row = ["editar", "excluir"]

    @action(description="Editar", url_path="editar", icon="edit")
    def editar(self, request, object_id):
        return redirect(reverse("admin:cardapio_produto_change", args=[object_id]))

    @action(description="Excluir", url_path="excluir", icon="delete", variant=ActionVariant.DANGER)
    def excluir(self, request, object_id):
        return redirect(reverse("admin:cardapio_produto_delete", args=[object_id]))


@admin.register(Oferta)
class OfertaAdmin(CoreModelAdmin):
    list_display = ("produto", "rotulo_exibicao", "percentual", "inicio", "fim", "ativo")
    list_filter = ("ativo",)


@admin.register(SlideCarrossel)
class SlideCarrosselAdmin(CoreModelAdmin):
    list_display = ("miniatura", "ordem", "ativo")
    list_editable = ("ordem",)
    list_filter = ("ativo",)

    @admin.display(description="imagem")
    def miniatura(self, obj):
        if not obj.imagem:
            return "—"
        return format_html(
            '<img src="{}" style="height:48px;border-radius:6px;object-fit:cover">', obj.imagem.url
        )
