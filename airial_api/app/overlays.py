# Image overlays for the survey map: an image drawn onto the ground
# Author: Owen Martin
# ---------------------------------------------------------------------------------------------------------------------------
# The overlay of an image is the image resampled onto a longitude/latitude grid
# over its footprint's bounding box, transparent where the image does not
# reach. It is drawn from the source image and the footprint's ground control
# points the first time it is asked for and stored in the bucket next to the
# image's tiles; the footprint's overlay_uri then holds its key.
# ---------------------------------------------------------------------------------------------------------------------------

from math import cos, radians
from typing import Any

import cv2
import numpy as np
import shapely
from flask import current_app
from scipy.interpolate import LinearNDInterpolator

from app.extensions import base, s3
from database.errors import ObjectNotFound
from database.modules import surveymap
from database.object_models.core.images import Image

# ---------------------------------------------------------------------------------------------------------------------------

# The file name changes when the drawing does, so stored overlays are redrawn.
OVERLAY_FILE = "ground.webp"
OVERLAY_WIDTH_PX = 1024
# The source is decoded at a quarter of its size: ample for a map overlay.
SOURCE_REDUCTION = 4
WEBP_QUALITY = 85
URL_SECONDS = 3600

# ---------------------------------------------------------------------------------------------------------------------------


def overlay_key(image: Image) -> str:
    """Returns the bucket key of the image's overlay."""
    return f"images/{image.uuid}/overlay/{OVERLAY_FILE}"


def render(
    image_data: bytes,
    gcps: list[list[float]],
    bbox_wsen: list[float],
    footprint_wkb: bytes | None = None,
) -> bytes:
    """Draws the image over its bounding box.

    The ground control's triangulation reaches the convex hull of the points,
    past the footprint where the footprint is concave, so the drawing is cut
    to the footprint when it is given.

    Args:
        image_data: The encoded source image.
        gcps: Ground control points as (row, column, longitude, latitude) in
            pixels of the full-size image.
        bbox_wsen: The bounding box: west, south, east, north.
        footprint_wkb: The footprint's outline as WKB.

    Returns:
        A WebP with transparency outside the image.

    Raises:
        ValueError: The image could not be decoded or the overlay encoded.
    """
    source = cv2.imdecode(
        np.frombuffer(image_data, dtype=np.uint8), cv2.IMREAD_REDUCED_COLOR_4
    )
    if source is None:
        raise ValueError("could not decode the source image")

    points = np.asarray(gcps, dtype=float).reshape(-1, 4)
    points = points[np.isfinite(points).all(axis=1)]

    west, south, east, north = bbox_wsen
    width = OVERLAY_WIDTH_PX
    # Degrees of longitude are shorter than degrees of latitude.
    stretch = cos(radians((north + south) / 2))
    height = max(1, round(width * (north - south) / ((east - west) * stretch)))

    lon, lat = np.meshgrid(
        np.linspace(west, east, width), np.linspace(north, south, height)
    )

    # Ground position to source pixel (column, row), undefined off the image.
    pixel = LinearNDInterpolator(points[:, [2, 3]], points[:, [1, 0]])(lon, lat)
    covered = np.isfinite(pixel).all(axis=2)
    if footprint_wkb:
        outline = shapely.from_wkb(bytes(footprint_wkb))
        covered &= shapely.contains_xy(
            outline, lon.ravel(), lat.ravel()
        ).reshape(lon.shape)
    pixel = np.nan_to_num(pixel, nan=-1.0) / SOURCE_REDUCTION

    drawn = cv2.remap(
        source,
        pixel[..., 0].astype(np.float32),
        pixel[..., 1].astype(np.float32),
        interpolation=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )

    overlay = np.dstack([drawn, np.where(covered, 255, 0).astype(np.uint8)])
    ok, encoded = cv2.imencode(
        ".webp", overlay, [cv2.IMWRITE_WEBP_QUALITY, WEBP_QUALITY]
    )
    if not ok:
        raise ValueError("could not encode the overlay")
    return encoded.tobytes()


def get_overlay(image: Image) -> dict[str, Any]:
    """Returns the image's overlay, drawing and storing it first if needed.

    Args:
        image: The image.

    Returns:
        A temporary URL of the overlay and the bounds it covers, as
        [[south, west], [north, east]].

    Raises:
        ObjectNotFound: The image has no footprint, or none with ground
            control to draw with.
    """
    source = base.execute(surveymap.get_overlay_source, image.image_id)
    if source is None:
        raise ObjectNotFound("ImageOverlay", str(image.uuid))

    bucket, key = current_app.config["BUCKET_NAME"], overlay_key(image)

    # Not drawn yet, or drawn by an earlier version of the drawing.
    if source["overlay_uri"] != key:
        image_data = s3.get_object(Bucket=bucket, Key=image.img_key)[
            "Body"
        ].read()
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=render(
                image_data,
                source["gcps"],
                source["bbox_wsen"],
                source["footprint"],
            ),
            ContentType="image/webp",
        )
        base.execute(surveymap.set_overlay_key, source["footprint_id"], key)

    west, south, east, north = source["bbox_wsen"]
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=URL_SECONDS,
    )
    return {"url": url, "bounds": [[south, west], [north, east]]}
