from __future__ import annotations

from functools import wraps
from json import load as load_json
from os import remove

from flask import redirect, request, send_from_directory
from flask_fullstack import counter_parser, get_or_pop
from flask_restx import Model, Resource
from flask_restx.fields import Integer

from common import ResourceController, ResponseDoc, User, open_file, absolute_path
from .wip_files_db import JSONFile, WIPModule, WIPPage
from ..authorship import Author
from ..knowledge import Module, Page

wip_images_namespace = ResourceController("wip-images", path="/wip/images/")
images_view_namespace = ResourceController("images", path="/images/")
image_ids_response: ResponseDoc = ResponseDoc(
    model=Model("Image IDs", {"author-id": Integer, "image-id": Integer})
)


@wip_images_namespace.route("/")
class ImageAdder(Resource):
    @wip_images_namespace.doc_file_param("image")
    @wip_images_namespace.doc_responses(image_ids_response)
    @wip_images_namespace.jwt_authorizer(Author)
    def post(self, author: Author):
        """Creates a new wip-image, saves it and create a permanent url for it"""
        author_id: int = author.id
        image_id: int = author.get_next_image_id()
        with open_file(f"files/images/{author_id}-{image_id}.png", "wb") as f:
            f.write(request.data)
        return {"author-id": author_id, "image-id": image_id}


@wip_images_namespace.route("/<int:image_id>/")
class ImageProcessor(Resource):
    @wip_images_namespace.response(302, "Redirect to /images/{author_id}-{image_id}/")
    @wip_images_namespace.jwt_authorizer(Author)
    def get(self, author: Author, image_id: int):
        """Redirects to a global permanent url for this image_id & author"""
        return redirect(f"/images/{author.id}-{image_id}/")

    @wip_images_namespace.doc_file_param("image")
    @wip_images_namespace.jwt_authorizer(Author)
    @wip_images_namespace.a_response()
    def put(self, author: Author, image_id: int) -> None:
        """Overwrites author's wip-image with request's body"""
        with open_file(f"files/images/{author.id}-{image_id}.png", "wb") as f:
            f.write(request.data)

    @wip_images_namespace.jwt_authorizer(Author)
    @wip_images_namespace.a_response()
    def delete(self, author: Author, image_id: int) -> None:
        """Deletes author's wip-image, removes the permanent url"""
        remove(absolute_path(f"files/images/{author.id}-{image_id}.png"))


@images_view_namespace.route("/<int:author_id>-<int:image_id>/")
class ImageViewer(Resource):
    @images_view_namespace.response(200, "PNG image as a byte string")
    @images_view_namespace.jwt_authorizer(User, check_only=True)
    def get(self, author_id: int, image_id: int):
        """Global loader for images uploaded by any author"""
        return send_from_directory(absolute_path("files/images/"), f"{author_id}-{image_id}.png")


wip_json_file_namespace = ResourceController("wip-files", path="/wip/<file_type>/")
wip_index_namespace = ResourceController("wip-files", path="/wip/")


@wip_index_namespace.route("/modules/index/")
class WIPModuleLister(Resource):
    @wip_index_namespace.jwt_authorizer(Author)
    @wip_index_namespace.argument_parser(counter_parser)
    @wip_index_namespace.lister(50, WIPModule.FullModel, skip_none=False)
    def post(self, author: Author, start: int, finish: int):
        """Lists all Author's wip-modules' metadata for author studio"""
        return WIPModule.find_by_owner(author, start, finish - start)


@wip_index_namespace.route("/pages/index/")
class WIPPageLister(Resource):
    @wip_index_namespace.jwt_authorizer(Author)
    @wip_index_namespace.argument_parser(counter_parser)
    @wip_index_namespace.lister(50, WIPPage.FullModel, skip_none=False)
    def post(self, author: Author, start: int, finish: int):
        """Lists all Author's wip-pages' metadata for author studio"""
        return WIPPage.find_by_owner(author, start, finish - start)


def file_getter(  # TODO # noqa: WPS231
    type_only: bool = True,
    use_author: bool = False,
):
    def file_getter_wrapper(function):  # TODO # noqa: WPS231
        @wip_json_file_namespace.jwt_authorizer(Author)
        @wraps(function)
        def get_file_or_type(*args, **kwargs):
            result: type[JSONFile]
            file_type: str = kwargs.pop("file_type")
            if file_type == "modules":
                result = WIPModule
            elif file_type == "pages":
                result = WIPPage
            else:
                return {"a": f"File type '{file_type}' is not supported"}, 400

            if "file_id" in kwargs:
                file: result = result.find_by_id(
                    get_or_pop(kwargs, "file_id", type_only)
                )
                if file is None:
                    return {"a": "File not found"}, 404
                if file.owner != (get_or_pop(kwargs, "author", use_author)).id:
                    return {"a": "Access denied"}, 403
                if not type_only:
                    return function(*args, file=file, **kwargs)
            return function(*args, file_type=result, **kwargs)

        return get_file_or_type

    return file_getter_wrapper


@wip_json_file_namespace.route("/")
class FileCreator(Resource):
    @wip_json_file_namespace.doc_file_param("json")
    @wip_json_file_namespace.doc_responses(
        ResponseDoc(model=Model("ID Response", {"id": Integer}))
    )
    @file_getter()
    def post(self, author: Author, file_type: type[JSONFile]):
        """Creates a new wip-file, saves its contents and adds its metadata to index"""
        try:
            result: file_type = file_type.create_from_json(author, request.get_json())
        except KeyError as e:
            return {"a": f"{file_type.__name__}'s json is missing {e}"}, 400
        # for CATFile  result: file_type = file_type.create_with_file(author, request.get_data())
        return {"id": result.id}


@wip_json_file_namespace.route("/<int:file_id>/")
class FileProcessor(Resource):
    @wip_json_file_namespace.response(200, "JSON-file of the file type")
    @file_getter(type_only=False)
    def get(self, file: JSONFile):
        """Loads author's wip-file's full contents"""
        with open_file(file.get_link()) as f:
            return load_json(f)

    @wip_json_file_namespace.doc_file_param("json")
    @file_getter(type_only=False)
    @wip_json_file_namespace.a_response()
    def put(self, file: JSONFile) -> None:
        """Overwrites author's wip-file's contents and modifies index accordingly"""
        file.update_json(request.get_json())

    @wip_json_file_namespace.doc_file_param("json")
    @file_getter(type_only=False)
    @wip_json_file_namespace.a_response()
    def delete(self, file: JSONFile) -> None:
        """Deletes author's wip-file's contents and erases its metadata form the index"""
        file.delete()


@wip_json_file_namespace.route("/<int:file_id>/publication/")
class FilePublisher(Resource):
    @file_getter(type_only=False, use_author=True)
    @wip_json_file_namespace.a_response()
    def post(self, file: JSONFile, author: Author) -> str:
        """Validates and then publishes author's wip-file"""
        with open_file(file.get_link()) as f:
            content: dict = load_json(f)
            content["id"] = file.id  # just making sure
            klass = Page if isinstance(file, WIPPage) else Module
            result: bool = klass.find_or_create(content, author) is None
        return "File already exists" if result else "Success"  # redo!!!
