"""Request models of the survey map.

The survey map reads images, footprints, predictions and annotations and has
no table of its own, so only its requests are defined here.
"""

from uuid import UUID

from pydantic import BaseModel

# ---------------------------------------------------------------------------------------------------------------------------


class SurveyMapQuery(BaseModel):
    """The survey whose map is drawn."""

    survey_id: UUID


class OverlayQuery(BaseModel):
    """The image to draw onto the ground."""

    image_id: UUID


class ImageCropsQuery(BaseModel):
    """The image whose annotated animals are shown."""

    image_id: UUID
