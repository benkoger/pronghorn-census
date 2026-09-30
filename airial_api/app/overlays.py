# Image overlays for the survey map: an image drawn onto the ground, built when first asked for
# Author: Owen Martin
# ---------------------------------------------------------------------------------------------------------------------------
# The overlay of an image is the image resampled onto a longitude/latitude grid over its
# footprint's bounding box, transparent where the image does not reach. It is built from the
# source image and the footprint's ground control points the first time it is asked for, and
# stored next to the image in the bucket. The footprint's overlay_uri then holds its key.
# ---------------------------------------------------------------------------------------------------------------------------

from math import cos, radians
from typing import Any

import cv2
import numpy as np
from flask import current_app
from scipy.interpolate import LinearNDInterpolator

from app.extensions import base, s3
from database.errors import ObjectNotFound
from database.modules import surveymap
from database.object_models.core.images import Image

# ---------------------------------------------------------------------------------------------------------------------------

OVERLAY_WIDTH_PX = 1024
SOURCE_REDUCTION = 4  # the source is decoded at a quarter of its size: ample for a map overlay
WEBP_QUALITY = 85
URL_SECONDS = 3600

# ---------------------------------------------------------------------------------------------------------------------------


STORED_PREFIX = "images/"


def _key(image: Image) -> str:
    return f"{STORED_PREFIX}{image.uuid}/overlay/ground.webp"


def render(image_data: bytes, gcps: list[list[float]], bbox_wsen: list[float]) -> bytes:
    """
    Returns the image drawn over its bounding box as a WebP with transparency. `gcps` are
    (row, column, longitude, latitude) in pixels of the full-size image.
    """
    source = cv2.imdecode(np.frombuffer(image_data, dtype=np.uint8), cv2.IMREAD_REDUCED_COLOR_4)
    if source is None:
        raise Exception("could not decode the source image")

    points = np.asarray(gcps, dtype=float)
    points = points[np.isfinite(points).all(axis=1)]

    west, south, east, north = bbox_wsen
    width = OVERLAY_WIDTH_PX
    stretch = cos(radians((north + south) / 2))  # degrees of longitude are shorter than latitude
    height = max(1, round(width * (north - south) / ((east - west) * stretch)))

    lon, lat = np.meshgrid(
        np.linspace(west, east, width),
        np.linspace(north, south, height),
    )

    # ground position -> source pixel (column, row), undefined outside the image
    pixel = LinearNDInterpolator(points[:, [2, 3]], points[:, [1, 0]])(lon, lat)
    covered = np.isfinite(pixel).all(axis=2)
    pixel = np.nan_to_num(pixel, nan=-1.0) / SOURCE_REDUCTION

    drawn = cv2.remap(
        source,  # type: ignore[call-overload]  # the stubs do not admit an integer image
        pixel[..., 0].astype(np.float32),
        pixel[..., 1].astype(np.float32),
        interpolation=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )

    overlay = np.dstack([drawn, np.where(covered, 255, 0).astype(np.uint8)])
    ok, encoded = cv2.imencode(".webp", overlay, [cv2.IMWRITE_WEBP_QUALITY, WEBP_QUALITY])
    if not ok:
        raise Exception("could not encode the overlay")

    return encoded.tobytes()


def get_overlay(image: Image) -> dict[str, Any]:
    """
    Returns the overlay of the image as a temporary URL and the bounds it covers
    ([[south, west], [north, east]]), building and storing it first when it is not stored.
    """
    source = base.execute(surveymap.get_overlay_source, image.image_id)
    if source is None:
        raise ObjectNotFound("ImageOverlay", str(image.uuid))

    bucket, key = current_app.config["BUCKET_NAME"], source["overlay_uri"]

    if not str(key or "").startswith(STORED_PREFIX):
        key = _key(image)
        image_data = s3.get_object(Bucket=bucket, Key=image.img_key)["Body"].read()
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=render(image_data, source["gcps"], source["bbox_wsen"]),
            ContentType="image/webp",
        )
        base.execute(surveymap.set_overlay_key, source["footprint_id"], key)

    west, south, east, north = source["bbox_wsen"]
    url = s3.generate_presigned_url(
        "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=URL_SECONDS
    )

    return {"url": url, "bounds": [[south, west], [north, east]]}
