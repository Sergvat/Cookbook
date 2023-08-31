## Продуктовый помощник - Foodgram.

## Описание

Данный проект представляет собой веб-приложение для публикации и обмена рецептами, с возможностью подписываться на публикации других пользователей, добавлять понравившиеся рецепты в список избранного, а также для создания списков покупок, связанных с этими рецептами, который можно скачать.

## Функциональность проекта:

1.  Регистрация и авторизация пользователей: Пользователи могут зарегистрироваться, создавать учетные записи и авторизовываться для доступа ко всей функциональности.
2.  Публикация рецептов: Пользователи могут публиковать свои рецепты с подробными инструкциями и фотографиями.
3.  Добавление рецептов в избранное: Пользователи могут добавлять рецепты других авторов в свой список избранных.
4.  Подписка на авторов: Пользователи могут подписываться на других авторов.
5.  Список покупок: Пользователи могут добавлять списки продуктов, необходимых для приготовления выбранных блюд и скачивать их.

## Стек технологий:

- Python
- Django
- DjangoRestFramework
- PostgresSQL
- Nginx
- Gunicorn
- Docker, Docker-compose, DockerHub (CI/CD)

## Запуск проекта:

Чтобы запустить проект, выполните следующие шаги:

1.  Клонируйте репозиторий с GitHub и перейдите в папку проекта в командной строке:

```
git clone git@github.com:Sergvat/foodgram-project-react.git
cd foodgram-project-react
```

2. Cоздайте и открыть файл `.env` с переменным окружением для хранения ключей:

```
cd infra
touch .env
```

3. Заполните файл `.env` :

```
DEBUG=True
SECRET_KEY=super-key
DB_ENGINE=django.db.backends.postgresql
DB_NAME=db.sqlite3
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432
```

4.  Сборка и запуск приложения в контейнерах:

```
docker compose -f docker-compose.production.yml up -d --build
```

5.  Выполните миграции, соберите статику, cоздайте суперпользователя и загрузите ингредиенты в БД:

```
docker-compose exec backend python manage.py makemigrations
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py collectstatic --no-input
docker-compose exec backend python manage.py createsuperuser
docker-compose exec backend python manage.py import_ingredients
```
