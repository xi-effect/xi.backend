from flask_restx.reqparse import RequestParser

counter_parser: RequestParser = RequestParser()
counter_parser.add_argument("counter", type=int, required=True, help="The number of the request for pagination")

password_parser: RequestParser = RequestParser()
password_parser.add_argument("password", required=True, help="User's password")
