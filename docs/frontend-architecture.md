# Frontend Architecture & Data Modeling

This document details the frontend architecture of the Airial web application (`generator_web_app/`), focusing on the data modeling layer, TypeScript abstraction, and synchronization with the backend REST API response models.

---

## 1. Architecture Overview

```
generator_web_app/
├── src/
│   ├── components/            # Reusable UI components and modal templates
│   ├── modules/
│   │   ├── api/               # Typed REST API clients for backend routes
│   │   └── stores/            # Pinia state stores (projectStore, cropperStore, etc.)
│   ├── pages/                 # Top-level route views (AutoCropper, CropVerifier, etc.)
│   ├── router.ts              # Vue Router configuration & route guards
│   ├── models/
│   │   └── index.ts           # Convenience re-export facade (`@/models`)
│   └── types/
│       ├── generatorobjects.ts # Backward-compatibility facade
│       ├── index.ts           # Main types barrel
│       └── models/            # Domain model layer mirroring airial_api/database/object_models/
│           ├── base.ts
│           ├── autocropper.ts
│           ├── verifier.ts
│           ├── core/
│           ├── project_management/
│           └── user_management/
```

The frontend is a single-page application (SPA) built on **Vue 3**, **TypeScript 5.8**, and **Vite 6**. It interfaces with the Flask REST API (`airial_api`) via JSON over HTTP.

---

## 2. Data Modeling Layer

### Design Motivation & Re-Abstraction

Previously, frontend data models and interfaces resided in a monolithic file (`generatorobjects.ts`) with missing fields and diverging contracts. The data modeling layer has been re-abstracted to **mirror the exact domain structure of the backend object models** (`airial_api/database/object_models/`).

### Key Design Principles

1. **Mirror Backend Domain Partitioning**:
   - `base.ts`: Foundational types (`PrimaryKey`, `Keyring`, `coord`, `BoxIntf`, and the `Box` class with spatial methods).
   - `core/`: High-volume survey imagery and computer vision entities (`images`, `predictions`, `reviewed_area`, `annotations`, and `ActivityType`).
   - `project_management/`: Survey hierarchy and taxonomy management (`projects`, `herd_units`, `surveys`, `labels`, `models`, `schemas`, and `ModelType`).
   - `user_management/`: Identity and access entities (`users`, `roles`, `organizations`).
   - Workflow modules: `autocropper.ts` and `verifier.ts` for batch review structures.

2. **Dual-Contract Pattern (`*Response` & Domain Class)**:
   - For each entity, an interface represents the raw JSON wire contract returned by the API's Pydantic `.Response` model (e.g., `ImageResponse`, `AnnotationResponse`).
   - A companion TypeScript class implements the interface, automatically deserializing ISO date strings into native JavaScript `Date` instances and converting raw dimensional coordinates into typed `Box` objects.

3. **Complete Backward Compatibility**:
   - All legacy interface names (`*Intf`, e.g., `ImageIntf`, `AnnotationIntf`) are preserved as type aliases pointing to their corresponding `*Response` interfaces.
   - `src/types/generatorobjects.ts` and `src/models/index.ts` re-export all domain models, allowing legacy imports (`from "@/types/generatorobjects"`) and modern imports (`from "@/types/models"` or `from "@/models"`) to work interchangeably.

---

## 3. Domain Model Specifications

### 1. Base Layer (`types/models/base.ts`)

| Type / Class | Description | Fields / Methods |
| :--- | :--- | :--- |
| `PrimaryKey` | Dual-ID identifier | `number \| string` |
| `Keyring` | Dual-ID pair | `pkey: number`, `uuid: string` |
| `coord` | 2D Point | `x: number`, `y: number` |
| `BoxIntf` | Bounding Box Wire Interface | `top_left: coord`, `bottom_right: coord` |
| `Box` | Spatial Utility Class | Coordinates with `getCenter()`, `getPoints()`, `getWidth()`, `getHeight()`, `calcIou()`, `serialize()`, `to_dict()` |
| `konvaBoxConf` | Konva Rendering Spec | Canvas bounding box layout & transform config |
| `tempRect` | Interactive Drawing Box | Temporary drag coordinates during manual box creation |
| `CGObject` | Generic Selectable Entity | Duck-typed selector interface for administrative dropdowns |

### 2. Core Domain (`types/models/core/`)

| Model | Response Interface | Key Attributes | Notes |
| :--- | :--- | :--- | :--- |
| **`ActivityType`** | *(Enum)* | `'auto cropper'`, `'active measurement'` | Matches `core.activity_type` PostgreSQL enum |
| **`Image`** | `ImageResponse` | `image_id`, `herd_unit_id`, `survey_id`, `name`, `img_key`, `in_training`, `crops_generated`, `image_length_px`, `image_width_px`, `uuid`, `created`, `modified` | Optional spatial attributes: `area`, `viewshed_polygon`, `has_detection`, `dem_name`, `bbox_wsen` |
| **`ReviewedArea`** | `ReviewedAreaResponse` | `reviewed_area_id`, `image_id`, `type`, `name`, `dimensions`, `reviewed_area_length_px`, `reviewed_area_width_px`, `ra_key`, `uuid`, `url`, `created`, `modified` | `dimensions` is instantiated as a `Box` |
| **`PredictionCrop`**| `PredictionCropResponse`| `image_id`, `pred_id`, `name`, `score`, `label`, `approved`, `dimensions`, `boundingBox`, `uuid`, `url`, `drawBox` | Ephemeral crop representation for chip review |
| **`Annotation`** | `AnnotationResponse` | `annotation_id`, `label_id`, `image_id`, `type`, `herd_unit_id`, `dimensions`, `uuid`, `created`, `modified` | `dimensions` is instantiated as a `Box` |
| **`Prediction`** | `PredictionResponse` | `pred_id`, `score`, `label`, `dimensions`, `uuid`, `image_id`, `model_id`, `created`, `modified` | `dimensions` is instantiated as a `Box` |

### 3. Project Management Domain (`types/models/project_management/`)

| Model | Response Interface | Key Attributes | Notes |
| :--- | :--- | :--- | :--- |
| **`Project`** | `ProjectResponse` | `project_id`, `name`, `uuid`, `created`, `modified` | Top-level project grouping |
| **`HerdUnit`** | `HerdUnitResponse` | `herd_unit_id`, `name`, `uuid`, `created`, `modified` | Geographic wildlife unit |
| **`Survey`** | `SurveyResponse` | `survey_id`, `survey_date`, `name`, `additional_info`, `uuid`, `created`, `modified` | Aerial flight campaign |
| **`Label`** | `LabelResponse` | `label_id`, `schema_id`, `label`, `name`, `image_link`, `color`, `uuid`, `created`, `modified` | Classification taxonomy entry |
| **`ModelType`** | *(Enum)* | `'detection'`, `'regression'`, `'depth estimation'` | Matches `projectmanagement.model_type` PostgreSQL enum |
| **`Model`** | `ModelResponse` | `model_id`, `schema_id`, `name`, `model_type`, `uuid`, `created`, `modified` | Computer vision model metadata |
| **`Schema`** | `SchemaResponse` | `schema_id`, `name`, `uuid`, `created`, `modified` | Label taxonomy schema |

### 4. User Management Domain (`types/models/user_management/`)

| Model | Response Interface | Key Attributes | Notes |
| :--- | :--- | :--- | :--- |
| **`Organization`** | `OrganizationResponse` | `organization_id`, `name`, `logo_url`, `uuid`, `created`, `modified` | Multi-tenant tenant entity |
| **`Role`** | `RoleResponse` | `role_id`, `name`, `uuid`, `created`, `modified` | Access control role |
| **`User`** | `UserResponse` | `user_id`, `username`, `email`, `status`, `last_login`, `locale`, `default_org_id`, `roles`, `uuid`, `created`, `modified` | User profile & session attributes |

### 5. Workflow Models

* **`autocropper.ts`**:
  * `autoCropperBatch`: Image and prediction matrix (`images: Image[]`, `predictions: Prediction[][]`, `predictionCrops: PredictionCrop[][]`).
  * `AutoCropperBatchQuery`: Query parameters for batch retrieval.
  * `AutoCropReq`: Submission payload for K-Means auto-cropping.
* **`verifier.ts`**:
  * `cropVerifierBatch`: Active reviewed areas mapped to canvas state, Konva box configurations, and draft annotations.
  * `ApproveAnnotationsReq`: Batch verification and submission payload.

---

## 4. Import Conventions

Developers and agents can import models using any of the following standard patterns:

```typescript
// Recommended: Domain-scoped imports
import { Image, ReviewedArea, Annotation } from "@/types/models/core";
import { Project, Survey, Label } from "@/types/models/project_management";
import { User, Organization } from "@/types/models/user_management";

// General Barrel import
import { Image, Project, User, Box } from "@/types/models";

// Top-level models facade
import { Image, Project, User } from "@/models";

// Legacy import (Fully backward-compatible)
import { Image, type ImageIntf, Box } from "@/types/generatorobjects";
```
