import io
import os

from django.core.files.base import ContentFile
from PIL import Image, ImageOps


def reduzir_imagem(campo, max_lado):
    """Reduz (em memória) uma imagem recém-enviada para no máximo `max_lado` px.

    Mantém o formato original e corrige a orientação do EXIF. Se a imagem já for
    pequena, não faz nada.
    """
    campo.file.seek(0)
    img = Image.open(campo.file)
    formato = img.format or "PNG"
    img = ImageOps.exif_transpose(img)
    if max(img.size) <= max_lado:
        campo.file.seek(0)
        return
    img.thumbnail((max_lado, max_lado), Image.LANCZOS)
    buf = io.BytesIO()
    opcoes = {"optimize": True}
    if formato in ("JPEG", "WEBP"):
        opcoes["quality"] = 85
    if formato == "JPEG" and img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    img.save(buf, format=formato, **opcoes)
    campo.save(os.path.basename(campo.name), ContentFile(buf.getvalue()), save=False)
