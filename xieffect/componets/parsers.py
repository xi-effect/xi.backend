from flask_restx.reqparse import RequestParser

counter_parser: RequestParser = RequestParser()
counter_parser.add_argument("counter", type=int, required=False, help="The page number for pagination")
counter_parser.add_argument("offset", type=int, required=False, help="The starting entity index")

password_parser: RequestParser = RequestParser()
password_parser.add_argument("password", required=True, help="User's password")
