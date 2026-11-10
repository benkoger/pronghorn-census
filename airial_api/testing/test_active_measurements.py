# Pytest runner for the active measurement and prediction routers in the Airial API
# Author: Owen Martin
# ---------------------------------------------------------------------------------------------------------------------------
# Runs like test_images.py: against the sample database, every test inside a
# transaction that is rolled back, S3 mocked, the tester account logged in.
# The survey's own measurement rows are deleted inside that transaction first,
# so the tests see the survey as the sample database has it, without one.
# Cache keys written by the routes are dropped after each test.

from uuid import uuid4

import io
import numpy as np
import pytest
from PIL import Image as PILImage
from psycopg.rows import tuple_row
from pydantic import TypeAdapter

from ais import Proposal
from app import proposal_store
from app.extensions import base, cache
from database.modules import activemeasurement as am
from database.object_models.core.am_units import AmUnit
from database.object_models.core.images import Image, ReviewedArea
from database.object_models.core.predictions import Prediction
from database.object_models.project_management.active_measurements import (
    ActiveMeasurement,
)
from testing_core import APITester

AM = "/api/v1/active-measurements"

SURVEY = {"pkey": 1, "uuid": "f4c0b5e0-af30-46fa-a276-6169932b6a34"}
LABEL = {"pkey": 3, "uuid": "d36185ab-1ae4-42f9-86b8-ec2f98f67693"}  # pronghorn
MODEL = {"pkey": 2, "uuid": "f5f4caad-1fd4-46a7-982e-21d396a36d48"}
IMAGE_ID = 1047
IMAGE_UUID = "26be495e-3ec2-41c8-ba14-d0b65726bb67"
IMAGE_SIZE = (8256, 5504)  # the sample image's declared size: tiles are cut from it

CACHE_KEYS = (
    "am_state_{uuid}",
    "am_terms_{uuid}",
    "am_area_{uuid}",
    "am_threshold_{uuid}",
)


def _sql(statement: str, params: dict | None = None) -> None:
    def run(cursor, db):
        cursor.execute(statement, params or {})

    base.execute(run)


class TestActiveMeasurements(APITester):

    # -------------------------------------------------------------------------
    # Fixtures: the survey without a measurement, then one with
    # -------------------------------------------------------------------------

    @pytest.fixture
    def bare_survey(self, auth_client):
        """The survey as the sample database ships it: no measurement."""
        _sql(
            "DELETE FROM projectmanagement.active_measurements "
            "WHERE survey_id = %(s)s;",
            {"s": SURVEY["pkey"]},
        )
        yield SURVEY

    @pytest.fixture
    def measurement(self, auth_client, bare_survey):
        res = auth_client.post(
            AM,
            json={
                "survey_ids": SURVEY,
                "label_ids": LABEL,
                "random_seed": 7,
                "retraining_cadence": 0,
                "target_percentage": 0.1,
            },
        )
        assert res.status_code == 201
        row = res.get_json()
        yield row
        for key in CACHE_KEYS:
            cache.delete(key.format(uuid=row["uuid"]))

    @pytest.fixture
    def tiles(self, auth_client, measurement):
        """The eight tiles of the sample image, cut if the database lacks them."""
        res = auth_client.post(
            f"{AM}/tiles", json={"survey_id": SURVEY["uuid"], "image_ids": [IMAGE_ID]}
        )
        assert res.status_code == 201
        mine = [t for t in res.get_json() if t["image_id"] == IMAGE_ID]
        assert len(mine) == am.TILE_ROWS * am.TILE_COLS
        return mine

    @pytest.fixture
    def proposal(self, auth_client, measurement, tiles):
        """Generation 0 over the sample image's tiles, every unit equally likely."""
        ids = [t["reviewed_area_id"] for t in tiles]
        res = auth_client.post(
            f"{AM}/{measurement['uuid']}/proposals",
            json={
                "reviewed_area_ids": ids,
                "raw": [1.0] * len(ids),
                "proposal": [1.0] * len(ids),
                "n_labels": 0,
                "alpha": 0.5,
            },
        )
        assert res.status_code == 201
        return res.get_json()

    @pytest.fixture
    def source_image(self, auth_client):
        """The sample image's bytes in the mocked bucket, at its declared size."""
        img = auth_client.get(f"/api/v1/images/{IMAGE_UUID}").get_json()
        buf = io.BytesIO()
        PILImage.new("RGB", IMAGE_SIZE, color="olive").save(buf, format="JPEG", quality=30)
        self.s3.put_object(Bucket=self.bucket_name, Key=img["img_key"], Body=buf.getvalue())
        return img

    # -------------------------------------------------------------------------
    # 1. Status and estimate before anything exists
    # -------------------------------------------------------------------------

    def test_status_without_measurement(self, auth_client, bare_survey):
        res = auth_client.get(f"{AM}/status", query_string={"survey_id": SURVEY["uuid"]})
        assert res.status_code == 200
        status = res.get_json()
        assert status["measurement"] is None
        assert status["ready"] is False
        assert [s["key"] for s in status["steps"]] == [
            "detections", "footprints", "tiles", "measurement", "proposal"
        ]

    def test_estimate_not_prepared(self, auth_client, bare_survey):
        res = auth_client.get(f"{AM}/estimate", query_string={"survey_id": SURVEY["uuid"]})
        assert res.status_code == 200
        est = res.get_json()
        assert est["status"] == "not prepared"
        assert est["active_measurement_id"] is None
        assert est["count"] is None

    def test_status_and_estimate_unknown_survey(self, auth_client):
        res = auth_client.get(f"{AM}/status", query_string={"survey_id": str(uuid4())})
        assert res.status_code == 404
        res = auth_client.get(f"{AM}/estimate", query_string={"survey_id": str(uuid4())})
        assert res.status_code == 404

    # -------------------------------------------------------------------------
    # 2. The measurement row
    # -------------------------------------------------------------------------

    def test_create_measurement_schema(self, measurement):
        ActiveMeasurement.Response.model_validate(measurement)
        assert measurement["survey_id"] == SURVEY["pkey"]
        assert measurement["label_id"] == LABEL["pkey"]
        assert measurement["final_count"] is None

    def test_create_measurement_invalid(self, auth_client, bare_survey):
        res = auth_client.post(AM, json={"survey_ids": SURVEY})
        assert res.status_code == 400

    def test_get_measurement(self, auth_client, measurement):
        res = auth_client.get(f"{AM}/{measurement['uuid']}")
        assert res.status_code == 200
        assert res.get_json()["uuid"] == measurement["uuid"]
        res = auth_client.get(f"{AM}/{measurement['active_measurement_id']}")
        assert res.status_code == 200

    def test_get_measurement_not_found(self, auth_client):
        res = auth_client.get(f"{AM}/{uuid4()}")
        assert res.status_code == 404

    def test_update_measurement(self, auth_client, measurement):
        res = auth_client.patch(
            f"{AM}/{measurement['uuid']}", json={"target_percentage": 0.05}
        )
        assert res.status_code == 200
        assert res.get_json()["target_percentage"] == 0.05

    def test_delete_measurement(self, auth_client, measurement):
        res = auth_client.delete(f"{AM}/{measurement['uuid']}")
        assert res.status_code == 204
        assert auth_client.get(f"{AM}/{measurement['uuid']}").status_code == 404
        assert cache.get(f"am_state_{measurement['uuid']}") is None

    def test_status_with_measurement(self, auth_client, measurement):
        res = auth_client.get(f"{AM}/status", query_string={"survey_id": SURVEY["uuid"]})
        assert res.status_code == 200
        status = res.get_json()
        assert status["measurement"]["uuid"] == measurement["uuid"]
        assert status["proposal_generations"] == 0

    def test_estimate_waiting_for_proposal(self, auth_client, measurement):
        res = auth_client.get(f"{AM}/estimate", query_string={"survey_id": SURVEY["uuid"]})
        assert res.status_code == 200
        est = res.get_json()
        assert est["status"] == "waiting for proposal"
        assert est["uuid"] == measurement["uuid"]
        assert est["count"] is None

    def test_next_unit_before_proposal(self, auth_client, measurement):
        res = auth_client.get(f"{AM}/next-unit", query_string={"survey_id": SURVEY["uuid"]})
        assert res.status_code == 409

    # -------------------------------------------------------------------------
    # 3. Tiles
    # -------------------------------------------------------------------------

    def test_tiles_cut_once(self, auth_client, measurement, tiles):
        """A second cut of the same image adds nothing; the listing carries bounds."""
        res = auth_client.post(
            f"{AM}/tiles", json={"survey_id": SURVEY["uuid"], "image_ids": [IMAGE_ID]}
        )
        assert res.status_code == 201
        again = [t for t in res.get_json() if t["image_id"] == IMAGE_ID]
        assert {t["reviewed_area_id"] for t in again} == {
            t["reviewed_area_id"] for t in tiles
        }

        res = auth_client.get(f"{AM}/tiles", query_string={"survey_id": SURVEY["uuid"]})
        assert res.status_code == 200
        listed = [t for t in res.get_json() if t["image_id"] == IMAGE_ID]
        assert len(listed) == len(tiles)
        for key in ("area_tx", "area_ty", "area_bx", "area_by", "name", "uuid"):
            assert key in listed[0]
        assert all(t["name"].endswith(f"__r{r}c{c}") for t, (r, c) in zip(
            sorted(listed, key=lambda t: (t["area_ty"], t["area_tx"])),
            [(r, c) for r in range(am.TILE_ROWS) for c in range(am.TILE_COLS)],
        ))

    # -------------------------------------------------------------------------
    # 4. Proposal generations as rows
    # -------------------------------------------------------------------------

    def test_proposal_rows(self, app, auth_client, measurement, tiles, proposal):
        assert proposal == {"generation": 0, "n_labels": 0}

        # the listing summarises the generations without their vectors
        res = auth_client.get(f"{AM}/{measurement['uuid']}/proposals")
        assert res.status_code == 200
        rows = res.get_json()
        assert rows == [
            {"generation": 0, "n_labels": 0, "n_units": len(tiles), "model_id": None, "alpha": 0.5}
        ]

        # the row itself holds the vectors, one entry per unit
        with app.app_context():
            row = base.get(ActiveMeasurement, measurement["active_measurement_id"])
            stored = base.execute(am.get_proposals, row)
            assert len(stored) == 1
            assert len(stored[0].proposal) == len(tiles)
            assert sorted(stored[0].reviewed_area_ids) == sorted(
                t["reviewed_area_id"] for t in tiles
            )

        res = auth_client.get(f"{AM}/status", query_string={"survey_id": SURVEY["uuid"]})
        assert res.get_json()["proposal_generations"] == 1

    def test_proposal_duplicate_and_out_of_order(self, auth_client, measurement, tiles, proposal):
        ids = [t["reviewed_area_id"] for t in tiles]
        body = {
            "reviewed_area_ids": ids,
            "raw": [1.0] * len(ids),
            "proposal": [1.0] * len(ids),
            "n_labels": 0,
            "alpha": 0.5,
        }
        # the same generation again: nothing stored
        res = auth_client.post(f"{AM}/{measurement['uuid']}/proposals", json=body)
        assert res.status_code == 409
        # a later generation must keep the unit order
        res = auth_client.post(
            f"{AM}/{measurement['uuid']}/proposals",
            json={**body, "reviewed_area_ids": list(reversed(ids)), "n_labels": 4},
        )
        assert res.status_code == 409
        rows = auth_client.get(f"{AM}/{measurement['uuid']}/proposals").get_json()
        assert len(rows) == 1

    def test_proposal_next_generation(self, auth_client, measurement, tiles, proposal):
        ids = [t["reviewed_area_id"] for t in tiles]
        res = auth_client.post(
            f"{AM}/{measurement['uuid']}/proposals",
            json={
                "reviewed_area_ids": ids,
                "raw": [1.0] * len(ids),
                "proposal": [2.0] * len(ids),
                "n_labels": 4,
                "alpha": 0.5,
            },
        )
        assert res.status_code == 201
        assert res.get_json()["generation"] == 1
        rows = auth_client.get(f"{AM}/{measurement['uuid']}/proposals").get_json()
        assert [r["generation"] for r in rows] == [0, 1]

    # -------------------------------------------------------------------------
    # 5. Serving, review and the estimate
    # -------------------------------------------------------------------------

    def test_next_unit_without_source_image(self, auth_client, measurement, tiles, proposal):
        """A tile whose source image is not in the bucket is withheld, not skipped."""
        res = auth_client.get(f"{AM}/next-unit", query_string={"survey_id": SURVEY["uuid"]})
        assert res.status_code == 409
        assert "not in the bucket" in res.get_json()["message"]

    def test_serving_loop(self, auth_client, measurement, tiles, proposal, source_image):
        survey = {"survey_id": SURVEY["uuid"]}
        tile_ids = {t["reviewed_area_id"] for t in tiles}

        first = auth_client.get(f"{AM}/next-unit", query_string=survey)
        assert first.status_code == 200
        unit = first.get_json()
        ReviewedArea.Response.model_validate(unit)
        assert unit["reviewed_area_id"] in tile_ids
        # drafted at the generation's threshold: a detector score
        assert 0 < unit["draft_threshold"] <= 1
        assert unit["n_boxes"] >= 0
        assert unit["expected_count"] >= 0

        # the same unit until it is reviewed, and its crop is in the bucket now
        again = auth_client.get(f"{AM}/next-unit", query_string=survey).get_json()
        assert again["reviewed_area_id"] == unit["reviewed_area_id"]
        self.s3.head_object(Bucket=self.bucket_name, Key=unit["ra_key"])

        # the detector's boxes are drafted on it
        drafts = auth_client.get(f"/api/v1/reviewed-area/{unit['uuid']}/annotations").get_json()
        assert len(drafts) == unit["n_boxes"]

        res = auth_client.patch(f"/api/v1/reviewed-area/{unit['uuid']}/set-reviewed")
        assert res.status_code == 200

        second = auth_client.get(f"{AM}/next-unit", query_string=survey).get_json()
        assert second["reviewed_area_id"] != unit["reviewed_area_id"]

        res = auth_client.get(f"{AM}/{measurement['uuid']}/am-units")
        assert res.status_code == 200
        units = res.get_json()
        TypeAdapter(list[AmUnit.Response]).validate_python(units)
        assert len(units) == 2

        est = auth_client.get(f"{AM}/estimate", query_string=survey).get_json()
        assert est["status"] == "measuring"
        assert est["n_reviewed"] == 1
        assert est["n_pending"] == 1
        assert est["n_units"] == len(tiles)
        assert est["phase"] == "full review"
        assert est["figures_from"] >= 100
        assert est["show_fraction"] == am.SHOW_FRACTION

    def test_review_to_exhaustion(self, auth_client, measurement, tiles, proposal, source_image):
        """Every unit served and reviewed: the measurement finishes with a count."""
        survey = {"survey_id": SURVEY["uuid"]}
        served = []
        while True:
            res = auth_client.get(f"{AM}/next-unit", query_string=survey)
            if res.status_code == 204:
                break
            assert res.status_code == 200
            unit = res.get_json()
            served.append(unit["reviewed_area_id"])
            assert auth_client.patch(
                f"/api/v1/reviewed-area/{unit['uuid']}/set-reviewed"
            ).status_code == 200

        assert len(served) == len(set(served))
        assert len(served) == len(tiles) - am.LAST_UNITS
        # finishing drops the serving state; a later estimate rebuilds it from the rows
        assert cache.get(f"am_state_{measurement['uuid']}") is None

        row = auth_client.get(f"{AM}/{measurement['uuid']}").get_json()
        assert row["final_count"] is not None

        est = auth_client.get(f"{AM}/estimate", query_string=survey).get_json()
        assert est["status"] == "finished"
        assert est["n_reviewed"] == len(served)
        assert est["count"] == pytest.approx(row["final_count"])

    # -------------------------------------------------------------------------
    # 6. The proposal store: cache in front of the rows
    # -------------------------------------------------------------------------

    def test_state_rebuilt_from_rows(self, app, auth_client, measurement, tiles, proposal):
        with app.app_context():
            row = base.get(ActiveMeasurement, measurement["active_measurement_id"])
            key = f"am_state_{row.uuid}"
            cache.delete(key)
            state = proposal_store.load(row)
            assert state is not None
            assert cache.get(key) is not None
            assert sorted(state.reviewed_area_ids) == sorted(
                t["reviewed_area_id"] for t in tiles
            )
            assert len(state.order) == len(tiles)

            cached = proposal_store.load(row)
            assert cached.order == state.order

            proposal_store.release(row)
            assert cache.get(key) is None

    def test_threshold_cached_per_generation(
        self, app, auth_client, measurement, tiles, proposal
    ):
        """The draft threshold is computed once and dropped when a generation lands."""
        with app.app_context():
            row = base.get(ActiveMeasurement, measurement["active_measurement_id"])
            state = proposal_store.load(row)
            key = f"am_threshold_{row.uuid}"
            cache.delete(key)
            threshold = proposal_store.load_threshold(row, state)
            assert 0 < threshold <= 1
            assert cache.get(key) is not None
            assert proposal_store.load_threshold(row, state) == threshold

            ids = state.reviewed_area_ids
            proposal_store.save(
                row,
                Proposal(
                    generation=1,
                    n_labels=1,
                    reviewed_area_ids=ids,
                    raw=np.full(len(ids), 100.0),
                    proposal=np.ones(len(ids)),
                ),
            )
            assert cache.get(key) is None
            # a far larger expected total admits more boxes: a lower score
            assert proposal_store.load_threshold(row, proposal_store.load(row)) <= threshold

    def test_area_cached_once(self, app, auth_client, measurement, tiles, proposal):
        with app.app_context():
            row = base.get(ActiveMeasurement, measurement["active_measurement_id"])
            state = proposal_store.load(row)
            key = f"am_area_{row.uuid}"
            cache.delete(key)
            area = proposal_store.load_area(row, state)
            assert area is None or area > 0
            if area is not None:
                assert cache.get(key) is not None
                assert proposal_store.load_area(row, state) == area

    # -------------------------------------------------------------------------
    # 7. Module functions behind the routes
    # -------------------------------------------------------------------------

    def test_draft_threshold(self, app, auth_client, measurement, tiles):
        """The k-th highest detector score of the label on the tiled images."""
        with app.app_context():
            row = base.get(ActiveMeasurement, measurement["active_measurement_id"])

            def scores(cursor, db):
                detector = am.get_detection_model(cursor, db, row.survey_id)
                cursor.row_factory = tuple_row
                cursor.execute(
                    """
                    SELECT p.score
                    FROM core.predictions p
                    JOIN projectmanagement.labels l ON l.label = p.label
                    WHERE p.model_id = %(m)s AND l.label_id = %(l)s
                      AND p.image_id IN (
                          SELECT ra.image_id FROM core.reviewed_area ra
                          JOIN core.images i ON i.image_id = ra.image_id
                          WHERE i.survey_id = %(s)s AND ra.type = 'active measurement')
                    ORDER BY p.score DESC;
                    """,
                    {"m": detector.model_id, "l": row.label_id, "s": row.survey_id},
                )
                return [float(r[0]) for r in cursor.fetchall()]

            ranked = base.execute(scores)
            assert ranked, "the sample survey has detector boxes on its tiled images"

            assert base.execute(am.draft_threshold, row, 0.0) == am.NO_DRAFTS
            assert base.execute(am.draft_threshold, row, 0.4) == am.NO_DRAFTS
            assert base.execute(am.draft_threshold, row, 1.0) == ranked[0]
            k = min(5, len(ranked))
            assert base.execute(am.draft_threshold, row, float(k)) == ranked[k - 1]
            # more animals expected than boxes: every box is drafted
            assert base.execute(am.draft_threshold, row, len(ranked) + 10.0) == ranked[-1]

    def test_detector_expectation(self, app, auth_client, measurement, tiles):
        threshold = 0.5
        preds = auth_client.get(f"/api/v1/images/{IMAGE_UUID}/predictions").get_json()
        above = [p for p in preds if p["score"] >= threshold]
        with app.app_context():
            row = base.get(ActiveMeasurement, measurement["active_measurement_id"])
            total_boxes = 0
            for tile in tiles:
                expected, n_boxes = base.execute(
                    am.detector_expectation, row, tile["reviewed_area_id"], threshold
                )
                assert expected >= 0 and n_boxes >= 0
                assert expected <= n_boxes  # every counted score is at most 1
                total_boxes += n_boxes
        # the tiles partition the image, so their boxes are the image's boxes of the label
        assert total_boxes <= len(above)

    def test_empty_estimate_shape(self, app):
        with app.app_context():
            est = am.empty_estimate(SURVEY["pkey"])
            assert est["status"] == "not prepared"
            assert est["show_fraction"] == am.SHOW_FRACTION
            for key in ("count", "ci_lower", "ci_upper", "phase", "figures_from"):
                assert est[key] is None

    def test_preparation_steps(self):
        steps = am.preparation_steps(
            {
                "images_with_predictions": 1,
                "images_with_footprints": 0,
                "tiles": 0,
                "georeferenced_images_without_tiles": 0,
                "measurement": None,
                "proposal_generations": 0,
            }
        )
        done = {s["key"]: s["done"] for s in steps}
        assert done == {
            "detections": True,
            "footprints": False,
            "tiles": False,
            "measurement": False,
            "proposal": False,
        }


class TestPredictions(APITester):

    def _one(self, auth_client) -> dict:
        preds = auth_client.get(f"/api/v1/images/{IMAGE_UUID}/predictions").get_json()
        assert preds
        return preds[0]

    def test_get_predictions_bulk(self, auth_client):
        pred = self._one(auth_client)
        res = auth_client.get("/api/v1/predictions", query_string={"object_ids": pred["uuid"]})
        assert res.status_code == 200
        rows = res.get_json()
        TypeAdapter(list[Prediction.Response]).validate_python(rows)
        assert rows[0]["uuid"] == pred["uuid"]

    def test_get_prediction_by_id(self, auth_client):
        pred = self._one(auth_client)
        res = auth_client.get(f"/api/v1/predictions/{pred['uuid']}")
        assert res.status_code == 200
        Prediction.Response.model_validate(res.get_json())
        assert auth_client.get(f"/api/v1/predictions/{uuid4()}").status_code == 404

    def test_create_prediction(self, auth_client):
        res = auth_client.post(
            "/api/v1/predictions",
            json={
                "image_ids": {"pkey": IMAGE_ID, "uuid": IMAGE_UUID},
                "model_ids": MODEL,
                "label": 2,
                "score": 0.42,
                "box_tx": 10,
                "box_ty": 10,
                "box_bx": 40,
                "box_by": 40,
            },
        )
        assert res.status_code == 200
        created = Prediction.Response.model_validate(res.get_json())
        assert created.score == 0.42
        assert created.label == 2
        assert created.dimensions == {
            "top_left": {"x": 10, "y": 10},
            "bottom_right": {"x": 40, "y": 40},
        }
        assert auth_client.get(f"/api/v1/predictions/{created.uuid}").status_code == 200

    def test_create_prediction_invalid(self, auth_client):
        res = auth_client.post("/api/v1/predictions", json={"score": 0.5})
        assert res.status_code == 400
