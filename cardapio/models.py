from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Prefetch
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.utils.functional import cached_property

from core.models import CoreModel, CoreQuerySet

from .imagens import reduzir_imagem
from .validators import VALIDADORES_IMAGEM


class ModeloComImagem(CoreModel):
    """Base para modelos com um campo `imagem`.

    - reduz a imagem enviada ao tamanho máximo `IMAGEM_MAX_LADO`;
    - apaga do disco o arquivo antigo quando a imagem é trocada ou removida.
    """

    IMAGEM_MAX_LADO = 1200

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        campo = self.imagem
        if campo and not campo._committed:
            reduzir_imagem(campo, self.IMAGEM_MAX_LADO)

        update_fields = kwargs.get("update_fields")
        grava_imagem = update_fields is None or "imagem" in update_fields
        antigo = None
        if self.pk and grava_imagem:
            antigo = type(self)._base_manager.filter(pk=self.pk).values_list("imagem", flat=True).first()

        super().save(*args, **kwargs)

        if antigo and antigo != self.imagem.name:
            self.imagem.storage.delete(antigo)


class OfertaQuerySet(CoreQuerySet):
    def vigentes(self):
        """Ofertas ativas cujo período inclui o momento atual."""
        agora = timezone.now()
        return self.ativos().filter(inicio__lte=agora, fim__gte=agora)


class ProdutoQuerySet(CoreQuerySet):
    def para_cardapio(self):
        """Produtos ativos já com as ofertas vigentes carregadas (evita N+1)."""
        return self.ativos().prefetch_related(
            Prefetch("ofertas", queryset=Oferta.objects.vigentes())
        )


class Produto(ModeloComImagem):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    preco = models.DecimalField(max_digits=7, decimal_places=2)
    destaque = models.BooleanField(default=False)
    imagem = models.ImageField(
        upload_to="produtos/",
        blank=True,
        validators=VALIDADORES_IMAGEM,
        help_text="Foto do card. JPG, PNG ou WebP, até 3 MB. Se vazio, usa uma imagem padrão.",
    )

    objects = ProdutoQuerySet.as_manager()

    class Meta:
        ordering = ["-destaque", "nome"]
        constraints = [
            models.CheckConstraint(condition=models.Q(preco__gt=0), name="produto_preco_positivo"),
        ]

    def __str__(self):
        return self.nome

    @cached_property
    def oferta_vigente(self):
        """Maior oferta em vigor agora. Usa as ofertas pré-carregadas, se houver."""
        agora = timezone.now()
        vigentes = [
            o for o in self.ofertas.all()
            if o.ativo and o.inicio <= agora <= o.fim
        ]
        return max(vigentes, key=lambda o: o.percentual, default=None)

    @property
    def preco_final(self):
        oferta = self.oferta_vigente
        return oferta.aplicar(self.preco) if oferta else self.preco


class Oferta(CoreModel):
    exclusao_logica = False  # pode ser apagada de verdade

    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name="ofertas")
    percentual = models.DecimalField(
        "desconto (%)", max_digits=5, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01")), MaxValueValidator(Decimal("100"))],
    )
    rotulo = models.CharField(
        "rótulo", max_length=40, blank=True,
        help_text="Texto do selo. Se vazio, usa '<percentual>% OFF'.",
    )
    inicio = models.DateTimeField("início")
    fim = models.DateTimeField()

    objects = OfertaQuerySet.as_manager()

    class Meta:
        ordering = ["-inicio"]
        constraints = [
            models.CheckConstraint(condition=models.Q(fim__gt=models.F("inicio")), name="oferta_fim_apos_inicio"),
            models.CheckConstraint(
                condition=models.Q(percentual__gt=0, percentual__lte=100), name="oferta_percentual_valido"
            ),
        ]

    def __str__(self):
        return f"{self.produto} — {self.rotulo_exibicao}"

    @property
    def rotulo_exibicao(self):
        return self.rotulo or f"{self.percentual.normalize():f}% OFF"

    def aplicar(self, preco):
        return (preco * (Decimal("100") - self.percentual) / Decimal("100")).quantize(Decimal("0.01"))

    def clean(self):
        if self.inicio and self.fim and self.fim <= self.inicio:
            raise ValidationError({"fim": "O fim deve ser posterior ao início."})


class SlideCarrossel(ModeloComImagem):
    exclusao_logica = False  # pode ser apagado de verdade
    IMAGEM_MAX_LADO = 1920

    imagem = models.ImageField(
        upload_to="carrossel/",
        validators=VALIDADORES_IMAGEM,
        help_text="JPG, PNG ou WebP, até 3 MB. Recomendado: horizontal, 1920x1080.",
    )
    ordem = models.PositiveIntegerField(default=0, help_text="Menor número aparece primeiro.")

    class Meta:
        ordering = ["ordem", "id"]
        verbose_name = "slide do carrossel"
        verbose_name_plural = "slides do carrossel"

    def __str__(self):
        return f"Slide {self.ordem}"


@receiver(post_delete, sender=Produto)
@receiver(post_delete, sender=SlideCarrossel)
def apagar_arquivo_da_imagem(sender, instance, **kwargs):
    """Remove o arquivo de imagem do disco quando o registro é excluído de vez."""
    if instance.imagem:
        instance.imagem.delete(save=False)
