# teslarent

# Setup

## Docker
```bash
docker build -t teslarent .
docker run -d -p 444:443 --link mysql-teslarent:mysql -e DJANGO_ALLOWED_HOST='*' -e DJANGO_SECRET_KEY=$DJANGO_SECRET_KEY --name teslarent teslarent
```

## Production deployment

### Environment variables
- make sure DJANGO_DEBUG is NOT set to True
- DATABASE_URL=postgres db config, e.g. postgres://postgres:password@192.168.100.100:5432/dbname
- DJANGO_ALLOWED_HOST=your_domain
- DJANGO_SECRET_KEY=random 50 symbol string
- these variables cannot be set in apache with SetEnv, either set them
 as global environment variables or define them in `./project/settings_prod.py`

### Generic Setup

#### Requirements
- Python (tested with version 3.5, others should be fine too)
- Pip
- Postgres or MySQL database
- Https Web Server with wsgi support, e.g. Apache with mod_wsgi (https://docs.djangoproject.com/en/1.10/howto/deployment/wsgi/modwsgi/)

  see apache2_wsgi_sample.conf, adjust python_app_dir and ssl certificates

#### Setup
```bash
git clone https://github.com/flarno11/teslarent.git
cd teslarent
git checkout release
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp project/settings_prod_sample.py project/settings_prod.py
```

make sure config variables are set correctly before continuing, either in `project/settings_prod.py` or via global environment variables
```bash
export DJANGO_SETTINGS_MODULE=project.settings_prod
python manage.py check --deploy
python manage.py migrate
python manage.py collectstatic --no-input

python manage.py createsuperuser
```

#### Upgrade
```
cd teslarent
git pull
export DJANGO_SETTINGS_MODULE=project.settings_prod
python manage.py migrate
python manage.py collectstatic --no-input
service httpd reload
```

### Setup using Heroku (heroku.com)
1. Create new app with automatic deployment from this github repo, choose the `release` branch
2. `heroku run --app your_heroku_app_name python manage.py check --deploy`
2. `heroku run --app your_heroku_app_name python manage.py migrate`
3. `heroku run --app your_heroku_app_name python manage.py createsuperuser`
4. Open https://your_domain/manage/ and login

