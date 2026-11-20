# Genera high quality crops of training data with model assisted labeling and Kmeans clustering
# Authors: Ben Koger, Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------

from uuid import uuid4

import cv2
import numpy as np
from sklearn.cluster import KMeans

from database.object_models import (
    Box,
    Image,
    Label,
    Prediction,
)
from database.object_models.base import Keyring
from database.object_models.core import (
    ActivityType,
    CreateAnnotationReq,
    CreateReviewedAreaReq,
    PredictionCrop,
)

# ---------------------------------------------------------------------------------------------------------------------------


def auto_crop(
    image: Image,
    predictions: list[Prediction],
    labels: list[Label],
    num_clusters: int = 1,
    crop_size: int = 2100,
) -> list[tuple[CreateReviewedAreaReq, list[CreateAnnotationReq]]]:
    """Automatically create crops of a given size containing all images with approved annotations

    Args:
                    image: source image that predictions were made from
                    points: List of coordinate points of the approximate center for each prediction associated with the image
                    crop_size: dimension for crop (note only square crops are currently supported)
                    num_clusters: number of centers for kmeans to determine clusters

    Returns list of crops based on original image
    """
    points = []
    centers = []
    output = []

    img = image.get_image()

    labels_ids = {label.label: label.label_id for label in labels}

    if img is None:
        raise Exception("could not get image")

    # Get centers for all predictions
    for pred in predictions:
        points.append(pred.dimensions.getCenter())

    if len(points) == 0:
        raise Exception("No predictions were provided!")
    elif len(points) == 1:
        centers.append(points[0])

    elif num_clusters == 1:
        x_min = x_max = int(points[0][0])
        y_min = y_max = int(points[0][1])

        for point in points:
            x_min = min(x_min, int(point[0]))
            x_max = max(x_max, int(point[0]))
            y_min = min(y_min, int(point[1]))
            y_max = max(y_max, int(point[1]))

        if (x_max - x_min <= 2100) and (y_max - y_min <= 2100):
            x_center = (x_min + x_max) // 2
            y_center = (y_min + y_max) // 2
            centers.append([x_center, y_center])

    elif num_clusters > 1:
        points_array = np.array(points)
        kmeans = KMeans(n_clusters=num_clusters)

        if len(points) >= num_clusters:
            kmeans.fit(points_array)
        else:
            raise Exception(
                "Cropping Failed! There were more clusters needed than points."
            )

        centers = kmeans.cluster_centers_

    points_in_crop = np.zeros(len(points))

    for crop_num, center in enumerate(centers):
        x_start = max(0, int(center[0]) - crop_size // 2)
        y_start = max(0, int(center[1]) - crop_size // 2)
        x_end = min(img.shape[1], x_start + crop_size)
        y_end = min(img.shape[0], y_start + crop_size)

        if x_end == img.shape[1]:
            x_start -= (x_start + crop_size) - img.shape[1]

        if y_end == img.shape[0]:
            y_start -= (y_start + crop_size) - img.shape[0]

        crop = CreateReviewedAreaReq(
            image_ids=Keyring(image.image_id, image.uuid),
            name=f"{image.name[0:50]}_crop_{crop_num}.JPG",
            type=ActivityType.AUTO_CROPPER,
            area_tx=x_start,
            area_ty=y_start,
            area_bx=x_end,
            area_by=y_end,
            reviewed_area_length_px=abs(y_start - y_end),
            reviewed_area_width_px=abs(x_start - x_end),
        )

        crop.set_image(img[y_start:y_end, x_start:x_end].copy())
        annotations = []

        for p_index, pred in enumerate(predictions):
            box = pred.dimensions.getPoints()

            if ((box[0] >= x_start) and (box[2] <= x_end)) and (
                (box[1] >= y_start) and (box[3] <= y_end)
            ):
                points_in_crop[p_index] += 1

                annotation = CreateAnnotationReq(
                    image_ids=Keyring(image.image_id, image.uuid),
                    type=ActivityType.AUTO_CROPPER,
                    reviewed_area_ids=None,
                    prediction_ids=Keyring(pred.pred_id, pred.uuid),
                    herd_unit_id=image.herd_unit_id,
                    label_id=labels_ids[pred.label],
                    box_tx=box[0],
                    box_ty=box[1],
                    box_bx=box[2],
                    box_by=box[3],
                    uuid=uuid4(),
                )

                annotations.append(annotation)
        output.append((crop, annotations))

    if np.all(points_in_crop >= 1):
        return output

    elif num_clusters + 1 <= len(points):
        return auto_crop(
            image=image,
            predictions=predictions,
            labels=labels,
            crop_size=crop_size,
            num_clusters=num_clusters + 1,
        )

    else:
        raise Exception("Could not generate any crops...")


# ---------------------------------------------------------------------------------------------------------------------------


def create_subcrop(
    image: Image,
    predictions: list[Prediction],
    crop_size: int = 150,
    drawBox: bool = False,
) -> list[PredictionCrop]:
    crops = []
    img = image.get_image()
    if len(predictions) == 0:
        raise Exception("Predictions cannot be zero")

    if img is None:
        raise Exception("Could not get image")

    img_height, img_width = img.shape[:2]

    for pred in predictions:
        box = pred.dimensions.top_left + pred.dimensions.bottom_right
        center_x = (box[0] + box[2]) / 2
        center_y = (box[1] + box[3]) / 2

        xmin = int(center_x - crop_size)
        ymin = int(center_y - crop_size)
        xmax = int(center_x + crop_size)
        ymax = int(center_y + crop_size)

        if xmin < 0:
            xmax -= xmin
            xmin = 0
        elif xmax > img_width:
            xmin -= xmax - img_width
            xmax = img_width

        if ymin < 0:
            ymax -= ymin
            ymin = 0
        elif ymax > img_height:
            ymin -= ymax - img_height
            ymax = img_height

        crop = PredictionCrop(
            image_id=image.image_id,
            pred_id=pred.pred_id,
            name=f"{image.name}_pred_crop_{pred.uuid}",
            score=pred.score,
            label=pred.label,
            dimensions=Box((int(xmin), int(ymax)), (int(xmax), int(ymin))),
            boundingBox=Box(
                (int(box[0] - xmin), int(box[1] - ymin)),
                (int(box[2] - xmin), int(box[3] - ymin)),
            ),
            uuid=pred.uuid,
        )
        crop.set_image(img[ymin:ymax, xmin:xmax].copy())
        crops.append(crop)

        if drawBox:
            cv2.rectangle(img, (box[0], box[1]), (box[2], box[3]), (255, 0, 0), 3)

    return crops


def cluster_windows(
    boxes: np.ndarray,
    width: int,
    height: int,
    crop_size: int,
) -> list[tuple[int, int, int, int]]:
    """auto_crop's clustering for boxes alone: square windows of crop_size around the KMeans
    centers of the boxes' centers, with clusters added until every box lies inside a window.

    Args:
                    boxes: (n, 4) boxes as left, top, right, bottom in image pixels
                    width: image width in pixels
                    height: image height in pixels
                    crop_size: side of a window in pixels

    Returns windows as left, top, right, bottom, kept inside the image
    """
    boxes = np.asarray(boxes, dtype=float).reshape(-1, 4)
    if len(boxes) == 0:
        return []

    centers = np.column_stack(
        [(boxes[:, 0] + boxes[:, 2]) / 2, (boxes[:, 1] + boxes[:, 3]) / 2]
    )
    side_x, side_y = min(crop_size, width), min(crop_size, height)

    def window(center) -> tuple[int, int, int, int]:
        left = int(min(max(0, center[0] - side_x // 2), width - side_x))
        top = int(min(max(0, center[1] - side_y // 2), height - side_y))
        return left, top, left + side_x, top + side_y

    for num_clusters in range(1, len(boxes) + 1):
        if num_clusters == 1:
            spans = boxes[:, :2].min(axis=0), boxes[:, 2:].max(axis=0)
            found = [(spans[0] + spans[1]) / 2]
        else:
            found = KMeans(n_clusters=num_clusters, n_init=10, random_state=0).fit(
                centers
            ).cluster_centers_

        windows = [window(center) for center in found]
        inside = np.zeros(len(boxes), dtype=bool)
        for left, top, right, bottom in windows:
            inside |= (
                (boxes[:, 0] >= left)
                & (boxes[:, 1] >= top)
                & (boxes[:, 2] <= right)
                & (boxes[:, 3] <= bottom)
            )
        if inside.all():
            return windows

    # A box larger than a window: one window around each box's center
    return [window(center) for center in centers]
