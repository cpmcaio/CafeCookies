from unfold.admin import ModelAdmin, TabularInline


class CoreModelAdmin(ModelAdmin):
    """Admin base para modelos que herdam de CoreModel.

    No cadastro (add) os campos de auditoria e `ativo` não aparecem: são
    preenchidos automaticamente. Na edição, a auditoria aparece somente leitura
    e `ativo` pode ser editado (para reativar registros excluídos).
    """

    audit_fields = ("criado_em", "criado_por", "atualizado_em", "atualizado_por")

    def get_readonly_fields(self, request, obj=None):
        readonly = tuple(super().get_readonly_fields(request, obj))
        return readonly + self.audit_fields if obj else readonly

    def get_fields(self, request, obj=None):
        fields = list(super().get_fields(request, obj))
        if obj is None:
            hidden = {*self.audit_fields, "ativo"}
            fields = [f for f in fields if f not in hidden]
        return fields


class CoreTabularInline(TabularInline):
    """Inline base: nunca exibe os campos do CoreModel (defina `fields` sem eles)."""
