# Class definition for ImageMetadata objects in the database
# Authors: Michael B. Lance, Antigravity
# ---------------------------------------------------------------------------------------------------------------------------

from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar, Optional, Self
from uuid import UUID

from authzed.api.v1 import RelationshipUpdate
import psycopg.sql as sql
from psycopg import Cursor
from psycopg.rows import class_row
from pydantic import BaseModel, ConfigDict

from database.object_models.base import DBbase, Keyring, create_spice_update

# ---------------------------------------------------------------------------------------------------------------------------


class CreateImageMetadataReq(BaseModel):
    image_ids: Keyring
    captured_at: datetime
    gps_lon: float
    gps_lat: float
    gps_alt_msl_m: float
    yaw_deg: float
    pitch_deg: float
    fov_deg: float
    terrain_elev_m: float
    agl_m: float

    model_config = ConfigDict(arbitrary_types_allowed=True)


# ---------------------------------------------------------------------------------------------------------------------------


class UpdateImageMetadataReq(BaseModel):
    captured_at: Optional[datetime] = None
    gps_lon: Optional[float] = None
    gps_lat: Optional[float] = None
    gps_alt_msl_m: Optional[float] = None
    yaw_deg: Optional[float] = None
    pitch_deg: Optional[float] = None
    fov_deg: Optional[float] = None
    terrain_elev_m: Optional[float] = None
    agl_m: Optional[float] = None


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class ImageMetadata(DBbase):
    metadata_id: int
    image_id: int
    captured_at: datetime
    gps_lon: float
    gps_lat: float
    gps_alt_msl_m: float
    yaw_deg: float
    pitch_deg: float
    fov_deg: float
    terrain_elev_m: float
    agl_m: float
    created: datetime
    modified: datetime
    uuid: UUID

    __table__: ClassVar[sql.Identifier] = sql.Identifier("core", "image_metadata")
    __pk__: ClassVar[sql.Identifier] = sql.Identifier("metadata_id")
    __parent_table__: ClassVar[sql.Identifier] = sql.Identifier("core", "images")
    __parent_fk__: ClassVar[sql.Identifier] = sql.Identifier("image_id")

    # -----------------------------------------------------------------------------------------------------------------------

    class Response(BaseModel):
        model_config = ConfigDict(from_attributes=True)

        metadata_id: int
        image_id: int
        captured_at: datetime
        gps_lon: float
        gps_lat: float
        gps_alt_msl_m: float
        yaw_deg: float
        pitch_deg: float
        fov_deg: float
        terrain_elev_m: float
        agl_m: float
        created: datetime
        modified: datetime
        uuid: UUID

    # -----------------------------------------------------------------------------------------------------------------------

    @classmethod
    def _create(
        cls, cursor: Cursor[Self], req: CreateImageMetadataReq
    ) -> Optional[tuple[Self, list[RelationshipUpdate]]]:
        cursor.row_factory = class_row(cls)
        query = sql.SQL("""
            INSERT INTO core.image_metadata (
                image_id, captured_at, gps_lon, gps_lat, gps_alt_msl_m,
                yaw_deg, pitch_deg, fov_deg, terrain_elev_m, agl_m
            )
            VALUES (
                %(image_id)s, %(captured_at)s, %(gps_lon)s, %(gps_lat)s, %(gps_alt_msl_m)s,
                %(yaw_deg)s, %(pitch_deg)s, %(fov_deg)s, %(terrain_elev_m)s, %(agl_m)s
            )
            RETURNING *;
        """)

        cursor.execute(
            query,
            {
                **req.model_dump(),
                "image_id": req.image_ids.pkey,
            },
        )

        if not (metadata := cursor.fetchone()):
            return None

        spice_updates = [
            create_spice_update(
                "image_metadata",
                metadata.uuid,
                "image",
                req.image_ids.uuid,
                "parent",
            )
        ]

        return metadata, spice_updates

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serialize(self) -> dict[str, Any]:
        return ImageMetadata.Response.model_validate(self).model_dump(mode="json")
