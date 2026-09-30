# Crops of detections for the survey map: the image around a box, with the box drawn
# Author: Owen Martin
# ---------------------------------------------------------------------------------------------------------------------------

import cv2
import numpy as np
from flask import current_app

from app.extensions import base, s3
from database.object_models.core.images import Image

# ---------------------------------------------------------------------------------------------------------------------------

MARGIN_PX = 100  # around the box's center, each way
LINE_PX = 2
COLORS = {"annotated": (0, 215, 255), "estimated": (0, 136, 255)}  # BGR, the map's colors
WEBP_QUALITY = 85


def detection_crop(image: Image, box: list[int], kind: str) -> bytes:
    """
    Returns a WebP crop of `image` centered on `box` (tx, ty, bx, by in image pixels) with the
    box drawn in the color of `kind`. The image is read from the bucket each time.
    """
    image.set_image(
        s3.get_object(Bucket=current_app.config["BUCKET_NAME"], Key=image.img_key)["Body"].read()
    )
    if (pixels := image.get_image()) is None:
        raise Exception(f"could not read image {image.uuid}")

    height, width = pixels.shape[:2]
    tx, ty, bx, by = box
    cx, cy = (tx + bx) // 2, (ty + by) // 2
    x0, y0 = max(0, cx - MARGIN_PX), max(0, cy - MARGIN_PX)
    x1, y1 = min(width, cx + MARGIN_PX), min(height, cy + MARGIN_PX)

    crop = np.ascontiguousarray(pixels[y0:y1, x0:x1])
    image.delete_image()

    cv2.rectangle(
        crop, (tx - x0, ty - y0), (bx - x0, by - y0), COLORS.get(kind, COLORS["estimated"]), LINE_PX
    )
    ok, encoded = cv2.imencode(".webp", crop, [cv2.IMWRITE_WEBP_QUALITY, WEBP_QUALITY])
    if not ok:
        raise Exception("could not encode the crop")
    return encoded.tobytes()
