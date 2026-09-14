# Model-Assisted Labeling & Wildlife Census Pipeline

Airial implements an end-to-end **model-assisted labeling workflow** for aerial wildlife abundance estimation. Because raw aerial survey imagery can be hundreds of megapixels per frame, annotators cannot manually scan entire flights. Instead, computer vision models assist annotators through a two-stage spatial processing and verification pipeline.

---

## 1. End-to-End Workflow

```
 [ Raw Survey Flights ]
          |
          | (1) Uploaded via Uploader UI (S3 Multipart Upload)
          v
  [ S3 Raw Imagery ]  +  [ PostgreSQL Image Records ]
          |
          | (2) Inference by Computer Vision Detection Model
          v
 [ Candidate Predictions ] (Bounding boxes, labels, confidence scores)
          |
          | (3) Auto-Cropper (crop_generator.auto_crop)
          |     - KMeans spatial clustering groups predictions
          |     - Generates 2100x2100 px ReviewedArea crops
          |     - Creates initial draft Annotations
          |     - Slices & saves crop JPGs to S3
          v
 [ ReviewedArea Crops & Draft Annotations ]
          |
          | (4) Crop-Verifier UI (/crop-verifier/)
          |     - Human annotator loads output crops needing review
          |     - Inspects draft annotations in Konva canvas
          |     - Confirms true positives, deletes false positives
          |     - Adjusts bounding boxes and corrects labels
          |     - Adds any missed animal annotations
          |     - Marks crop as reviewed (committed to DB)
          v
[ Verified Ground-Truth Annotations & Certified Census Data ]
          |
          +---> Retraining / Model Improvement Loop
          |
          +---> Abundance & Population Estimates
```

---

## 2. Stage 1: Auto-Cropper

The **Auto-Cropper** (`/auto-cropper/`) automates the spatial bundling of model predictions into manageable image crops.

### How It Works:
1. **Gather Candidate Predictions**: Queries all unreviewed model predictions for a given survey image.
2. **KMeans Spatial Clustering** (`crop_generator.auto_crop`):
   * Extracts center coordinates $(x_{center}, y_{center})$ for all predictions.
   * If all predictions comfortably fit inside a single $2100 \times 2100$ pixel window, a single bounding crop is created.
   * If predictions are dispersed across the image, KMeans clustering clusters coordinates into $k$ centers ($k = \text{num\_clusters}$).
   * If any prediction falls outside the generated crop bounds, the algorithm recursively increments $k \leftarrow k + 1$ until every candidate prediction is safely captured within a crop boundary.
3. **Artifact Creation**:
   * Creates a `ReviewedArea` record in the database (`core.reviewed_area`) with key `images/<uuid>/reviewed_area/<name>.JPG`.
   * Maps each enclosed prediction to a draft `Annotation` record (`core.annotations`).
   * Slices the $2100 \times 2100$ pixel crop from the source image and uploads it to S3.

---

## 3. Stage 2: Crop-Verifier

The **Crop-Verifier** (`/crop-verifier/`) is the human-in-the-loop verification interface where annotators review the output crops produced by the Auto-Cropper.

### Verification Workflow:
1. **Fetch Unreviewed Crops**:
   * The verifier queries `core.reviewed_area` records filtered by Herd Unit and Survey where `reviewed_by_user_id` is unset (`getReviewedArea`).
   * The corresponding crop image is loaded from S3 via presigned URL alongside its associated draft annotations.
2. **Interactive Konva Canvas**:
   * Annotators interact with the crop on an HTML5 canvas powered by `vue-konva`.
   * **Confirm / Adjust**: Drag or resize bounding boxes to tightly fit the wildlife.
   * **Reclassify**: Change the species label if a detection was misclassified.
   * **Delete**: Remove false positives (e.g., rocks, shrubs, shadows).
   * **Add**: Draw new bounding boxes for animals the CV model missed.
3. **Submission & Lock Management**:
   * Changes are queued in an undo/redo action stack in `cropVerifierStore.ts`.
   * On submission:
     * Draft annotations are updated, created, or deleted in bulk (`bulkUpdateAnnotations`, `bulkCreateAnnotations`, `bulkDeleteAnnotations`).
     * The `ReviewedArea` is marked as reviewed (`setAsReviewed`), setting `reviewed_by_user_id` and timestamp.
   * The verifier immediately transitions to the next available crop in the queue.

---

## 4. Multi-User Verification Without Conflicts

Multiple human annotators can work simultaneously on the same survey:
* Database queries lease crops to active users by tracking `opened_by_user_id` and timestamps.
* Once a user completes or releases a crop, it is either marked reviewed or returned to the pool, preventing overlapping duplicate work.
