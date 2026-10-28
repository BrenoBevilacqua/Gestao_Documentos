#!/bin/sh
set -e

echo ">> Aplicando migrações..."
python manage.py migrate --noinput

# Cria um superusuário automaticamente se as variáveis forem informadas
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py createsuperuser --noinput \
    --username "$DJANGO_SUPERUSER_USERNAME" \
    --email "${DJANGO_SUPERUSER_EMAIL:-admin@example.com}" 2>/dev/null || true
fi

# Importa os dados da planilha na primeira execução, se solicitado
if [ "$IMPORTAR_PLANILHA" = "1" ]; then
  python manage.py importar_planilha || true
fi

exec "$@"
