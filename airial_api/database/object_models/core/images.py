# Class definition for Image objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------

import io
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Union
from uuid import UUID

import cv2
import numpy as np
import PIL.Image as PillowImage
from pydantic import BaseModel, field_validator

from ..base import Box, DBbase

# ---------------------------------------------------------------------------------------------------------------------------


class ImageMixin:
    image: Optional[np.ndarray] = None

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def set_image(self, imageData: np.ndarray):
        if isinstance(imageData, bytes):
            try:
                pilImage = PillowImage.open(io.BytesIO(imageData))
                pilImage = pilImage.convert("RGB")
                self.image = cv2.cvtColor(np.array(pilImage), cv2.COLOR_RGB2BGR)
            except Exception as e:
                print(f"Error converting bytes to image: {e}")
                self.image = None
        elif isinstance(imageData, np.ndarray):
            self.image = imageData

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def get_image(self) -> Optional[np.ndarray]:
        if self.image is not None:
            return self.image

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def deleteImage(self):
        del self.image

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serve(self, img_format: str):
        if self.image is not None:
            _, img_encoded = cv2.imencode(
                img_format,
                self.get_image(),  # pyright: ignore
                [cv2.IMWRITE_JPEG_QUALITY, 100],  # pyright: ignore
            )
        else:
            raise Exception("no image data")
        return img_encoded.tobytes()

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@dataclass
class Image(DBbase, ImageMixin):
    image_id: int
    herd_unit_id: int
    survey_id: int
    name: str
    img_key: str
    in_training: bool
    crops_generated: int
    opened_by_user_id: int
    created: datetime
    modified: datetime
    image_length_px: int
    image_width_px: int
    area: float
    viewshed_polygon: List[List[float]]
    has_detection: bool
    dem_name: str
    bbox_wsen: List[int]
    uuid: UUID

    image: Optional[np.ndarray] = field(default=None, init=False)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def to_dict(self) -> dict:
        return {
            "image_id": self.image_id,
            "herd_unit_id": self.herd_unit_id,
            "survey_id": self.survey_id,
            "img_key": self.img_key,
            "name": self.name,
            "in_training": self.in_training,
            "crops_generated": self.crops_generated,
            "created": self.created,
            "modified": self.modified,
            "image_length_px": self.image_length_px,
            "image_width_px": self.image_width_px,
            "uuid": str(self.uuid),
        }


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class ReviewedArea(DBbase, ImageMixin):
    image_id: int
    name: str
    created: datetime
    modified: datetime
    area_tx: int
    area_ty: int
    area_bx: int
    area_by: int
    reviewed_area_length_px: int
    reviewed_area_width_px: int
    reviewed_area_id: int
    reviewed_by_user_id: int
    uuid: UUID

    ra_key: Optional[str] = None
    dimensions: "Box" = field(init=False)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def __post_init__(self):
        self.dimensions = Box(
            (self.area_tx, self.area_ty), (self.area_bx, self.area_by)
        )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def to_dict(self) -> dict:
        return {
            "reviewed_area_id": self.reviewed_area_id,
            "image_id": self.image_id,
            "name": self.name,
            "dimensions": self.dimensions.to_dict(),
            "created": self.fmt_date(self.created),
            "modified": self.fmt_date(self.modified),
            "reviewed_area_length_px": self.reviewed_area_length_px,
            "reviewed_area_width_px": self.reviewed_area_width_px,
            "ra_key": self.ra_key,
            "uuid": str(self.uuid),
        }


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class PredictionCrop(DBbase, ImageMixin):
    image_id: int
    name: str
    pred_id: int
    score: float
    label: int
    uuid: UUID
    dimensions: "Box"
    boundingBox: "Box"
    url: Optional[str] = None
    approved: bool = field(default=False, init=False)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def to_dict(self) -> dict:
        return {
            "image_id": self.image_id,
            "approved": self.approved,
            "label": self.label,
            "dimensions": self.dimensions.to_dict(),
            "boundingBox": self.boundingBox.to_dict(),
            "uuid": str(self.uuid),
        }


# ---------------------------------------------------------------------------------------------------------------------------


class CreateImageReq(BaseModel):
    name: str
    herd_unit_id: Union[int, str]
    survey_id: Union[int, str]
    img_key: str
    image_length_px: int
    image_width_px: int
    area: Optional[int] = None
    viewshed_polygon: Optional[List[List[float]]] = None
    has_detection: bool = False
    dem_name: Optional[str] = None
    bbox_wsen: Optional[List[int]] = None


# ---------------------------------------------------------------------------------------------------------------------------


class CreatePresignedPutReq(BaseModel):
    image_id: Union[str, int]
    upload_id: str
    part_number: int
    chunk_size: int
    chunk_md5: str


# ---------------------------------------------------------------------------------------------------------------------------


class UpdateImageReq(BaseModel):
    name: Optional[str] = None
    herd_unit_id: Optional[int] = None
    survey_id: Optional[int] = None
    img_key: Optional[str] = None
    image_length_px: Optional[int] = None
    image_width_px: Optional[int] = None
    area: Optional[int] = None
    opened_by_user_id: Optional[int] = None
    viewshed_polygon: Optional[List[List[float]]] = None
    has_detection: bool = False
    dem_name: Optional[str] = None
    bbox_wsen: Optional[List[int]] = None


# ---------------------------------------------------------------------------------------------------------------------------


class CreatePredictionCropReq(BaseModel):
    image_id: UUID
    prediction_id: List[UUID]

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @field_validator("prediction_id")
    @classmethod
    def ensure_list(cls, value):
        if isinstance(value, list):
            return value
        if value is None or value == "":
            return []
        return [value]


# ---------------------------------------------------------------------------------------------------------------------------


class RAQuery(BaseModel):
    herd_unit_id: Optional[List[UUID]]
    survey_id: Optional[List[UUID]]
    include_reviewed: Optional[bool] = False
    include_opened: Optional[bool] = False
    num: Optional[int] = None

    @field_validator("herd_unit_id", "survey_id", mode="before")
    @classmethod
    def ensure_list(cls, value):
        if isinstance(value, list):
            return value
        if value is None or value == "":
            return []
        return [value]


# ---------------------------------------------------------------------------------------------------------------------------


class CreateReviewedAreaReq(BaseModel, ImageMixin):
    image_id: UUID
    name: str
    area_tx: int
    area_ty: int
    area_bx: int
    area_by: int
    reviewed_area_length_px: int
    reviewed_area_width_px: int
    reviewed_by_user_id: int = 0
    ra_key: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


# ---------------------------------------------------------------------------------------------------------------------------


class UpdateReviewedAreaReq(BaseModel):
    image_id: Optional[UUID] = None
    name: Optional[str] = None
    area_tx: Optional[int] = None
    area_ty: Optional[int] = None
    area_bx: Optional[int] = None
    area_by: Optional[int] = None
    reviewed_area_length_px: Optional[int] = None
    reviewed_area_width_px: Optional[int] = None
    ra_key: Optional[str] = None
