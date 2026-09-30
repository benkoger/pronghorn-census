# Crops of active measurement tiles: cut from the source image the first time a tile is served
# Author: Owen Martin
# ---------------------------------------------------------------------------------------------------------------------------

import io

from botocore.exceptions import ClientError
from flask import current_app

from app.extensions import base, s3
from database.object_models.core.images import Image, ReviewedArea

# ---------------------------------------------------------------------------------------------------------------------------


def _exists(key: str) -> bool:
    try:
        s3.head_object(Bucket=current_app.config["BUCKET_NAME"], Key=key)
    except ClientError as error:
        if error.response["Error"]["Code"] in ("NoSuchKey", "404", "NotFound"):
            return False
        raise
    return True


def ensure_crop(reviewed_area: ReviewedArea) -> bool:
    """
    Uploads the reviewed area's crop to its ra_key unless it is already there.
    Returns True when the crop was cut by this call.
    """
    if not reviewed_area.ra_key or _exists(reviewed_area.ra_key):
        return False

    bucket = current_app.config["BUCKET_NAME"]
    image = base.get(Image, reviewed_area.image_id)

    # The source image is not cached: consecutive units rarely share an image, and a survey's
    # worth of full frames does not fit in the cache.
    image.set_image(s3.get_object(Bucket=bucket, Key=image.img_key)["Body"].read())
    if (pixels := image.get_image()) is None:
        raise Exception(f"could not read image {image.uuid}")

    reviewed_area.set_image(
        pixels[
            reviewed_area.area_ty : reviewed_area.area_by,
            reviewed_area.area_tx : reviewed_area.area_bx,
        ].copy()
    )

    s3.put_object(
        Bucket=bucket,
        Key=reviewed_area.ra_key,
        Body=io.BytesIO(reviewed_area.serve(".JPG")),
        ContentType="image/jpeg",
    )
    reviewed_area.delete_image()
    image.delete_image()
    return True
