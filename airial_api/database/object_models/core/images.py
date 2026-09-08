# Class definition for Image objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------

import io
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, Self
from uuid import UUID

import cv2
import numpy as np
import PIL.Image as PillowImage
import psycopg.sql as sql
from psycopg import Cursor
from psycopg.rows import class_row
from pydantic import BaseModel, field_validator, ConfigDict
from authzed.api.v1 import RelationshipUpdate

from ..base import Box, Keyring, create_spice_update, DBbase

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

    def delete_image(self):
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


# ---------------------------------------------------------------------------------------------------------------------------


class CreateImageReq(BaseModel):
    name: str
    herd_unit_ids: Keyring
    survey_ids: Keyring
    img_key: str
    image_length_px: int
    image_width_px: int
    area: Optional[int] = None
    viewshed_polygon: Optional[list[list[float]]] = None
    has_detection: bool = False
    dem_name: Optional[str] = None
    bbox_wsen: Optional[list[int]] = None


# ---------------------------------------------------------------------------------------------------------------------------


class CreatePresignedPutReq(BaseModel):
    image_id: int | UUID
    upload_id: str
    part_number: int
    chunk_size: int
    chunk_md5: str


# ---------------------------------------------------------------------------------------------------------------------------


class PresignedImageGetReq(BaseModel):
    image_id: UUID
    expires_in: int


# ---------------------------------------------------------------------------------------------------------------------------


class CreateImageMultiPartUploadReq(BaseModel):
    image_key: str


# ---------------------------------------------------------------------------------------------------------------------------


class AbortMulitPartUploadReq(BaseModel):
    image_key: str
    upload_id: str


# ---------------------------------------------------------------------------------------------------------------------------


class CompleteMultiPartUploadReq(BaseModel):
    image_key: str
    upload_id: str
    parts: list[Any]


# ---------------------------------------------------------------------------------------------------------------------------


class UpdateImageReq(BaseModel):
    name: Optional[str] = None
    img_key: Optional[str] = None
    image_length_px: Optional[int] = None
    image_width_px: Optional[int] = None
    area: Optional[int] = None
    opened_by_user_id: Optional[int] = None
    viewshed_polygon: Optional[list[list[float]]] = None
    has_detection: bool = False
    dem_name: Optional[str] = None
    bbox_wsen: Optional[list[int]] = None


# ---------------------------------------------------------------------------------------------------------------------------


class CreatePredictionCropReq(BaseModel):
    image_id: UUID
    prediction_id: list[UUID]

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
    herd_unit_id: Optional[list[UUID]]
    survey_id: Optional[list[UUID]]
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
    image_ids: Keyring
    name: str
    area_tx: int
    area_ty: int
    area_bx: int
    area_by: int
    reviewed_area_length_px: int
    reviewed_area_width_px: int
    reviewed_by_user_id: int = 0
    ra_key: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


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
    reviewed_by_user_id: Optional[int] = None


# ---------------------------------------------------------------------------------------------------------------------------


class CrateReviewedAreaPresignedGetReq(BaseModel):
    reviewed_area_id: UUID


# ---------------------------------------------------------------------------------------------------------------------------


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
    viewshed_polygon: list[list[float]]
    has_detection: bool
    dem_name: str
    bbox_wsen: Optional[list[int]]
    uuid: UUID

    image: Optional[np.ndarray] = field(default=None, init=False)

    __tablename__: str = "images"
    __schema__: str = "core"
    __pk_name__: str = "image_id"

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class Response(BaseModel):
        model_config = ConfigDict(from_attributes=True)

        image_id: int
        herd_unit_id: int
        survey_id: int
        name: str
        img_key: str
        in_training: bool
        crops_generated: int
        created: datetime
        modified: datetime
        image_length_px: int
        image_width_px: int
        uuid: UUID

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def _create(
        cls, cursor: Cursor[Self], req: CreateImageReq
    ) -> Optional[tuple[Self, list[RelationshipUpdate]]]:
        cursor.row_factory = class_row(cls)
        query = sql.SQL("""
            INSERT INTO core.images (
                herd_unit_id, survey_id, name, img_key, image_length_px,
                image_width_px, area, viewshed_polygon, has_detection,
                dem_name, bbox_wsen
            )
            VALUES (
                %(herd_unit_id)s, %(survey_id)s, %(name)s,
                %(img_key)s, %(image_length_px)s,
                %(image_width_px)s, %(area)s, %(viewshed_polygon)s,
                %(has_detection)s, %(dem_name)s, %(bbox_wsen)s
                )
            RETURNING *;
        """)

        cursor.execute(
            query,
            {
                **req.model_dump(),
                "herd_unit_id": req.herd_unit_ids.pkey,
                "survey_id": req.survey_ids.pkey,
            },
        )

        if not (image := cursor.fetchone()):
            return None

        spice_updates = [
            create_spice_update(
                "image", image.uuid, "survey", req.survey_ids.uuid, "parent"
            ),
            create_spice_update(
                "image", image.uuid, "herd_unit", req.herd_unit_ids.uuid, "parent"
            ),
        ]

        return image, spice_updates

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serialize(self) -> dict:
        return Image.Response.model_validate(self).model_dump(mode="json")


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class ReviewedArea(DBbase, ImageMixin):
    reviewed_area_id: int
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
    reviewed_by_user_id: int
    uuid: UUID

    ra_key: Optional[str] = None
    dimensions: "Box" = field(init=False)

    __tablename__: str = "reviewed_area"
    __schema__: str = "core"
    __pk_name__: str = "reviewed_area_id"

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def __post_init__(self):
        self.dimensions = Box(
            (self.area_tx, self.area_ty), (self.area_bx, self.area_by)
        )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class Response(BaseModel):
        model_config = ConfigDict(from_attributes=True)

        reviewed_area_id: int
        image_id: int
        name: str
        dimensions: dict[str, dict[str, int]]
        created: datetime
        modified: datetime
        reviewed_area_length_px: int
        reviewed_area_width_px: int
        ra_key: str
        uuid: UUID

        @field_validator("dimensions", mode="before")
        @classmethod
        def transform(cls, value):
            if isinstance(value, Box):
                return value.serialize()
            return value

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def _create(
        cls, cursor: Cursor[Self], req: CreateReviewedAreaReq
    ) -> Optional[tuple[Self, list[RelationshipUpdate]]]:
        cursor.row_factory = class_row(cls)
        query = sql.SQL("""
            INSERT INTO core.reviewed_area (
                image_id, name, area_tx, area_ty, area_bx, area_by, reviewed_area_length_px,
                reviewed_area_width_px, reviewed_by_user_id, ra_key
            )
            VALUES (
                %(image_id)s, %(name)s, %(area_tx)s, %(area_ty)s, %(area_bx)s, %(area_by)s, 
                %(reviewed_area_length_px)s, %(reviewed_area_width_px)s, %(reviewed_by_user_id)s,
                %(ra_key)s
            )
            RETURNING *;
        """)

        cursor.execute(query, {**req.model_dump(), "image_id": req.image_ids.pkey})

        if not (reviewed_area := cursor.fetchone()):
            return None

        spice_updates = [
            create_spice_update(
                "reviewed_area",
                reviewed_area.uuid,
                "image",
                req.image_ids.uuid,
                "parent",
            )
        ]

        return reviewed_area, spice_updates

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serialize(self) -> dict:
        return ReviewedArea.Response.model_validate(self).model_dump(mode="json")


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

    class Response(BaseModel):
        model_config = ConfigDict(from_attributes=True)

        image_id: int
        score: float
        pred_id: int
        name: str
        approved: bool
        label: int
        dimensions: dict[str, dict[str, int]]
        boundingBox: dict[str, dict[str, int]]
        uuid: UUID

        @field_validator("dimensions", "boundingBox", mode="before")
        @classmethod
        def transform(cls, value: Any) -> Any:
            if isinstance(value, Box):
                return value.serialize()
            return value

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def _create(
        cls, cursor: Cursor[Self], req: CreatePredictionCropReq
    ) -> Optional[tuple[Self, list[RelationshipUpdate]]]: ...

    ### This method will never be implemented, just proves we need smarter
    ### abstraction in the future

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serialize(self) -> dict[str, Any]:
        return PredictionCrop.Response.model_validate(self).model_dump(mode="json")


# ---------------------------------------------------------------------------------------------------------------------------
