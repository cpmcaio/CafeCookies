#!/usr/bin/env bash
# Build do Render: instala dependências, coleta estáticos e aplica migrações.
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput

# Cria o superusuário na primeira vez (o plano gratuito do Render não tem shell).
# Defina DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL e DJANGO_SUPERUSER_PASSWORD.
if [[ -n "${DJANGO_SUPERUSER_USERNAME:-}" && -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]]; then
    python manage.py createsuperuser --noinput || echo "Superusuário já existe."
fi
