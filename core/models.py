from django.conf import settings
from django.db import models
from django.utils import timezone

from .current_user import get_current_user


class CoreQuerySet(models.QuerySet):
    def ativos(self):
        return self.filter(ativo=True)

    def delete(self):
        """Exclusão lógica (marca como inativo), salvo se o modelo desativar isso."""
        if not self.model.exclusao_logica:
            return super().delete()
        return self.update(
            ativo=False,
            atualizado_em=timezone.now(),
            atualizado_por=get_current_user(),
        )

    def hard_delete(self):
        return super().delete()


class CoreModel(models.Model):
    """Modelo abstrato base com campos de auditoria. Todos os modelos herdam dele."""

    criado_em = models.DateTimeField("criado em", auto_now_add=True, editable=False)
    atualizado_em = models.DateTimeField("atualizado em", auto_now=True, editable=False)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="criado por",
        null=True,
        blank=True,
        editable=False,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="atualizado por",
        null=True,
        blank=True,
        editable=False,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    ativo = models.BooleanField("ativo", default=True)

    objects = CoreQuerySet.as_manager()

    # True: delete() só inativa o registro. Modelos que podem ser apagados de
    # verdade definem `exclusao_logica = False`.
    exclusao_logica = True

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        user = get_current_user()
        if user is not None:
            if self._state.adding and self.criado_por_id is None:
                self.criado_por = user
            self.atualizado_por = user
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = {*update_fields, "atualizado_por", "criado_por"}
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        """Exclusão lógica: o registro fica inativo e deixa de ser exibido."""
        if not self.exclusao_logica:
            return super().delete(using=using, keep_parents=keep_parents)
        self.ativo = False
        self.save(update_fields=["ativo", "atualizado_em"])

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)
