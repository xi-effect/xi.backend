from flask import request, send_from_directory
from flask_restful import Resource
from flask_restful.reqparse import RequestParser

from authorship.submissions import CATSubmission
from authorship.user_roles import Author, Moderator
from componets import jwt_authorizer, database_searcher, argument_parser, lister, counter_parser


class Submitter(Resource):  # [POST] /cat/submissions/
    parser: RequestParser = RequestParser()
    parser.add_argument("type", type=int, required=True)
    parser.add_argument("tags", required=True)

    @jwt_authorizer(Author, "author")
    @argument_parser(parser, ("type", "submission_type"), "tags")
    def post(self, author: Author, submission_type: int, tags: str):
        submission: CATSubmission = CATSubmission.create(author.id, submission_type, tags)

        with open(f"submissions/s{submission.id}.json", "wb") as f:
            f.write(request.data)

        return {"a": "Success"}
        # return redirect(googleapis)


class SubmissionLister(Resource):  # [POST] /cat/submissions/owned/
    @jwt_authorizer(Author, "author")
    @lister(24)
    def post(self, author: Author, start: int, finish: int) -> list:
        submission: CATSubmission
        result: list = list()
        for submission in CATSubmission.find_by_author(author.id, start, finish - start):
            result.append(submission.to_author_json())
        return result


class SubmissionIndexer(Resource):  # [POST] /cat/submissions/index/
    parser: RequestParser = counter_parser.copy()
    parser.add_argument("type", type=int, required=False)
    parser.add_argument("tags", required=True)

    @jwt_authorizer(Moderator, None)
    @lister(24, argument_parser(parser, "counter", ("type", "submission_type"), "tags"))
    def post(self, start: int, finish: int, submission_type: int, tags: str):
        submission: CATSubmission
        result: list = list()

        for submission in CATSubmission.find_by_tags(
                set(tags.split(" ")), submission_type, start, finish - start):
            result.append(submission.to_moderator_json())

        return result


class SubmissionReader(Resource):  # [GET] /cat/submissions/<int:submission_id>/
    @jwt_authorizer(Moderator, "moderator")
    @database_searcher(CATSubmission, "submission_id", "submission")
    def get(self, moderator: Moderator, submission: CATSubmission):
        pass  # check if taken

        submission.mark_read()

        return send_from_directory("submissions", f"s{submission.id}.json")


class ReviewIndex(Resource):  # [GET|POST] /cat/reviews/<int:submission_id>/
    parser: RequestParser = RequestParser()
    parser.add_argument("published", type=bool, required=True)

    @jwt_authorizer(Author, "author")
    @database_searcher(CATSubmission, "submission_id", "submission")
    def get(self, author: Author, submission: CATSubmission):
        if submission.author_id != author.id:
            return {"a": "'NOT YOUR STUFF' ERROR"}

        return send_from_directory("submissions", f"r{submission.id}.json")

    @argument_parser(parser, "published")
    @jwt_authorizer(Moderator, "moderator")
    @database_searcher(CATSubmission, "submission_id", "submission")
    def post(self, moderator: Moderator, submission: CATSubmission, published: bool):
        pass  # check if taken

        submission.review(published)

        with open(f"submissions/r{submission.id}.json", "wb") as f:
            f.write(request.data)


class Publisher(Resource):  # [POST] /cat/publications/
    @jwt_authorizer(Moderator, "moderator")
    def post(self, moderator: Moderator):
        pass
