# Request models for the survey map
# Author: Owen Martin
# ---------------------------------------------------------------------------------------------------------------------------
# The survey map reads images, footprints, predictions and annotations; it has no table of its own,
# so only the requests of its routes are defined here.
# ---------------------------------------------------------------------------------------------------------------------------

from uuid import UUID

from pydantic import BaseModel

# ---------------------------------------------------------------------------------------------------------------------------


class SurveyMapQuery(BaseModel):
    survey_id: UUID


class OverlayReq(BaseModel):
    image_id: UUID


class DetectionCropReq(BaseModel):
    image_id: UUID
    box: list[int]  # tx, ty, bx, by in image pixels
    kind: str = "estimated"
