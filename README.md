# FOODGRAM
## _социальная сеть рецептов_


#### Локальное подключение
- Сделать форк на свою учетную запись на GitHub
- Клонировать репозиторий
```sh
git clone git@github.com:SergeiVasilchenko/foodgram-project-react.git
```
- Установить виртуальное окружение
- Активировать виртуальное окружение
- Установить зависимости
```sh
pip install -r requirements.txt
```
Внимание! На локальной машине применяется база данных SQLite, для удаленного сервера работает PostgreSQL. Для работы   локально поменяйте в файле ```settings.py``` переменную
```sh
DEBUG = True
```
- Выполнить миграции данных
```sh
python manage.py migrate
```
Внимание! Для работы сервиса подготовлен файл с ингредиентами которые подгружаются в базу данных командой
```sh
python manage.py loadingredients
```
- Создать пользователя с правами администратора
```sh
python manage.py createsuperuser
```
_После запуска этой команды ведите требуемые данные  регистрации. В дальнейшем уже зарегистрированный пользователь логинится через адрес эл. почты и пароль._

_Для навигации по эндпойнтам сервиса используйте файл документации_ ```redoc.html```
- Выполнить команды
```sh
cd infra && docker-compose up
```
Проект запустится по адресу
http://localhost
увидеть спецификацию API вы сможете по адресу
http://localhost/api/docs/

### Установить на удаленный сервер
_Технология автоматического продакшена на удаленный сервер предполагает пользование переменными окружения, которые необходимы для аутентификации и полноценного пользования сервисом в роли владельца. Для этого необходимо выполнить следующие операции._
- Установить на локальную машину и на удаленный сервер Docker
- Создать в корневой папке проекта файл `.env`
- Определить в файле следующие переменные со значениями, например:
```sh
POSTGRES_DB=db
POSTGRES_USER=foodgram_user
POSTGRES_PASSWORD=foodgram_password
DB_HOST=db
DB_PORT=5432
DB_NAME=db
SERCRET_KEY='django-insecure-bn7sz7p+1eib1rb2%dn6awm6j0t2u_4ccgm+vvbl0j03%nhxk%'
```
- В скопированном репозитории в разделе Settings в левом поле найти Раздел Security и подменю Secrets and Variables, нажать actions. Помимо выше перечисленных переменных и их значений добавить следующие переменные и их значения
```sh
DOCKER_USERNAME=<your personal docker username>
DOCKER_PASSWORD=<your personal docker password>
HOST=<your remote server host IP address>
USER=<your remote server username>
SSH_PASSPHRASE=<…>
SSH_KEY=<your OpenSSH key for remote server authorization>
TELEGRAM_TO=<your telegram account id>
TELEGRAM_TOKEN=<your telegram token>
```
- в файле `settings.py` в переменной `ALLOWED_HOSTS` заменить ip адрес удаленого сервера на ip адрес вашего удаленного сервера.
- из корневой папки выполнить поочередно
```sh
git add .
git commit -m ‘<some message>’
git push
```
Далее в автоматическом режиме выполнится следующая процедура:
> После пуша (триггер) проекта на репозиторий github в репозитории запустится файл `main.yml`
Выполнятся тесты flake8 проверщика по правилам PEP8
На вашем удаленном сервере в корневой папке будет создана папка foodgram
Будут скопированы файлы `docker-compose.yml` и `nginx.conf`
На основе Dockerfile папки backend будет собран образ foodgram-backend и запушен на репозиторий вашего DockerHub На основе Dockerfile папки frontend будет собран образ foodgram-frontend и запушен на репозиторий вашего DockerHub
Также будут собраны контейнер базы данных и контейнер nginx сервера.
После успешного деплоя на удаленный сервер проект будет доступен для работы.

Учетные данные администратора
8045274@gmail.com
пароль
DR%5t1212
