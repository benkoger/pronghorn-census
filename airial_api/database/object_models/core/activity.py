"""Activity type enum definitions for core operations."""

# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------

from enum import StrEnum


class ActivityType(StrEnum):
    """Activity type enumeration for automated actions."""

    AUTO_CROPPER = "auto cropper"
    ACTIVE_MEASUREMENT = "active measurement"
