from typing import List, Any
from uuid import UUID

from pydantic import BaseModel, model_validator

from .core import Prediction


class AutoCropperBatchQuery(BaseModel):
    survey_id: UUID
    herd_unit_id: UUID
    model_id: UUID
    label: List[int]
    batch_size: int
    min_confidence: float


class AutoCropReq(BaseModel):
    image_id: UUID
    predictions: List[Prediction]
    label_ids: List[UUID]

    @model_validator(mode="before")
    @classmethod
    def flatten_prediction_dimensions(cls, data: Any) -> Any:
        if isinstance(data, dict) and "predictions" in data:
            flattened_predictions = []

            for pred in data["predictions"]:
                # If it's already an object, skip
                if not isinstance(pred, dict):
                    flattened_predictions.append(pred)
                    continue

                # Extract coordinates from the incoming nested JSON format
                dims = pred.get("dimensions", {})
                top_left = dims.get("top_left", [0, 0])
                bottom_right = dims.get("bottom_right", [0, 0])

                # Inject the flat variables the dataclass init expects
                pred["box_tx"] = top_left[0]
                pred["box_ty"] = top_left[1]
                pred["box_bx"] = bottom_right[0]
                pred["box_by"] = bottom_right[1]

                # Set a fallback default for DB fields missing in your json payload
                if "reviewed_by_user_id" not in pred:
                    pred["reviewed_by_user_id"] = 0

                flattened_predictions.append(pred)

            data["predictions"] = flattened_predictions
        return data
