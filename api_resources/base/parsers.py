from flask_restful.reqparse import RequestParser

counter_parser: RequestParser = RequestParser()
counter_parser.add_argument("counter", type=int, required=True)

password_parser: RequestParser = RequestParser()
password_parser.add_argument("password", required=True)
