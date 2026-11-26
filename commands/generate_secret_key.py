from django.core.management.utils import get_random_secret_key
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

key = get_random_secret_key()

if ENV_FILE.exists():
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    new_lines = []
    replaced = False
    for line in lines:
        if line.startswith("SECRET_KEY="):
            new_lines.append(f"SECRET_KEY={key}")
            replaced = True
        else:
            new_lines.append(line)
    if not replaced:
        new_lines.append(f"SECRET_KEY={key}")
    ENV_FILE.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    print(f"SECRET_KEY atualizada no .env")
else:
    print(f"SECRET_KEY={key}")
    print("\nArquivo .env não encontrado. Copie a linha acima para o seu .env.")
