from functools import wraps
from json import load
from os import remove

from flask import request, send_from_directory, redirect
from flask_restx import Resource, Model
from flask_restx.fields import Integer

from common import ResourceController, ResponseDoc, User, counter_parser
from .wip_files_db import JSONFile, WIPPage, WIPModule
from ..authorship import Author
from ..knowledge import Page, Module

wip_images_namespace = ResourceController("wip-images", path="/wip/images/")
images_view_namespace = ResourceController("images", path="/images/")
image_ids_response: ResponseDoc = ResponseDoc(
    model=Model("Image IDs", {"author-id": Integer, "image-id": Integer})
)


@wip_images_namespace.route("/")
class ImageAdder(Resource):
    @wip_images_namespace.doc_file_param("image")
    @wip_images_namespace.doc_responses(image_ids_response)
    @wip_images_namespace.jwt_authorizer(Author, use_session=False)
    def post(self, author: Author):
        """Creates a new wip-image, saves it and create a permanent url for it"""
        author_id: int = author.id
        image_id: int = author.get_next_image_id()
        with open(f"../files/images/{author_id}-{image_id}.png", "wb") as f:
            f.write(request.data)
        return {"author-id": author_id, "image-id": image_id}


@wip_images_namespace.route("/<int:image_id>/")
class ImageProcessor(Resource):
    @wip_images_namespace.response(302, "Redirect to /images/{author_id}-{image_id}/")
    @wip_images_namespace.jwt_authorizer(Author, use_session=False)
    def get(self, author: Author, image_id: int):
        """Redirects to a global permanent url for this image_id & author"""
        return redirect(f"/images/{author.id}-{image_id}/")

    @wip_images_namespace.doc_file_param("image")
    @wip_images_namespace.jwt_authorizer(Author, use_session=False)
    @wip_images_namespace.a_response()
    def put(self, author: Author, image_id: int) -> None:
        """Overwrites author's wip-image with request's body"""
        with open(f"../files/images/{author.id}-{image_id}.png", "wb") as f:
            f.write(request.data)

    @wip_images_namespace.jwt_authorizer(Author, use_session=False)
    @wip_images_namespace.a_response()
    def delete(self, author: Author, image_id: int) -> None:
        """Deletes author's wip-image, removes the permanent url"""
        remove(f"../files/images/{author.id}-{image_id}.png")


@images_view_namespace.route("/<int:author_id>-<int:image_id>/")
class ImageViewer(Resource):
    @images_view_namespace.response(200, "PNG image as a byte string")
    @images_view_namespace.jwt_authorizer(User, check_only=True, use_session=False)
    def get(self, author_id: int, image_id: int):
        """Global loader for images uploaded by any author"""
        return send_from_directory("../files/images/", f"{author_id}-{image_id}.png")


wip_json_file_namespace = ResourceController("wip-files", path="/wip/<file_type>/")
wip_index_namespace = ResourceController("wip-files", path="/wip/")


@wip_index_namespace.route("/modules/index/")
class WIPModuleLister(Resource):
    @wip_index_namespace.jwt_authorizer(Author)
    @wip_index_namespace.argument_parser(counter_parser)
    @wip_index_namespace.lister(50, WIPModule.FullModel, skip_none=False)
    def post(self, session, author: Author, start: int, finish: int):
        """Lists all Author's wip-modules' metadata for author studio"""
        return WIPModule.find_by_owner(session, author, start, finish - start)


@wip_index_namespace.route("/pages/index/")
class WIPPageLister(Resource):
    @wip_index_namespace.jwt_authorizer(Author)
    @wip_index_namespace.argument_parser(counter_parser)
    @wip_index_namespace.lister(50, WIPPage.FullModel, skip_none=False)
    def post(self, session, author: Author, start: int, finish: int):
        """Lists all Author's wip-pages' metadata for author studio"""
        return WIPPage.find_by_owner(session, author, start, finish - start)


def file_getter(
    type_only: bool = True, use_session: bool = True, use_author: bool = False
):
    def file_getter_wrapper(function):
        @wraps(function)
        @wip_json_file_namespace.jwt_authorizer(Author)
        def get_file_or_type(*args, **kwargs):
            session = kwargs.pop("session")
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
                    session, kwargs["file_id"] if type_only else kwargs.pop("file_id")
                )
                if file is None:
                    return {"a": "File not found"}, 404
                if (
                    file.owner
                    != (kwargs["author"] if use_author else kwargs.pop("author")).id
                ):
                    return {"a": "Access denied"}, 403
                if not type_only:
                    if use_session:
                        return function(file=file, session=session, *args, **kwargs)
                    else:
                        return function(file=file, *args, **kwargs)
            if use_session:
                return function(file_type=result, session=session, *args, **kwargs)
            else:
                return function(file_type=result, *args, **kwargs)

        return get_file_or_type

    return file_getter_wrapper


@wip_json_file_namespace.route("/")
class FileCreator(Resource):
    @wip_json_file_namespace.doc_file_param("json")
    @wip_json_file_namespace.doc_responses(
        ResponseDoc(model=Model("ID Response", {"id": Integer}))
    )
    @file_getter()
    def post(self, session, author: Author, file_type: type[JSONFile]):
        """Creates a new wip-file, saves its contents and adds its metadata to index"""
        try:
            result: file_type = file_type.create_from_json(
                session, author, request.get_json()
            )
        except KeyError as e:
            return {"a": f"{file_type.__name__}'s json is missing {str(e)}"}, 400
        # for CATFile  result: file_type = file_type.create_with_file(author, request.get_data())
        return {"id": result.id}


@wip_json_file_namespace.route("/<int:file_id>/")
class FileProcessor(Resource):
    @wip_json_file_namespace.response(200, "JSON-file of the file type")
    @file_getter(type_only=False, use_session=False)
    def get(self, file: JSONFile):
        """Loads author's wip-file's full contents"""
        with open(file.get_link(), "rb") as f:
            return load(f)

    @wip_json_file_namespace.doc_file_param("json")
    @file_getter(type_only=False)
    @wip_json_file_namespace.a_response()
    def put(self, session, file: JSONFile) -> None:
        """Overwrites author's wip-file's contents and modifies index accordingly"""
        file.update_json(session, request.get_json())

    @wip_json_file_namespace.doc_file_param("json")
    @file_getter(type_only=False)
    @wip_json_file_namespace.a_response()
    def delete(self, session, file: JSONFile) -> None:
        """Deletes author's wip-file's contents and erases its metadata form the index"""
        file.delete(session)


@wip_json_file_namespace.route("/<int:file_id>/publication/")
class FilePublisher(Resource):
    @file_getter(type_only=False, use_author=True)
    @wip_json_file_namespace.a_response()
    def post(self, session, file: JSONFile, author: Author) -> str:
        """Validates and then publishes author's wip-file"""
        with open(file.get_link(), "rb") as f:
            content: dict = load(f)
            content["id"] = file.id  # just making sure
            result: bool = (Page if isinstance(file, WIPPage) else Module).find_or_create(
                session, content, author
            ) is None
        return "File already exists" if result else "Success"  # redo!!!
