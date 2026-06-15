#!/bin/sh
set -eu

if [ "${DEBUG:-False}" != "True" ] && [ "${POSTGRES_PASSWORD:-opencirt}" = "opencirt" ]; then
    echo "ERROR: POSTGRES_PASSWORD is still the default 'opencirt'." >&2
    echo "       Set a strong password in your .env file before starting in production." >&2
    exit 1
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
