# Pytest runner for the predictions router in the Airial API
# Author Michael B. Lance

from testing_core import APITester
import pytest 

class PredictionTester(APITester):

    # -------------------------------------------------------------------------
    # 1. GET Single & List Endpoint Schema Validation
    # ------------------------------------------------------------------------- 

    @pytest.mark.parameterize(
        "endpoint, expected_schema, is_list",
        [
            (

                )
            ]
            )

    def test_get_endpoints_schema_success(
            self, auth_client, endpoint, expected_schema, is_list
            ):
        pass
