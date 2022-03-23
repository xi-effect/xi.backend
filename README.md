# Xi-Effect-Backend

## Работа над проектом
1. Скачать репозиторий (через `git clone` или PyCharm)
2. Инициализировать субмодули (`git submodule init` и `git submodule update`)
3. Временно сменить ветку на `prod`, далее см. [Раздел про GIT](#GIT)
4. Настроить виртуальное окружение или глобальный интерпретатор python. Используется [**3.9.7**](https://www.python.org/downloads/release/python-397/) ради совместимости с хостингом
5. Установить все библиотеки через `pip install -r requirements.txt`

### Для PyCharm
1. Пометить папки `xieffect`, `xieffect-socketio` и `blueprints` как *Sources Root*
2. Открыть `xieffect/wsgi.py` и запустить его. Возможно, придётся поменять working directory на `path/to/project/xieffect`
3. Проверить доступность http://localhost:5000/doc/
4. Открыть `xieffect-socketio/main.py` и запустить его. Возможно, придётся поменять working directory на `path/to/project/xieffect-socketio`
5. Проверить доступность http://localhost:5050/ и работоспособность отправки сообщений (введённое сообщение должно выводится на экране чуть ниже поля ввода) 
6. Затем оба сервера можно останавливать
7. Создать конфигурацию `pytest` для папки `xieffect`. Также поменять working directory на `path/to/project/xieffect`. Проверить, что всё работает (запустить тесты и дождаться успешного завершения)


### GIT
1. Никогда не работать в ветках `master` или `prod`
2. Создавать ответвления (feature-branches) от `prod` для работы над проектом
3. По окончании работы над фичей, отправлять PR из своей *feature-branch* в `prod`
4. В PR нужно отмечать issues, над которыми работали и призывать кого-то на review
5. Если во время работы над фичей произошло обновление в `prod`, необходимо обновить собственную ветку до PR!

### Heroku
1. Установить [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli#download-and-install)
2. Залогиниться: `heroku login`
3. Открыть терминал в папке проекта
4. Добавить remote: `heroku git:remote -a xieffect-socketio`
5. Пушить только тщательной проверки локально, при обновлениях в `xieffect-socketio`, после всех коммитов. Команда: `git push -f heroku feat/socketio-integration:master`
