# xi.backend

## Начало работы
1. Скачать репозиторий (через `git clone` или PyCharm)
2. Перейти в папку, куда склонирован репозиторий
3. Инициализировать субмодули (`git submodule init` и `git submodule update`)
4. Временно сменить ветку на `prod`, далее см. [Раздел про командную работу](#Командная-работа)
5. Настроить виртуальное окружение или глобальный интерпретатор python. Используется [**python 3.11**](https://www.python.org/downloads/release/python-311/)
6. Установить все библиотеки через `pip install -r requirements.txt`
7. Ознакомиться с [инфой по линтерам](https://github.com/xi-effect/xieffect-backend/pull/133)
8. Включить гит-хуки: `pre-commit install`

### Для PyCharm
1. Пометить папку `xieffect` как *Sources Root*
2. Пометить папку `xieffect/test` как *Test Sources Root*
3. Стоит в меню "commit" нажать на шестерёнку под полем ввода и включить:
    - Reformat Code
    - Analyze Code
4. Несколько инструкций добавлено с [линтерами](https://github.com/xi-effect/xieffect-backend/pull/133)

### Первичный запуск проекта
1. Перейти в папку `xieffect`
2. Запустить `wsgi.py` (через команду `python wsgi.py` или через одноимённую run-конфигурацию)
3. Проверить доступность http://localhost:5000/doc/ и остановить сервер
4. В папке `xieffect` запустить `pytest` (через консоль одноимённой командой или через run-конфигурацию)
5. Дождаться успешного завершения тестов

## Командная работа
1. Никогда не работать в ветках `master` или `prod`
2. Создавать ответвления (feature-branches) от `prod` для работы над проектом
3. По окончании работы над фичей, отправлять PR из своей *feature-branch* в `prod`
4. В PR нужно призывать кого-то на review (обычно reviewer определяется при взятии таски)
5. Если во время работы над фичей произошло обновление в `prod`, необходимо ребейснуть собственную ветку на `prod` (важно уметь это делать — лучше спросить, чем сломать git)
6. За merge PR-а отвечает лид или старший разработчик (в будущем...)
7. При чекауте иногда нужно прогонять `git submodule update` и переустанавливать зависимости

### Полная переустановка зависимостей
```sh
# с активированным venv или через `python -m`
pip freeze > tmp
pip uninstall -y -r tmp
rm tmp
pip install -r requirements.txt
```

## Окружение
TBA

## Полезная информация
- [ссылки по используемым библиотекам](https://gist.github.com/niqzart/e79643045bcc135aa05def3534ad2338)
- [информационные PRы](https://github.com/xi-effect/xieffect-backend/issues?q=label%3Ainfo-pr)
