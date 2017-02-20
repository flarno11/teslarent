# teslarent

## Production deployment
### Environment variables
- make sure DJANGO_DEBUG is NOT set to True
- DATABASE_URL=postgres db config, e.g. postgres://postgres:password@192.168.100.100:5432/teslarent
- DJANGO_ALLOWED_HOST=your_domain
- DJANGO_SECRET_KEY=random 50 symbol string

### Setup using Heroku
1. Create new app with automatic deployment from this github repo, choose the `release` branch
2. `heroku run --app your_heroku_app_name python manage.py check --deploy`
2. `heroku run --app your_heroku_app_name python manage.py migrate`
3. `heroku run --app your_heroku_app_name python manage.py createsuperuser`
4. Open https://your_domain/manage/ and login
