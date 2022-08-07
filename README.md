# xi.backend

## Работа над проектом
1. Скачать репозиторий (через `git clone` или PyCharm)
2. Перейти в место, куда склонирован репозиторий
3. Инициализировать субмодули (`git submodule init` и `git submodule update`)
4. Временно сменить ветку на `prod`, далее см. [Раздел про GIT](#GIT)
5. Настроить виртуальное окружение или глобальный интерпретатор python. Используется [**3.9.7**](https://www.python.org/downloads/release/python-397/) ради совместимости с хостингом
6. Установить все библиотеки через `pip install -r requirements.txt`

### Для PyCharm
1. Пометить папку `xieffect` как *Sources Root*
2. Пометить папку `templates` как *Excluded*, чтобы форматер на него не ругался
3. Открыть `xieffect/wsgi.py` и запустить его. Возможно, придётся поменять working directory на `path/to/project/xieffect`
4. Проверить доступность http://localhost:5000/doc/ и остановить сервер
5. Создать конфигурацию `pytest` для папки `xieffect`. Также поменять working directory на `path/to/project/xieffect`. Проверить, что всё работает (запустить тесты и дождаться успешного завершения)


### GIT
1. Никогда не работать в ветках `master` или `prod`
2. Создавать ответвления (feature-branches) от `prod` для работы над проектом
3. По окончании работы над фичей, отправлять PR из своей *feature-branch* в `prod`
4. В PR нужно отмечать issues, над которыми работали и призывать кого-то на review
5. Если во время работы над фичей произошло обновление в `prod`, необходимо обновить собственную ветку до PR!

## Полезная информация
- [ссылки по используемым библиотекам](https://gist.github.com/niqzart/e79643045bcc135aa05def3534ad2338)
- [информационные PRы](https://github.com/xi-effect/xieffect-backend/issues?q=label%3Ainfo-pr)
