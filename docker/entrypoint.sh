#!/bin/sh
set -eu

if [ "${DEBUG:-False}" != "True" ] && [ "${DATABASE_PASSWORD:-opencirt}" = "opencirt" ]; then
    echo "ERROR: DATABASE_PASSWORD is still the default 'opencirt'." >&2
    echo "       Set POSTGRES_PASSWORD to a strong value in your .env file." >&2
    exit 1
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
