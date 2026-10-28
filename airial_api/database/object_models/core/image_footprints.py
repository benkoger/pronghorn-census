# Class definition for ImageFootprint objects in the database
# Authors: Michael B. Lance, Antigravity
# ---------------------------------------------------------------------------------------------------------------------------
"""Image footprint database models and schemas."""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar, Self
from uuid import UUID

import psycopg.sql as sql
import shapely
import shapely.geometry
from authzed.api.v1 import RelationshipUpdate
from psycopg import Cursor
from psycopg.rows import class_row
from pydantic import BaseModel, ConfigDict, field_validator

from database.object_models.base import DBbase, Keyring, create_spice_update

# ---------------------------------------------------------------------------------------------------------------------------


class CreateImageFootprintReq(BaseModel):
    """Request schema for creating an image footprint."""

    image_ids: Keyring
    footprint: dict[str, Any] | None = None
    has_detection: bool = False
    footprint_metadata: dict[str, Any] | None = None
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
    """Request schema for updating an image footprint."""

    footprint: dict[str, Any] | None = None
    has_detection: bool | None = None
    footprint_metadata: dict[str, Any] | None = None
    bbox_wsen: list[float] | None = None
    footprint_partial: bool | None = None
    area_m2: float | None = None
    area_geodesic_m2: float | None = None
    area_sigma_m2: float | None = None
    area_q05_m2: float | None = None
    area_q95_m2: float | None = None
    dem_name: str | None = None
    georef_status: str | None = None
    n_ties: int | None = None
    tie_residual_before_m: float | None = None
    rmse_h_m: float | None = None
    rmse_p50_m: float | None = None
    rmse_p90_m: float | None = None
    n_checkpoints: int | None = None
    pose_delta: list[float] | None = None
    pose_sigma: list[float] | None = None
    pose_free: list[str] | None = None
    pose_cond: float | None = None
    prior_source: str | None = None
    gcps: dict[str, Any] | list[Any] | None = None
    overlay_uri: str | None = None
    georef_modified: datetime | None = None


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class ImageFootprint(DBbase):
    """Database representation of an image footprint."""

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
    footprint: Any | None = None
    footprint_metadata: Any | None = None

    __table__: ClassVar[sql.Identifier] = sql.Identifier("core", "image_footprints")
    __pk__: ClassVar[sql.Identifier] = sql.Identifier("footprint_id")
    __parent_table__: ClassVar[sql.Identifier] = sql.Identifier("core", "images")
    __parent_fk__: ClassVar[sql.Identifier] = sql.Identifier("image_id")

    # -----------------------------------------------------------------------------------------------------------------------

    class Response(BaseModel):
        """Response schema for an image footprint."""

        model_config = ConfigDict(from_attributes=True)

        footprint_id: int
        image_id: int
        footprint: dict[str, Any] | None = None
        has_detection: bool
        footprint_metadata: dict[str, Any] | None = None
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
        def parse_geometry(cls, v: Any) -> dict[str, Any] | None:
            """Parse WKB/GeoJSON geometry into a dictionary."""
            if v is None or isinstance(v, dict):
                return v
            raw = bytes.fromhex(v) if isinstance(v, str) else bytes(v)
            return shapely.geometry.mapping(shapely.from_wkb(raw))

    # -----------------------------------------------------------------------------------------------------------------------

    @classmethod
    def _create(cls, cursor: Cursor[Self], req: CreateImageFootprintReq) -> tuple[Self, list[RelationshipUpdate]] | None:
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
                CASE
                    WHEN %(footprint_json)s IS NOT NULL THEN ST_SetSRID(ST_GeomFromGeoJSON(%(footprint_json)s), 4326)
                    ELSE NULL
                END,
                %(has_detection)s,
                CASE
                    WHEN %(footprint_metadata_json)s IS NOT NULL
                    THEN ST_SetSRID(ST_GeomFromGeoJSON(%(footprint_metadata_json)s), 4326)
                    ELSE NULL
                END,
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
                "footprint_metadata_json": (
                    json.dumps(req.footprint_metadata) if req.footprint_metadata is not None else None
                ),
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
        """Serialize image footprint to a dictionary."""
        return ImageFootprint.Response.model_validate(self).model_dump(mode="json")
