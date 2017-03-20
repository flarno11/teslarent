# teslarent

# Setup

Choose between Docker, Generic Setup and Heroku

## Docker
```bash
docker build -t teslarent .
docker run -d -p 444:443 --link mysql-teslarent:mysql -e DJANGO_ALLOWED_HOST='*' -e DJANGO_SECRET_KEY=$DJANGO_SECRET_KEY --name teslarent teslarent
```

## Production deployment

### Environment variables
- DATABASE_URL=postgres/mysql db config, e.g. postgres://postgres:password@192.168.100.100:5432/dbname
- DJANGO_ALLOWED_HOST=your_domain
- DJANGO_SECRET_KEY=random 50 symbol string
- these variables cannot be set in Apache with SetEnv, either set them
 as global environment variables or define them in `./project/settings_prod.py`
- make sure DJANGO_DEBUG is NOT set to True

### Generic Setup

#### Requirements
- Python (tested with version 3.5, others should be fine too)
 - virtualenv, e.g. python3-venv
- Postgres or MySQL database
- Https Web Server with wsgi support, e.g. Apache with mod_wsgi
  (https://docs.djangoproject.com/en/1.10/howto/deployment/wsgi/modwsgi/),
  see [apache2_wsgi_sample.conf](https://github.com/flarno11/teslarent/blob/master/apache2_wsgi_sample.conf), adjust python_app_dir and ssl certificates

#### Setup
- Fetch source code and install requirements
```bash
git clone https://github.com/flarno11/teslarent.git
cd teslarent
git checkout release
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp project/settings_prod_sample.py project/settings_prod.py
```

- Make sure config variables are set correctly before continuing,
 either in `project/settings_prod.py` or via global environment variables
- Run checks and initialize database
```bash
export DJANGO_SETTINGS_MODULE=project.settings_prod
python manage.py check --deploy
python manage.py migrate
python manage.py collectstatic --no-input
```

- Create admin user
```bash
python manage.py createsuperuser
```
and follow the instructions

- Open https://your_domain/manage/ in your browser and login


#### Upgrade
- Fetch updated source code and install new requirements if necessary
```bash
cd teslarent
git pull
source venv/bin/activate
pip install -r requirements.txt
export DJANGO_SETTINGS_MODULE=project.settings_prod
python manage.py migrate
python manage.py collectstatic --no-input
```
- Reload web server, e.g. with `service httpd reload`

### Setup using Heroku (heroku.com)
- Create new app
 - Go to Resources, add Postgres database
 - Enable automatic deployment from this github repo, choose the `release` branch
- From the command line
 - `export APP_NAME=your_heroku_app_name
 - `heroku config:set --app $APP_NAME DJANGO_SETTINGS_MODULE=project.settings`
   - do the same for DJANGO_ALLOWED_HOST and DJANGO_SECRET_KEY
 - Verify config with `heroku config --app $APP_NAME`
 - `heroku run --app $APP_NAME python manage.py check --deploy`
 - `heroku run --app $APP_NAME python manage.py migrate`
 - `heroku run --app $APP_NAME python manage.py createsuperuser`
- Open https://your_domain/manage/ in your browser and login
