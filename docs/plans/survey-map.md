# Feature Specification: Survey Map and Abundance Terms

Branch `survey-map` off `origin/indev`, after the active measurement module merged.

## 1. Overview

This PR adds the survey map and the terms that turn the running count into an abundance. The
map draws a survey's image footprints, the animals annotated on the reviewed tiles, and the
detector's boxes standing in for the animals the estimate expects on the tiles not reviewed
yet; any image can be drawn onto the ground over satellite imagery. The survey terms
(habitable area, surveyed area, the transects, the overlap between images and the
representation of the transects) are posted once per measurement and stored on its row; from
then on the estimate carries the abundance over the herd unit with its uncertainty by source.

## 2. Goals

**User-facing.**
- A Survey Map page, from the nav, shows the selected survey's footprints coloured by state
  (a tile reviewed, a detection, neither), the annotated and estimated detections, and the
  running estimate and abundance under the same masking as the Abundance Estimation page.
- The detections are drawn as one circle per tile and kind. Tiles of different images with
  detections within 15 m of each other, where another image covers them, show the same
  animals and are joined into one circle, annotated when any of them was reviewed. A
  circle's area is proportional to its animals after the overlap weights (each detection
  weighs 1 / the images covering it), so joining changes the drawing, not the total.
- Clicking an image shows its annotated animals, across all its tiles, zoomed in crops
  grouped as the auto cropper groups predictions, and offers to draw it onto the ground.
  Clicking a circle's estimated detections shows the image around each of the detector's
  boxes, and its annotated detections the crops holding them.
- Once an image is drawn onto the ground, "Show pronghorn in image" draws its detections'
  boxes on it. Each box's corners are placed through the image's ground control points, the
  mapping the overlay is drawn with, so the boxes lie on the animals of the drawn image.
  The detections carry the corners: the estimated boxes' are placed with the boxes, once
  per generation, and the annotated boxes' with their positions.
- The Abundance Estimation page shows an Overall Abundance card once the terms are posted and
  the figures are unmasked: the abundance and its interval over the habitable area, the
  animals in the surveyed area after the overlap factor, and each source of uncertainty alone.
- The preparation card lists the survey terms as an optional sixth step: reviewing can start
  without them, and the estimate is then a count without an abundance.

**Engineering.**
- The terms are durable on the measurement row (`active_measurements.terms`, JSONB, the
  `SurveyTerms` as a plain object) with `am_terms_<uuid>` in Valkey in front of it, rebuilt
  from the row on a miss.
- One detector score serves the drafts, the map and the terms: the measurement's draft
  threshold. The detector's boxes at or above it number the regressor's expected total, so
  before review they stand for the animals, and during review the map picks from them.
- The boxes at the draft threshold, placed on the ground through each image's ground control
  points, take seconds to place, so they are placed once per generation and kept under
  `am_boxes_<uuid>` as msgpacked `PlacedBoxes`, dropped when a generation is posted.
- The map and the abundance agree on where the animals are: one function (`surveymap.shown`)
  decides which animals the map shows at the estimated count, and the abundance takes its
  overlap factor and representation from those same animals.
- The estimate's count, interval and density stay the estimator's. The abundance is an added
  block, `abundance`, null until the terms are posted and a reviewed tile gives a positive
  count.
- An image's overlay is drawn from the source image the first time it is asked for and stored
  in the bucket at `images/<image uuid>/overlay/ground.webp`; the footprint's `overlay_uri`
  then holds that key.
- Estimated detections' crops come from the images router's prediction crops, one request
  per tile and image.
- An image's annotated animals come from `GET /survey-maps/image-crops`: the measurement's
  annotated boxes on the image, grouped by `crop_generator.cluster_windows` (the auto
  cropper's clustering: KMeans on the box centers, clusters added until every box lies in
  a 300 px window, the prediction crops' size), each window cut from the source image and returned inline as a WebP
  with the boxes inside it. The source image is cached under its uuid as the prediction
  crops cache it.

## 3. Core Concepts

- **Footprint.** An image's outline on the ground with its ground control points, a grid of
  (row, column, longitude, latitude) over the image, posted by the survey preparation tooling.
- **Placing a box.** The box's center in image pixels, interpolated through its image's ground
  control points to longitude and latitude.
- **Overlap weight.** An animal placed from one image and inside the latest footprints of n
  other images has weight 1 / (1 + n); the overlap factor is the mean weight
  (`ais.overlap.coverage_weights`). The footprints have no spatial index, so the survey's are
  read once per computation and searched with a shapely STRtree.
- **Shown animals.** At an estimated count N: the annotations of the measurement's label on its
  reviewed tiles, then N minus those, rounded, of the placed boxes on tiles not reviewed.
  Unreviewed tiles are visited in descending expected count, each giving up to ceil(expected
  count) of its highest scoring boxes; the rest are the highest scoring boxes left. When the
  boxes run out, the remainder is reported as unplaced.
- **Survey terms.** The habitable area (posted), the surveyed area and each transect's area
  (the union of the footprints, by `image_metadata.transect_id`), the surveyed area's
  standard deviation and draws (posted, from the georeferencing), and the overlap factor and
  representation of the placed boxes. Posted again, they replace the earlier ones.
- **Live abundance.** The overlap factor and the representation recomputed from the shown
  animals at the running count, then `overall_abundance` with the terms as prepared reported
  beside them.

**Invariants.**
- The map, the abundance and the drafts use the same detector score for a generation.
- A reviewed tile's boxes are never estimated: its annotations carry its animals.
- The terms on the row and in the cache are the same object; the cache is never the only copy.

## 4. Edge Cases

| Scenario | Expected behaviour |
| :--- | :--- |
| Detections for a survey without a measurement, or without a proposal | 200 with no detections and a null threshold. |
| Detections before any review | No annotated or estimated detections: the estimate has no count. |
| The estimate exceeds the boxes left to place | The rest are reported as `unplaced`. |
| An annotation on an image without a footprint | Counted as annotated, not drawn. |
| Overlay of an image without a footprint, or whose footprint has no ground control | 404. |
| Overlay asked for twice | Drawn and stored once; the second request returns the stored key's URL. |
| Terms posted before generation 0 | 409: no proposal. |
| Terms when no image has a transect | 409. |
| Terms with a habitable area at or below zero | 409 from `SurveyTerms`. |
| Terms posted twice | The second replaces the first, on the row and in the cache. |
| Valkey restarted after the terms were posted | `load_terms` rebuilds them from the row. |
| A new generation posted | `am_threshold_<uuid>` and `am_boxes_<uuid>` are dropped and recomputed at the new score. |
| Terms posted, no tile reviewed | The estimate's `abundance` is null. |

## 5. Acceptance Criteria

**Real survey, 2026-11-19, on the local stack with the PR527 centennial load (4,772
footprints, 12 transects, 38,176 tiles, 61 reviewed).**
- [x] `POST /terms` with the herd unit's habitable area (2,849 km²): 868 boxes placed, the
      surveyed area 123.9 km², overlap factor 0.775, representation ±6.6% over 12 transects,
      in 7 s.
- [x] The estimate carries the abundance with a live overlap factor of 0.775, in 0.8 s once
      the boxes are placed.
- [x] Footprints: 4,772 features in 1.6 s. Detections: 75 annotated and 713 estimated, none
      unplaced, in 0.6 s with the boxes cached.
- [x] An image's overlay drawn and stored in the bucket, returned as a presigned URL.
- [x] The status reports six steps, the sixth optional and done, and `ready` true.

**Tests, `airial_api/testing/test_survey_maps.py`.** In the shape of
`test_active_measurements.py`, whose fixtures it shares (`MeasurementFixtures`). The sample
image is georeferenced inside the transaction: its earlier footprints deleted, a footprint
over a small box of ground with a 5 x 5 grid of ground control, and metadata on transect 0.
- [x] Footprints: the image's feature with its bounds and tiles; 404 for an unknown survey.
- [x] Detections: empty without a measurement or a proposal; after a review with an added
      annotation, the annotated detections on the image inside its footprint, the estimated
      ones at or above the threshold, and annotated plus estimated plus unplaced equal to the
      count; an annotation off the ground counted and not drawn.
- [x] Overlays: 404 without a footprint and without ground control; drawn once, stored with
      transparency, its key on the footprint; undecodable and unencodable images refused.
- [x] Terms: 409 without a proposal, without a transect and out of range; 400 without a body;
      stored on the row and in the status; rebuilt from the row after the cache is dropped;
      the abundance on the estimate after a review; the defaults kept with no boxes.
- [x] Module functions: placing estimated boxes by expected count, the ground position inside
      and outside the control grid, and the cache round trips of `PlacedBoxes` and
      `SurveyTerms`.
- [x] 77 tests pass, on the local stack and on a fresh restore of `local_db/pct_b` with a
      fresh SpiceDB from `local_db/backup.zed`. The survey map router, `app/overlays.py`,
      `app/proposal_store.py` and the `surveymap` and `abundance` modules are fully covered.

**Database.**
- [x] Migration `20261116000000_measurement_terms.sql` adds `active_measurements.terms`;
      `atlas.sum` rehashed; the canonical DDL and dbml carry the column.
- [x] `local_db/pct_b` re-dumped with the migration applied: the same 297 entries, the column
      added.

**Frontend.**
- [x] `vue-tsc --build` passes in the webapp container.
- [x] Leaflet 1.9.4 added, with its types as a dev dependency.
- [ ] The Survey Map page and the Overall Abundance card checked in a browser.
