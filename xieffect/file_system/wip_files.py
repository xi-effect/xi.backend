from os import remove

from flask import request, send_from_directory
from flask_restful import Resource

from authorship import Author
from componets.checkers import jwt_authorizer
from users import User


class ImageAdder(Resource):  # POST /wip/images/
    @jwt_authorizer(Author, "author", use_session=False)
    def post(self, author: Author):
        author_id: int = author.id
        image_id: int = author.get_next_image_id()
        with open(f"files/images/{author_id}-{image_id}.png", "wb") as f:
            f.write(request.data)
        return {"aid": author_id, "iid": image_id}


class ImageProcessor(Resource):  # [PUT|DELETE] /wip/images/<int:image_id>/
    @jwt_authorizer(Author, "author", use_session=False)
    def put(self, author: Author, image_id: int):
        with open(f"files/images/{author.id}-{image_id}.png", "wb") as f:
            f.write(request.data)
        return {"a": True}

    @jwt_authorizer(Author, "author", use_session=False)
    def delete(self, author: Author, image_id: int):
        remove(f"files/images/{author.id}-{image_id}.png")
        return {"a": True}


class ImageViewer(Resource):  # GET /images/<int:image_id>/
    @jwt_authorizer(User, None, use_session=False)
    def get(self, image_id: int):
        return send_from_directory("../files/images/", str(image_id) + ".png")
