from typing import Union

from flask import request, send_from_directory, redirect
from flask_restx import Resource, marshal
from flask_restx.reqparse import RequestParser

from common import Namespace, ResponseDoc, User, counter_parser


# TODO /modules/<module_id>/results/ -> пагинация, минимальная информация
# TODO использовать user из авторизации

# TODO /modules/<module_id>/results/<result_id>/ -> GET & DELETE
