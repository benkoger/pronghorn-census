# Endpoints for crop verification in the API
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------#

from typing import cast
from uuid import UUID

from flask import Blueprint, abort, current_app
from flask_login import current_user, login_required
from flask_pydantic import validate
from psycopg.errors import DatabaseError

from app.extensions import base
from database import ObjectNotFound
from database.object_models import ApproveAnnotationsReq
from database.object_models.core import RAQuery
from database.object_models.user_management import User

verifierBp = Blueprint("verifier", __name__, url_prefix="/api/v1/verifier")

# ---------------------------------------------------------------------------------------------------------------------------#
# GET


@verifierBp.get("/area-needing-reviewed")
@login_required
@validate()
def get(query: RAQuery):
    """
    Retrieve a reviewed area
    ---
    paramaters:
      - in: query
            name: herd_unit_id
            type: number
      - in: query
            name: survey_id
            type: number
    responses:
            200:
                    description: List of reviewed areas.
            400:
                    description: Invalid UUID format.
            404:
                    description: No reviewed areas found.
            500:
                    description: Database error.
    """
    try:
        query.num = 1
        reviewed_areas = base.get_crop_to_review(query, cast(User, current_user))
        current_app.logger.info(reviewed_areas)
    except ObjectNotFound as e:
        current_app.logger.exception(e)
        abort(404, str(e))
    except (DatabaseError, Exception) as e:
        current_app.logger.exception(e)
        abort(500)

    return reviewed_areas[0].to_dict(), 200


@verifierBp.get("/needing-reviewed")
@login_required
@validate()
def get_selection_count(query: RAQuery):
    """ """
    try:
        count = base.get_crop_to_review_selection_count(query)
    except ObjectNotFound as e:
        current_app.logger.exception(e)
        abort(404, str(e))
    except (DatabaseError, Exception) as e:
        current_app.logger.exception(e)
        abort(500)

    return {"count": count}, 200




# @verifierBp.put("/submit")
# @login_required
# @validate()
# def approve_annotations(body: ApproveAnnotationsReq):
#     """ """
#     data = body.model_dump()
#
#     # loop over incoming annotation data
#     for annot in data["annotations"]:
#         # check if annotation in the database
#         try:
#             if base.get_annotation_exists(UUID(annot["uuid"])):
#                 # TODO: check if annotation still inersects prediction in threshold
#                 # update annotation
#                 res_i = base.update_annotation(
#                     annot["annotation_id"],
#                     label_id=annot["label_id"],
#                     box_tx=annot["dimensions"]["top_left"]["x"],
#                     box_ty=annot["dimensions"]["top_left"]["y"],
#                     box_bx=annot["dimensions"]["bottom_right"]["x"],
#                     box_by=annot["dimensions"]["bottom_right"]["y"],
#                 )
#             # else
#             else:
#                 # create annotation
#                 base.create_annotation(
#                     data["reviewed_area_id"],
#                     {
#                         "label_id": annot["label_id"],
#                         "image_id": annot["image_id"],
#                         "herd_unit_id": annot["herd_unit_id"],
#                         "box_tx": annot["dimensions"]["top_left"]["x"],
#                         "box_ty": annot["dimensions"]["top_left"]["y"],
#                         "box_bx": annot["dimensions"]["bottom_right"]["x"],
#                         "box_by": annot["dimensions"]["bottom_right"]["y"],
#                         "user_id": current_user.user_id,
#                         "uuid": annot["uuid"],
#                     },
#                 )
#         except ObjectNotFound as e:
#             current_app.logger.exception(e)
#             abort(404, str(e))
#         except (DatabaseError, Exception) as e:
#             current_app.logger.exception(e)
#             abort(500)
#
#     # loop over deleted annotations
#     try:
#         # TODO: add method to delete multiple dicts in a single pass
#         for annot in data["deleted_annotations"]:
#             base.delete_annotation(annot["annotation_id"])
#
#         # set crop reviewed
#         base.update_reviewed_area(
#             data["reviewed_area_id"], reviewed_by_user_id=current_user.user_id
#         )
#
#         # set image closed
#         base.update_image(data["image_id"], {"opened_by_user_id": 0})
#     except (DatabaseError, Exception):
#         abort(500)
#
#     return "", 201
