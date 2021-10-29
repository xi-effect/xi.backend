from os import remove

from flask import request, send_from_directory, redirect
from flask_restx import Resource, Model
from flask_restx.fields import Integer

from authorship import Author
from componets.checkers import Namespace, ResponseDoc
from users import User

wip_images_namespace: Namespace = Namespace("wip-images", path="/wip/images/")
images_view_namespace: Namespace = Namespace("images", path="/images/")
image_ids_response: ResponseDoc = ResponseDoc(model=Model("Image IDs", {"author-id": Integer, "image-id": Integer}))


@wip_images_namespace.route("/")
class ImageAdder(Resource):  # POST /wip/images/
    @wip_images_namespace.doc_file_param("image")
    @wip_images_namespace.doc_responses(image_ids_response)
    @wip_images_namespace.jwt_authorizer(Author, use_session=False)
    def post(self, author: Author):
        """ Creates a new wip-image, saves it and create a permanent url for it """
        author_id: int = author.id
        image_id: int = author.get_next_image_id()
        with open(f"../files/images/{author_id}-{image_id}.png", "wb") as f:
            f.write(request.data)
        return {"author-id": author_id, "image-id": image_id}


@wip_images_namespace.route("/<int:image_id>/")
class ImageProcessor(Resource):  # [GET|PUT|DELETE] /wip/images/<int:image_id>/
    @wip_images_namespace.response(302, "Redirect to /images/{author_id}-{image_id}/")
    @wip_images_namespace.jwt_authorizer(Author, use_session=False)
    def get(self, author: Author, image_id: int):
        """ Redirects to a global permanent url for this image_id & author """
        return redirect(f"/images/{author.id}-{image_id}/")

    @wip_images_namespace.doc_file_param("image")
    @wip_images_namespace.jwt_authorizer(Author, use_session=False)
    @wip_images_namespace.a_response()
    def put(self, author: Author, image_id: int) -> None:
        """ Overwrites author's wip-image with request's body """
        with open(f"../files/images/{author.id}-{image_id}.png", "wb") as f:
            f.write(request.data)

    @wip_images_namespace.jwt_authorizer(Author, use_session=False)
    @wip_images_namespace.a_response()
    def delete(self, author: Author, image_id: int) -> None:
        """ Deletes author's wip-image, removes the permanent url """
        remove(f"../files/images/{author.id}-{image_id}.png")


@images_view_namespace.route("/<int:author_id>-<int:image_id>/")
class ImageViewer(Resource):  # GET /images/<image_id>/
    @images_view_namespace.response(200, "PNG image as a byte string")
    @images_view_namespace.jwt_authorizer(User, check_only=True, use_session=False)
    def get(self, author_id: int, image_id: int):
        """ Global loader for images uploaded by any author """
        return send_from_directory("../files/images/", f"{author_id}-{image_id}.png")
