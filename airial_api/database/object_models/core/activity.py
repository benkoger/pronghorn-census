# Enum definition for ActivityType
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------

"""Activity type enum definitions for core operations."""

from enum import StrEnum


class ActivityType(StrEnum):
    """Activity type enumeration for automated actions."""

    AUTO_CROPPER = "auto cropper"
    ACTIVE_MEASUREMENT = "active measurement"
