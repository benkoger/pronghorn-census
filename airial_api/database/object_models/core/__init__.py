"""Core database object models and schemas."""

from database.object_models.base import Box

from .activity import ActivityType
from .am_units import (
    AmUnit,
    CreateAmUnitReq,
    UpdateAmUnitReq,
)
from .annotations import (
    Annotation,
    BulkCreateAnnotationReq,
    BulkDeleteAnnotationsReq,
    BulkUpdateAnnotationsReq,
    CreateAnnotationReq,
    DeleteAnnotationReq,
    UpdateAnnotationReq,
)
from .core_bindings import (
    AnnotationsReviewedArea,
)
from .image_footprints import (
    CreateImageFootprintReq,
    ImageFootprint,
    UpdateImageFootprintReq,
)
from .image_metadata import (
    CreateImageMetadataReq,
    ImageMetadata,
    UpdateImageMetadataReq,
)
from .images import (
    AbortMulitPartUploadReq,
    CompleteMultiPartUploadReq,
    CrateReviewedAreaPresignedGetReq,
    CreateImageMultiPartUploadReq,
    CreateImageReq,
    CreatePredictionCropReq,
    CreatePresignedPutReq,
    CreateReviewedAreaReq,
    Image,
    ImageMixin,
    PredictionCrop,
    PresignedImageGetReq,
    RAQuery,
    ReviewedArea,
    UpdateImageReq,
    UpdateReviewedAreaReq,
)
from .predictions import (
    CreatePredictionReq,
    Prediction,
    PredictionQuery,
    UpdatePredictionReq,
)

__all__ = [
    "AbortMulitPartUploadReq",
    "ActivityType",
    "AmUnit",
    "Annotation",
    "AnnotationsReviewedArea",
    "Box",
    "BulkCreateAnnotationReq",
    "BulkDeleteAnnotationsReq",
    "BulkUpdateAnnotationsReq",
    "CompleteMultiPartUploadReq",
    "CrateReviewedAreaPresignedGetReq",
    "CreateAmUnitReq",
    "CreateAnnotationReq",
    "CreateImageFootprintReq",
    "CreateImageMetadataReq",
    "CreateImageMultiPartUploadReq",
    "CreateImageReq",
    "CreatePredictionCropReq",
    "CreatePredictionReq",
    "CreatePresignedPutReq",
    "CreateReviewedAreaReq",
    "DeleteAnnotationReq",
    "Image",
    "ImageFootprint",
    "ImageMetadata",
    "ImageMixin",
    "Prediction",
    "PredictionCrop",
    "PredictionQuery",
    "PresignedImageGetReq",
    "RAQuery",
    "ReviewedArea",
    "UpdateAmUnitReq",
    "UpdateAnnotationReq",
    "UpdateImageFootprintReq",
    "UpdateImageMetadataReq",
    "UpdateImageReq",
    "UpdatePredictionReq",
    "UpdateReviewedAreaReq",
]
