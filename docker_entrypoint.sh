#!/bin/bash

cat <<EOT > /www/project/settings_prod.py
import os

os.environ['DJANGO_DEBUG'] = 'False'
os.environ['DATABASE_URL'] = 'mysql://root:${MYSQL_ENV_MYSQL_ROOT_PASSWORD}@${MYSQL_PORT_3306_TCP_ADDR}:${MYSQL_PORT_3306_TCP_PORT}/${MYSQL_ENV_MYSQL_DATABASE}'
os.environ['DJANGO_ALLOWED_HOST'] = '$DJANGO_ALLOWED_HOST'
os.environ['DJANGO_SECRET_KEY'] = '$DJANGO_SECRET_KEY'

from project.settings import *
EOT

cd /www
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=project.settings_prod
python manage.py check --deploy
python manage.py migrate
python manage.py collectstatic --no-input
deactivate

exec "$@"
