# Class definition for ImageFootprint objects in the database
# Authors: Michael B. Lance, Antigravity
# ---------------------------------------------------------------------------------------------------------------------------

from dataclasses import dataclass
from datetime import datetime
import json
from typing import Any, ClassVar, Optional, Self
from uuid import UUID

from authzed.api.v1 import RelationshipUpdate
import psycopg.sql as sql
from psycopg import Cursor
from psycopg.rows import class_row
from pydantic import BaseModel, ConfigDict, field_validator
import shapely
import shapely.geometry

from database.object_models.base import DBbase, Keyring, create_spice_update

# ---------------------------------------------------------------------------------------------------------------------------


class CreateImageFootprintReq(BaseModel):
    image_ids: Keyring
    footprint: Optional[dict[str, Any]] = None
    has_detection: bool = False
    footprint_metadata: Optional[dict[str, Any]] = None
    bbox_wsen: list[float]
    footprint_partial: bool
    area_m2: float
    area_geodesic_m2: float
    area_sigma_m2: float
    area_q05_m2: float
    area_q95_m2: float
    dem_name: str
    georef_status: str
    n_ties: int
    tie_residual_before_m: float
    rmse_h_m: float
    rmse_p50_m: float
    rmse_p90_m: float
    n_checkpoints: int
    pose_delta: list[float]
    pose_sigma: list[float]
    pose_free: list[str]
    pose_cond: float
    prior_source: str
    gcps: dict[str, Any] | list[Any]
    overlay_uri: str
    georef_modified: datetime

    model_config = ConfigDict(arbitrary_types_allowed=True)


# ---------------------------------------------------------------------------------------------------------------------------


class UpdateImageFootprintReq(BaseModel):
    footprint: Optional[dict[str, Any]] = None
    has_detection: Optional[bool] = None
    footprint_metadata: Optional[dict[str, Any]] = None
    bbox_wsen: Optional[list[float]] = None
    footprint_partial: Optional[bool] = None
    area_m2: Optional[float] = None
    area_geodesic_m2: Optional[float] = None
    area_sigma_m2: Optional[float] = None
    area_q05_m2: Optional[float] = None
    area_q95_m2: Optional[float] = None
    dem_name: Optional[str] = None
    georef_status: Optional[str] = None
    n_ties: Optional[int] = None
    tie_residual_before_m: Optional[float] = None
    rmse_h_m: Optional[float] = None
    rmse_p50_m: Optional[float] = None
    rmse_p90_m: Optional[float] = None
    n_checkpoints: Optional[int] = None
    pose_delta: Optional[list[float]] = None
    pose_sigma: Optional[list[float]] = None
    pose_free: Optional[list[str]] = None
    pose_cond: Optional[float] = None
    prior_source: Optional[str] = None
    gcps: Optional[dict[str, Any] | list[Any]] = None
    overlay_uri: Optional[str] = None
    georef_modified: Optional[datetime] = None


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class ImageFootprint(DBbase):
    footprint_id: int
    image_id: int
    has_detection: bool
    bbox_wsen: list[float]
    footprint_partial: bool
    area_m2: float
    area_geodesic_m2: float
    area_sigma_m2: float
    area_q05_m2: float
    area_q95_m2: float
    dem_name: str
    georef_status: str
    n_ties: int
    tie_residual_before_m: float
    rmse_h_m: float
    rmse_p50_m: float
    rmse_p90_m: float
    n_checkpoints: int
    pose_delta: list[float]
    pose_sigma: list[float]
    pose_free: list[str]
    pose_cond: float
    prior_source: str
    gcps: Any
    overlay_uri: str
    georef_modified: datetime
    created: datetime
    modified: datetime
    uuid: UUID
    footprint: Optional[Any] = None
    footprint_metadata: Optional[Any] = None

    __table__: ClassVar[sql.Identifier] = sql.Identifier("core", "image_footprints")
    __pk__: ClassVar[sql.Identifier] = sql.Identifier("footprint_id")

    # -----------------------------------------------------------------------------------------------------------------------

    class Response(BaseModel):
        model_config = ConfigDict(from_attributes=True)

        footprint_id: int
        image_id: int
        footprint: Optional[dict[str, Any]] = None
        has_detection: bool
        footprint_metadata: Optional[dict[str, Any]] = None
        bbox_wsen: list[float]
        footprint_partial: bool
        area_m2: float
        area_geodesic_m2: float
        area_sigma_m2: float
        area_q05_m2: float
        area_q95_m2: float
        dem_name: str
        georef_status: str
        n_ties: int
        tie_residual_before_m: float
        rmse_h_m: float
        rmse_p50_m: float
        rmse_p90_m: float
        n_checkpoints: int
        pose_delta: list[float]
        pose_sigma: list[float]
        pose_free: list[str]
        pose_cond: float
        prior_source: str
        gcps: Any
        overlay_uri: str
        georef_modified: datetime
        created: datetime
        modified: datetime
        uuid: UUID

        @field_validator("footprint", "footprint_metadata", mode="before")
        @classmethod
        def parse_geometry(cls, v: Any) -> Optional[dict[str, Any]]:
            if v is None or isinstance(v, dict):
                return v
            raw = bytes.fromhex(v) if isinstance(v, str) else bytes(v)
            return shapely.geometry.mapping(shapely.from_wkb(raw))

    # -----------------------------------------------------------------------------------------------------------------------

    @classmethod
    def _create(
        cls, cursor: Cursor[Self], req: CreateImageFootprintReq
    ) -> Optional[tuple[Self, list[RelationshipUpdate]]]:
        cursor.row_factory = class_row(cls)
        query = sql.SQL("""
            INSERT INTO core.image_footprints (
                image_id, footprint, has_detection, footprint_metadata, bbox_wsen,
                footprint_partial, area_m2, area_geodesic_m2, area_sigma_m2,
                area_q05_m2, area_q95_m2, dem_name, georef_status, n_ties,
                tie_residual_before_m, rmse_h_m, rmse_p50_m, rmse_p90_m,
                n_checkpoints, pose_delta, pose_sigma, pose_free, pose_cond,
                prior_source, gcps, overlay_uri, georef_modified
            )
            VALUES (
                %(image_id)s,
                CASE WHEN %(footprint_json)s IS NOT NULL THEN ST_SetSRID(ST_GeomFromGeoJSON(%(footprint_json)s), 4326) ELSE NULL END,
                %(has_detection)s,
                CASE WHEN %(footprint_metadata_json)s IS NOT NULL THEN ST_SetSRID(ST_GeomFromGeoJSON(%(footprint_metadata_json)s), 4326) ELSE NULL END,
                %(bbox_wsen)s,
                %(footprint_partial)s, %(area_m2)s, %(area_geodesic_m2)s, %(area_sigma_m2)s,
                %(area_q05_m2)s, %(area_q95_m2)s, %(dem_name)s, %(georef_status)s, %(n_ties)s,
                %(tie_residual_before_m)s, %(rmse_h_m)s, %(rmse_p50_m)s, %(rmse_p90_m)s,
                %(n_checkpoints)s, %(pose_delta)s, %(pose_sigma)s, %(pose_free)s, %(pose_cond)s,
                %(prior_source)s, %(gcps_json)s, %(overlay_uri)s, %(georef_modified)s
            )
            RETURNING *;
        """)

        cursor.execute(
            query,
            {
                **req.model_dump(),
                "image_id": req.image_ids.pkey,
                "footprint_json": json.dumps(req.footprint) if req.footprint is not None else None,
                "footprint_metadata_json": json.dumps(req.footprint_metadata) if req.footprint_metadata is not None else None,
                "gcps_json": json.dumps(req.gcps) if req.gcps is not None else None,
            },
        )

        if not (footprint := cursor.fetchone()):
            return None

        spice_updates = [
            create_spice_update(
                "image_footprint",
                footprint.uuid,
                "image",
                req.image_ids.uuid,
                "parent",
            )
        ]

        return footprint, spice_updates

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serialize(self) -> dict[str, Any]:
        return ImageFootprint.Response.model_validate(self).model_dump(mode="json")
