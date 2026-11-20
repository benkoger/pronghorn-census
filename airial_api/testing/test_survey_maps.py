# Pytest runner for the survey map router and the abundance terms in the Airial API
# Author: Owen Martin
# ---------------------------------------------------------------------------------------------------------------------------
# Runs like test_active_measurements.py, whose fixtures it shares: the sample
# database with every test rolled back, S3 mocked, the tester account. The
# sample image is georeferenced inside the transaction: a footprint over a
# small box of ground with a grid of ground control points, and metadata
# putting it on transect 0. Its earlier footprints are deleted first, so the
# tests see only the one they made.

import io
from datetime import UTC, datetime
from uuid import UUID, uuid4

import numpy as np
import pytest
from PIL import Image as PILImage
from psycopg.rows import tuple_row

from ais import PlacedBoxes, SurveyTerms
from app import overlays, proposal_store
from app.extensions import base, cache
from app.routers.survey_maps import NO_DETECTIONS
from crop_generator import cluster_windows
from database.modules import abundance, surveymap
from database.object_models.core.images import Image
from database.object_models.project_management.active_measurements import (
    ActiveMeasurement,
)
from test_active_measurements import (
    AM,
    IMAGE_ID,
    IMAGE_SIZE,
    IMAGE_UUID,
    LABEL,
    SURVEY,
    MeasurementFixtures,
    _sql,
)

MAPS = "/api/v1/survey-maps"
# The ground the sample image covers: west, south, east, north.
BBOX = [-105.20, 41.000, -105.19, 41.005]
GRID = 5  # ground control points per side


def _gcps() -> list[list[float]]:
    """A GRID x GRID grid of (row, column, longitude, latitude) over BBOX."""
    width, height = IMAGE_SIZE
    west, south, east, north = BBOX
    return [
        [row, col, west + col / width * (east - west), north - row / height * (north - south)]
        for row in np.linspace(0, height, GRID).tolist()
        for col in np.linspace(0, width, GRID).tolist()
    ]


def _jpeg(size: tuple[int, int]) -> bytes:
    buf = io.BytesIO()
    PILImage.new("RGB", size, color="olive").save(buf, format="JPEG")
    return buf.getvalue()


def _inside(lon: float, lat: float) -> bool:
    west, south, east, north = BBOX
    return west <= lon <= east and south <= lat <= north


def _footprint(image_ids: dict, bbox: list[float], gcps: list[list[float]]) -> dict:
    """A footprint over `bbox` for the image-footprints route."""
    west, south, east, north = bbox
    ring = [[west, south], [east, south], [east, north], [west, north], [west, south]]
    return {
        "image_ids": image_ids,
        "footprint": {"type": "Polygon", "coordinates": [ring]},
        "bbox_wsen": bbox,
        "footprint_partial": False,
        "area_m2": 4.6e5,
        "area_geodesic_m2": 4.6e5,
        "area_sigma_m2": 0.0,
        "area_q05_m2": 4.6e5,
        "area_q95_m2": 4.6e5,
        "dem_name": "test",
        "georef_status": "solved",
        "n_ties": 0,
        "tie_residual_before_m": 0.0,
        "rmse_h_m": 2.0,
        "rmse_p50_m": 2.0,
        "rmse_p90_m": 2.0,
        "n_checkpoints": 0,
        "pose_delta": [0.0] * 7,
        "pose_sigma": [0.0] * 7,
        "pose_free": [],
        "pose_cond": 0.0,
        "prior_source": "test",
        "gcps": gcps,
        "overlay_uri": "",
        "georef_modified": datetime.now(UTC).isoformat(),
    }


class TestSurveyMaps(MeasurementFixtures):

    # -------------------------------------------------------------------------
    # Fixtures: the sample image without a footprint, then georeferenced
    # -------------------------------------------------------------------------

    @pytest.fixture
    def bare_image(self, auth_client):
        """The sample image without a footprint."""
        _sql(
            "DELETE FROM core.image_footprints WHERE image_id = %(i)s;",
            {"i": IMAGE_ID},
        )
        return IMAGE_UUID

    @pytest.fixture
    def georeferenced(self, auth_client, bare_image):
        """A footprint over BBOX with ground control, and transect 0."""
        west, south, east, north = BBOX
        image_ids = {"pkey": IMAGE_ID, "uuid": IMAGE_UUID}
        res = auth_client.post(
            "/api/v1/image-footprints", json=_footprint(image_ids, BBOX, _gcps())
        )
        assert res.status_code == 201
        res = auth_client.post(
            "/api/v1/image-metadata",
            json={
                "image_ids": image_ids,
                "captured_at": datetime.now(UTC).isoformat(),
                "gps_lon": (west + east) / 2,
                "gps_lat": (south + north) / 2,
                "gps_alt_msl_m": 2000.0,
                "yaw_deg": 0.0,
                "pitch_deg": 0.0,
                "fov_deg": 60.0,
                "terrain_elev_m": 1900.0,
                "agl_m": 100.0,
                "transect_id": 0,
            },
        )
        assert res.status_code == 201
        return res.get_json()

    def _review_one(self, auth_client) -> dict:
        """Serves the next unit, adds an animal at its center to its drafts,
        and marks it reviewed."""
        unit = auth_client.get(
            f"{AM}/next-unit", query_string={"survey_id": SURVEY["uuid"]}
        ).get_json()
        corners = unit["dimensions"]
        x = (corners["top_left"]["x"] + corners["bottom_right"]["x"]) // 2
        y = (corners["top_left"]["y"] + corners["bottom_right"]["y"]) // 2
        res = auth_client.post(
            "/api/v1/annotations",
            json={
                "label_id": LABEL["pkey"],
                "image_ids": {"pkey": IMAGE_ID, "uuid": IMAGE_UUID},
                "herd_unit_id": 1,
                "box_tx": x - 10,
                "box_ty": y - 10,
                "box_bx": x + 10,
                "box_by": y + 10,
                "uuid": str(uuid4()),
                "type": "active measurement",
                "reviewed_area_ids": {"pkey": unit["reviewed_area_id"], "uuid": unit["uuid"]},
            },
        )
        assert res.status_code == 201
        res = auth_client.patch(f"/api/v1/reviewed-area/{unit['uuid']}/set-reviewed")
        assert res.status_code == 200
        return {**unit, "animals": unit["n_boxes"] + 1}

    # -------------------------------------------------------------------------
    # 1. Footprints
    # -------------------------------------------------------------------------

    def test_footprints(self, auth_client, georeferenced, tiles):
        res = auth_client.get(f"{MAPS}/footprints", query_string={"survey_id": SURVEY["uuid"]})
        assert res.status_code == 200
        collection = res.get_json()
        assert collection["type"] == "FeatureCollection"

        mine = [
            f for f in collection["features"] if f["properties"]["image_uuid"] == IMAGE_UUID
        ]
        assert len(mine) == 1
        feature = mine[0]
        assert feature["geometry"]["type"] == "Polygon"
        assert feature["properties"]["bbox_wsen"] == BBOX
        assert feature["properties"]["tiles"] == len(tiles)
        assert feature["properties"]["tiles_reviewed"] == 0

    def test_footprints_unknown_survey(self, auth_client):
        from uuid import UUID, uuid4

        res = auth_client.get(f"{MAPS}/footprints", query_string={"survey_id": str(uuid4())})
        assert res.status_code == 404

    # -------------------------------------------------------------------------
    # 2. Detections
    # -------------------------------------------------------------------------

    def test_detections_without_measurement(self, auth_client, bare_survey):
        res = auth_client.get(f"{MAPS}/detections", query_string={"survey_id": SURVEY["uuid"]})
        assert res.status_code == 200
        assert res.get_json() == NO_DETECTIONS

    def test_detections_without_proposal(self, auth_client, measurement):
        res = auth_client.get(f"{MAPS}/detections", query_string={"survey_id": SURVEY["uuid"]})
        assert res.status_code == 200
        assert res.get_json() == NO_DETECTIONS

    def test_detections_after_review(
        self, auth_client, georeferenced, measurement, tiles, proposal, source_image
    ):
        unit = self._review_one(auth_client)

        res = auth_client.get(f"{MAPS}/detections", query_string={"survey_id": SURVEY["uuid"]})
        assert res.status_code == 200
        shown = res.get_json()

        # The reviewed tile's annotations, on the sample image.
        assert shown["annotated"] == unit["animals"]
        assert shown["threshold"] == unit["draft_threshold"]
        annotated = [d for d in shown["detections"] if d["kind"] == "annotated"]
        assert len(annotated) == unit["animals"]
        for d in annotated:
            assert d["image_id"] == IMAGE_ID
            assert d["reviewed_area_id"] == unit["reviewed_area_id"]
            assert _inside(d["lon"], d["lat"])
            assert d["score"] is None and d["prediction_uuid"] is None
            assert len(d["box"]) == 4
            # The box on the ground: north up and west left as the ground
            # control runs, centered where the animal is placed.
            (west, north), (east, _), (_, south), _ = d["corners"]
            assert west < east and south < north
            assert sum(c[0] for c in d["corners"]) / 4 == pytest.approx(d["lon"])
            assert sum(c[1] for c in d["corners"]) / 4 == pytest.approx(d["lat"])
            # No other image covers the sample image's ground.
            assert d["weight"] == 1.0

        # The rest stand in for the animals the estimate expects elsewhere.
        estimated = [d for d in shown["detections"] if d["kind"] == "estimated"]
        assert len(estimated) == shown["estimated"]
        for d in estimated:
            assert d["score"] >= shown["threshold"]
            assert d["prediction_uuid"] and d["box"] is None
            assert 0 < d["weight"] <= 1
            assert len(d["corners"]) == 4
            assert d["reviewed_area_id"] != unit["reviewed_area_id"]

        est = auth_client.get(
            f"{AM}/estimate", query_string={"survey_id": SURVEY["uuid"]}
        ).get_json()
        wanted = int(round(max(0.0, est["count"] - shown["annotated"])))
        assert shown["estimated"] + shown["unplaced"] == wanted

        # The map's footprint now counts the reviewed tile.
        collection = auth_client.get(
            f"{MAPS}/footprints", query_string={"survey_id": SURVEY["uuid"]}
        ).get_json()
        mine = [
            f for f in collection["features"] if f["properties"]["image_uuid"] == IMAGE_UUID
        ]
        assert mine[0]["properties"]["tiles_reviewed"] == 1

    def test_detections_off_the_ground(
        self, auth_client, bare_image, measurement, tiles, proposal, source_image
    ):
        """An annotation on an image with no footprint is counted, not drawn."""
        unit = self._review_one(auth_client)
        shown = auth_client.get(
            f"{MAPS}/detections", query_string={"survey_id": SURVEY["uuid"]}
        ).get_json()
        assert shown["annotated"] == unit["animals"]
        assert not [d for d in shown["detections"] if d["image_id"] == IMAGE_ID]

    # -------------------------------------------------------------------------
    # 3. Overlays
    # -------------------------------------------------------------------------

    def test_overlay_without_footprint(self, auth_client, bare_image):
        res = auth_client.get(f"{MAPS}/overlay", query_string={"image_id": IMAGE_UUID})
        assert res.status_code == 404

    def test_overlay_without_ground_control(self, auth_client, georeferenced):
        _sql(
            "UPDATE core.image_footprints SET gcps = '[]'::jsonb WHERE image_id = %(i)s;",
            {"i": IMAGE_ID},
        )
        res = auth_client.get(f"{MAPS}/overlay", query_string={"image_id": IMAGE_UUID})
        assert res.status_code == 404

    def test_overlay_drawn_once(self, auth_client, georeferenced, source_image, monkeypatch):
        drawn = []
        render = overlays.render
        monkeypatch.setattr(
            overlays, "render", lambda *args: drawn.append(1) or render(*args)
        )

        res = auth_client.get(f"{MAPS}/overlay", query_string={"image_id": IMAGE_UUID})
        assert res.status_code == 200
        overlay = res.get_json()
        west, south, east, north = BBOX
        assert overlay["bounds"] == [[south, west], [north, east]]
        key = f"images/{IMAGE_UUID}/overlay/{overlays.OVERLAY_FILE}"
        assert key in overlay["url"]

        # Stored in the bucket, with transparency where the image is not.
        stored = self.s3.get_object(Bucket=self.bucket_name, Key=key)["Body"].read()
        pixels = np.asarray(PILImage.open(io.BytesIO(stored)).convert("RGBA"))
        assert pixels.shape[1] == overlays.OVERLAY_WIDTH_PX
        assert (pixels[..., 3] == 255).any()

        def stored_key(cursor, db):
            cursor.row_factory = tuple_row
            cursor.execute(
                "SELECT overlay_uri FROM core.image_footprints WHERE image_id = %(i)s;",
                {"i": IMAGE_ID},
            )
            return cursor.fetchone()[0]

        assert base.execute(stored_key) == key

        # The second request finds it stored and does not draw again.
        res = auth_client.get(f"{MAPS}/overlay", query_string={"image_id": IMAGE_UUID})
        assert res.status_code == 200
        assert drawn == [1]

    def test_image_crops(
        self, app, auth_client, georeferenced, measurement, tiles, proposal, source_image
    ):
        crops_of = f"{MAPS}/image-crops"
        query = {"image_id": IMAGE_UUID}
        # The source image is cached by uuid; drop any copy of another run's.
        with app.app_context():
            cache.delete(UUID(IMAGE_UUID))

        # No annotated animal before a review.
        res = auth_client.get(crops_of, query_string=query)
        assert res.status_code == 200
        assert res.get_json() == {"crops": []}

        self._review_one(auth_client)
        shown = auth_client.get(
            f"{MAPS}/detections", query_string={"survey_id": SURVEY["uuid"]}
        ).get_json()
        boxes = [d["box"] for d in shown["detections"] if d["kind"] == "annotated"]

        # Twice: the second from the cached source image.
        for _ in range(2):
            crops = auth_client.get(crops_of, query_string=query).get_json()["crops"]
            assert crops
            for crop in crops:
                assert crop["image"].startswith("data:image/webp;base64,")
                left, top, right, bottom = crop["window"]
                assert right - left == overlays.CROP_PX
                assert bottom - top == overlays.CROP_PX

            # Every annotated animal is in a crop, at its place in the crop.
            for left, top, right, bottom in boxes:
                assert any(
                    [left - c["window"][0], top - c["window"][1],
                     right - c["window"][0], bottom - c["window"][1]] in c["boxes"]
                    for c in crops
                )

    def test_image_crops_without_measurement(self, auth_client, bare_survey):
        res = auth_client.get(f"{MAPS}/image-crops", query_string={"image_id": IMAGE_UUID})
        assert res.status_code == 200
        assert res.get_json() == {"crops": []}

    def test_image_crops_refuse(self, app, monkeypatch):
        monkeypatch.setattr(overlays, "_source", lambda image: b"not an image")
        with app.app_context():
            image = base.get(Image, UUID(IMAGE_UUID))
            with pytest.raises(ValueError):
                overlays.annotated_crops(image, [[0, 0, 10, 10]])
        monkeypatch.setattr(
            overlays.cv2, "imencode", lambda *args, **kwargs: (False, None)
        )
        monkeypatch.setattr(overlays, "_source", lambda image: _jpeg((64, 64)))
        with app.app_context():
            with pytest.raises(ValueError):
                overlays.annotated_crops(image, [[0, 0, 10, 10]])

    def test_cluster_windows(self):
        assert cluster_windows([], 1000, 1000, 100) == []

        # Two animals close together: one window around both.
        near = [[100, 100, 120, 120], [150, 150, 170, 170]]
        assert cluster_windows(near, 1000, 1000, 100) == [(85, 85, 185, 185)]

        # Far apart: a window each, kept inside the image.
        far = [[0, 0, 20, 20], [950, 950, 990, 990]]
        windows = sorted(cluster_windows(far, 1000, 1000, 100))
        assert windows == [(0, 0, 100, 100), (900, 900, 1000, 1000)]

        # A box larger than a window: a window at each box's center.
        assert cluster_windows([[0, 0, 300, 300]], 1000, 1000, 100) == [
            (100, 100, 200, 200)
        ]

    def test_render_refuses(self, monkeypatch):
        gcps, bbox = _gcps(), BBOX
        with pytest.raises(ValueError):
            overlays.render(b"not an image", gcps, bbox)

        buf = io.BytesIO()
        PILImage.new("RGB", (64, 48), color="olive").save(buf, format="JPEG")
        monkeypatch.setattr(overlays.cv2, "imencode", lambda *args: (False, None))
        with pytest.raises(ValueError):
            overlays.render(buf.getvalue(), gcps, bbox)

    # -------------------------------------------------------------------------
    # 4. Survey terms and the abundance
    # -------------------------------------------------------------------------

    def test_terms_without_proposal(self, auth_client, measurement):
        res = auth_client.post(
            f"{AM}/{measurement['uuid']}/terms", json={"habitable_area_m2": 5.0e6}
        )
        assert res.status_code == 409

    def test_terms_invalid(self, auth_client, measurement):
        res = auth_client.post(f"{AM}/{measurement['uuid']}/terms", json={})
        assert res.status_code == 400

    def test_terms_without_transect(
        self, auth_client, georeferenced, measurement, tiles, proposal
    ):
        _sql(
            "UPDATE core.image_metadata m SET transect_id = -1 FROM core.images i "
            "WHERE i.image_id = m.image_id AND i.survey_id = %(s)s;",
            {"s": SURVEY["pkey"]},
        )
        res = auth_client.post(
            f"{AM}/{measurement['uuid']}/terms", json={"habitable_area_m2": 5.0e6}
        )
        assert res.status_code == 409

    def test_terms_out_of_range(self, auth_client, georeferenced, measurement, tiles, proposal):
        res = auth_client.post(
            f"{AM}/{measurement['uuid']}/terms", json={"habitable_area_m2": -1.0}
        )
        assert res.status_code == 409

    def test_terms_and_abundance(
        self, app, auth_client, georeferenced, measurement, tiles, proposal, source_image
    ):
        survey = {"survey_id": SURVEY["uuid"]}

        # Before the terms: a count without an abundance, and the optional
        # step not done.
        status = auth_client.get(f"{AM}/status", query_string=survey).get_json()
        assert status["terms"] is None
        assert [s for s in status["steps"] if s["key"] == "terms"][0]["done"] is False

        res = auth_client.post(
            f"{AM}/{measurement['uuid']}/terms", json={"habitable_area_m2": 5.0e6}
        )
        assert res.status_code == 201
        summary = res.get_json()
        assert summary["habitable_area_m2"] == 5.0e6
        assert summary["surveyed_area_m2"] > 0
        assert summary["transects"] >= 1
        assert 0 < summary["overlap_factor"] <= 1
        assert summary["boxes_placed"] >= 0

        # Stored on the row, reported by the status.
        with app.app_context():
            row = base.get(ActiveMeasurement, measurement["active_measurement_id"])
            assert row.terms is not None
            assert row.terms["habitable_area_m2"] == 5.0e6
        status = auth_client.get(f"{AM}/status", query_string=survey).get_json()
        assert status["terms"]["transects"] == summary["transects"]
        step = [s for s in status["steps"] if s["key"] == "terms"][0]
        assert step["done"] is True and step["optional"] is True

        # No abundance before a reviewed tile; one once the count is positive.
        est = auth_client.get(f"{AM}/estimate", query_string=survey).get_json()
        assert est["abundance"] is None
        self._review_one(auth_client)
        est = auth_client.get(f"{AM}/estimate", query_string=survey).get_json()
        assert est["area_m2"] == summary["surveyed_area_m2"]
        if est["count"] > 0:
            assert est["abundance"]["habitable_area_m2"] == 5.0e6
            assert est["abundance"]["ci_lower"] <= est["abundance"]["abundance"]
        else:
            assert est["abundance"] is None

    def test_terms_rebuilt_from_row(
        self, app, auth_client, georeferenced, measurement, tiles, proposal
    ):
        res = auth_client.post(
            f"{AM}/{measurement['uuid']}/terms", json={"habitable_area_m2": 5.0e6}
        )
        assert res.status_code == 201

        with app.app_context():
            row = base.get(ActiveMeasurement, measurement["active_measurement_id"])
            cached = proposal_store.load_terms(row)
            cache.delete(f"am_terms_{row.uuid}")
            rebuilt = proposal_store.load_terms(row)
            assert rebuilt.as_dict() == cached.as_dict()
            assert cache.get(f"am_terms_{row.uuid}") is not None

    def test_live_abundance(self, app, auth_client, georeferenced, measurement, tiles, proposal):
        auth_client.post(
            f"{AM}/{measurement['uuid']}/terms", json={"habitable_area_m2": 5.0e6}
        )
        with app.app_context():
            row = base.get(ActiveMeasurement, measurement["active_measurement_id"])
            state = proposal_store.load(row)
            terms = proposal_store.load_terms(row)
            boxes = proposal_store.load_boxes(row, state)

            # The boxes are placed once per generation.
            assert cache.get(f"am_boxes_{row.uuid}") is not None

            nothing = base.execute(
                abundance.live_abundance, row, state, {"count": None}, terms, boxes
            )
            assert nothing is None

            estimate = {"count": 10.0, "std_error": 2.0}
            result = base.execute(
                abundance.live_abundance, row, state, estimate, terms, boxes
            )
            animals = result["overlap_factor"] * 10.0
            assert result["abundance"] == pytest.approx(
                animals / terms.surveyed_area_m2 * terms.habitable_area_m2
            )
            assert result["ci_lower"] <= result["abundance"] <= result["ci_upper"]
            assert result["overlap_factor_prepared"] == terms.overlap_factor

    def test_terms_without_boxes(self, app, auth_client, georeferenced, measurement):
        """With no box on the ground, the terms keep their defaults."""
        empty = PlacedBoxes([], [], [], [], [], [], [])
        with app.app_context():
            row = base.get(ActiveMeasurement, measurement["active_measurement_id"])
            terms = base.execute(abundance.prepare_terms, row, empty, 5.0e6, 0.0, [])
            assert terms.overlap_factor == 1.0
            assert terms.representation_sigma == 0.0

    def test_overlap_from_covering_images(self, app, auth_client, georeferenced):
        """An animal inside another image's footprint has weight 1/2."""
        west, south, east, north = BBOX
        middle = (west + east) / 2
        with app.app_context():
            other = base.execute(
                lambda cursor, db: cursor.execute(
                    "SELECT image_id, uuid FROM core.images "
                    "WHERE survey_id = %(s)s AND image_id <> %(i)s "
                    "ORDER BY image_id LIMIT 1;",
                    {"s": SURVEY["pkey"], "i": IMAGE_ID},
                ).fetchone()
            )
        other_ids = {"pkey": other[0], "uuid": str(other[1])}
        res = auth_client.post(
            "/api/v1/image-footprints",
            json=_footprint(other_ids, [west, south, middle, north], []),
        )
        assert res.status_code == 201

        lat = (south + north) / 2
        positions = [
            ((west + middle) / 2, lat),  # in both footprints
            ((middle + east) / 2, lat),  # in the sample image's only
            ((west + middle) / 2, lat),  # placed from the other image
        ]
        with app.app_context():
            frames = base.execute(abundance.get_frames, SURVEY["pkey"])
            per_image, factor = base.execute(
                lambda cursor, db: abundance._weighted(
                    cursor,
                    SURVEY["pkey"],
                    frames,
                    [IMAGE_ID, IMAGE_ID, other[0]],
                    positions,
                )
            )
        assert per_image == {IMAGE_ID: 1.5, other[0]: 0.5}
        assert factor == pytest.approx(2.0 / 3.0)

        with app.app_context():
            nothing = base.execute(
                lambda cursor, db: surveymap.covering(cursor, SURVEY["pkey"], [], [])
            )
        assert len(nothing) == 0

    def test_transect_areas_without_footprints(self, app):
        with app.app_context():
            # The placeholder survey has no images.
            assert base.execute(abundance.get_transect_areas, 0) == ([], [], 0.0)

    # -------------------------------------------------------------------------
    # 5. Module functions
    # -------------------------------------------------------------------------

    def test_place_estimated(self):
        boxes = [
            {"reviewed_area_id": 1, "score": 0.9},
            {"reviewed_area_id": 2, "score": 0.8},
            {"reviewed_area_id": 1, "score": 0.7},
            {"reviewed_area_id": 3, "score": 0.6},
        ]
        expected = {1: 0.4, 2: 1.6, 3: 0.0}

        # Tile 2 first (most expected), room for ceil(1.6) = 2 but it has one;
        # then tile 1, room for one; then tile 3.
        picked = surveymap.place_estimated(boxes, expected, 3)
        assert [(b["reviewed_area_id"], b["score"]) for b in picked] == [
            (2, 0.8),
            (1, 0.9),
            (3, 0.6),
        ]
        # The rest are the highest scoring boxes left.
        assert len(surveymap.place_estimated(boxes, expected, 4)) == 4
        assert surveymap.place_estimated(boxes, expected, 0) == []
        assert len(surveymap.place_estimated(boxes, expected, 10)) == 4

    def test_ground_position(self):
        assert surveymap.ground_position([[0, 0, 1, 1], [0, 1, 2, 1]]) is None

        locate = surveymap.ground_position(_gcps())
        width, height = IMAGE_SIZE
        west, south, east, north = BBOX
        lon, lat = locate(width / 2, height / 2)
        assert lon == pytest.approx((west + east) / 2)
        assert lat == pytest.approx((south + north) / 2)
        # Outside the grid, the nearest control point.
        assert locate(-1000.0, -1000.0) == pytest.approx((west, north))

    def test_cache_round_trips(self):
        boxes = PlacedBoxes(
            image_ids=[1, 2],
            reviewed_area_ids=[3, 4],
            prediction_uuids=["a", "b"],
            scores=[0.9, 0.8],
            lon=[-105.0, -105.1],
            lat=[41.0, 41.1],
            corners=[[0.0] * 8, [1.0] * 8],
        )
        again = PlacedBoxes.from_cache(boxes.to_cache())
        assert again.prediction_uuids == ["a", "b"]
        assert again.lat.tolist() == [41.0, 41.1]
        assert again.corners.tolist() == [[0.0] * 8, [1.0] * 8]
        assert len(again) == 2
        with pytest.raises(ValueError):
            PlacedBoxes([1], [1], [], [0.5], [0.0], [0.0], [[0.0] * 8])

        terms = SurveyTerms(habitable_area_m2=5.0, surveyed_area_m2=1.0, transects=["0"],
                            transect_areas_m2=[1.0])
        assert SurveyTerms.from_cache(terms.to_cache()).as_dict() == terms.as_dict()
