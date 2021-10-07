from os import remove

from flask import request, send_from_directory, redirect
from flask_restx import Resource, Model
from flask_restx.fields import Integer

from authorship import Author
from componets.checkers import Namespace, ResponseDoc
from users import User

wip_images_namespace: Namespace = Namespace("wip-images", path="/wip/images/")
images_view_namespace: Namespace = Namespace("images", path="/images/")
image_ids_response: ResponseDoc = ResponseDoc(model=Model("Image IDs", {"author_id": Integer, "image_id": Integer}))


@wip_images_namespace.route("/")
class ImageAdder(Resource):  # POST /wip/images/
    @wip_images_namespace.doc_responses(image_ids_response)
    @wip_images_namespace.jwt_authorizer(Author, "author", use_session=False)
    def post(self, author: Author):
        author_id: int = author.id
        image_id: int = author.get_next_image_id()
        with open(f"files/images/{author_id}-{image_id}.png", "wb") as f:
            f.write(request.data)
        return {"author_id": author_id, "image_id": image_id}


@wip_images_namespace.route("/<int:image_id>/")
class ImageProcessor(Resource):  # [GET|PUT|DELETE] /wip/images/<int:image_id>/
    @wip_images_namespace.jwt_authorizer(Author, "author", use_session=False)
    def get(self, author: Author, image_id: int):
        return redirect(f"/images/{author.id}-{image_id}/")

    @wip_images_namespace.a_response()
    @wip_images_namespace.jwt_authorizer(Author, "author", use_session=False)
    def put(self, author: Author, image_id: int) -> None:
        with open(f"files/images/{author.id}-{image_id}.png", "wb") as f:
            f.write(request.data)

    @wip_images_namespace.a_response()
    @wip_images_namespace.jwt_authorizer(Author, "author", use_session=False)
    def delete(self, author: Author, image_id: int) -> None:
        remove(f"files/images/{author.id}-{image_id}.png")


@images_view_namespace.route("/<image_id>/")
class ImageViewer(Resource):  # GET /images/<image_id>/
    @images_view_namespace.jwt_authorizer(User, None, use_session=False)
    def get(self, image_id: str):
        return send_from_directory("../files/images/", image_id + ".png")
