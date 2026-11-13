# Crops of active measurement tiles: cut from the source image when first served
# Author: Owen Martin
# ---------------------------------------------------------------------------------------------------------------------------

import io

from botocore.exceptions import ClientError
from flask import current_app

from app.extensions import base, s3
from database.errors import MeasurementBlocked
from database.object_models.core.images import Image, ReviewedArea

# ---------------------------------------------------------------------------------------------------------------------------

MISSING = ("NoSuchKey", "404", "NotFound")


def _exists(key: str) -> bool:
    try:
        s3.head_object(Bucket=current_app.config["BUCKET_NAME"], Key=key)
    except ClientError as error:
        if error.response["Error"]["Code"] in MISSING:
            return False
        raise
    return True


def ensure_crop(reviewed_area: ReviewedArea) -> bool:
    """Uploads the reviewed area's crop to its ra_key unless it is there.

    Returns:
        True when the crop was cut by this call.

    Raises:
        MeasurementBlocked: the source image is not in the bucket. The unit
        stays pending and is served again once the image is there; it is
        never skipped, since that would bias the sample.
    """
    if not reviewed_area.ra_key or _exists(reviewed_area.ra_key):
        return False

    bucket = current_app.config["BUCKET_NAME"]
    image = base.get(Image, reviewed_area.image_id)

    # The source image is not cached: consecutive units rarely share an
    # image, and a survey's worth of full frames does not fit in the cache.
    try:
        source = s3.get_object(Bucket=bucket, Key=image.img_key)["Body"].read()
    except ClientError as error:
        if error.response["Error"]["Code"] not in MISSING:
            raise
        raise MeasurementBlocked(
            f"the source image of tile {reviewed_area.name} is not in the "
            f"bucket ({image.img_key}); upload it and the tile will be served"
        ) from error
    image.set_image(source)
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
