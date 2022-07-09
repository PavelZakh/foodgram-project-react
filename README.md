![example workflow](https://github.com/PavelZakh/foodgram-project-react/actions/workflows/foodgram_workflow.yml/badge.svg)

## Проект Foodgram

Foodgram - продуктовый помощник. С помощью этого веб-сервиса вы сможете составлять свои рецепты, смотреть рецепты других авторов, подписываться на них, а так же составлять свою корзину покупок и скачивать её. Для этого необходимо зарегестрироваться на сервере.

Развернутый проект доступен по ссылке http://51.250.18.217/

### Как развернуть проект локально:

Для начала необходимо установить Docker.
```
https://docs.docker.com/engine/install/
```
Клонировать репозиторий и перейти в него в командной строке:
```
git clone https://github.com/PavelZakh/foodgram-project-react.git
```
Перейти в папку infra
```
cd infra
```
Выполнить команду по запуску контейнеров
```
docker compose up --build
```
Готово! Теперь у вас запущен проект!

Теперь вы можете обращаться по этому адресу и взаимодействовать с помощником:
```
http://localhost/
```

### Как развернуть проект на удаленном сервере:

1) Локально склонировать проект
```
git clone https://github.com/PavelZakh/foodgram-project-react.git
```
2) Выполнить вход на удаленный сервер по вашему ssh
3) Установить docker, а так же docker-compose:
```
https://docs.docker.com/engine/install/
```
4) Отредактировать файл infra/nginx.conf, в строке server_name впишите IP вашего сервера
5) Скопировать файлы nginx.conf и docker-compose.yml на сервер
```
scp docker-compose.yml <username>@<host>:/home/<username>/docker-compose.yml
scp nginx.conf <username>@<host>:/home/<username>/nginx.conf
```
6) Создать файл .env и вписать следующие значения:
```
DB_ENGINE=django.db.backends.postgresql
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=<пароль>
DB_HOST=db
DB_PORT=5432
SECRET_KEY=<секретный ключ проекта django>
```
7) Соберите контейнеры с помощью docker-compose:
```
sudo docker-compose up -d --build
```
8) После этого один раз необходимо применить миграции:
```
sudo docker-compose exec backend python manage.py migrate --noinput
```
9) Сделать сбор статических файлов:
```
sudo docker-compose exec backend python manage.py collectstatic --noinput
```
10) Загрузите ингредиенты в базу данных:
```
sudo docker-compose exec backend python manage.py load_data ingredients.json
```
11) Готово! Проект запущен на вашем сервере. Можете обращаться к нему по вашему IP

### Об авторе

Захаров Павел Валерьевич 

Студент Яндекс.Практикума по python backend разработке

Telegram - @zkhrv_pash