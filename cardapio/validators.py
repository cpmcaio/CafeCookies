from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

TAMANHO_MAXIMO_IMAGEM = 3 * 1024 * 1024  # 3 MB


def validar_imagem(imagem):
    if imagem.size > TAMANHO_MAXIMO_IMAGEM:
        raise ValidationError("A imagem deve ter no máximo 3 MB.")


# validadores de todo campo de imagem enviado pelo admin
VALIDADORES_IMAGEM = [FileExtensionValidator(["jpg", "jpeg", "png", "webp"]), validar_imagem]
