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
    AbortMultiPartUploadReq,
    CompleteMultiPartUploadReq,
    CreateReviewedAreaPresignedGetReq,
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
from .proposal_generations import CreateProposalGenerationReq, ProposalGeneration

__all__ = [
    "AbortMultiPartUploadReq",
    "ActivityType",
    "AmUnit",
    "Annotation",
    "AnnotationsReviewedArea",
    "Box",
    "BulkCreateAnnotationReq",
    "BulkDeleteAnnotationsReq",
    "BulkUpdateAnnotationsReq",
    "CompleteMultiPartUploadReq",
    "CreateReviewedAreaPresignedGetReq",
    "CreateAmUnitReq",
    "CreateAnnotationReq",
    "CreateImageFootprintReq",
    "CreateImageMetadataReq",
    "CreateImageMultiPartUploadReq",
    "CreateImageReq",
    "CreatePredictionCropReq",
    "CreatePredictionReq",
    "CreatePresignedPutReq",
    "CreateProposalGenerationReq",
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
    "ProposalGeneration",
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
