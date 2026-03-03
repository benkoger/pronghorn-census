from uuid import uuid4
import urllib.parse

from annotation_testing_core import APITester

class TestReviedAreas(APITester):

	def test_get_reviewed_area(self, auth_client):
		params = {
			'herd_unit_id': [1, 2],
			'survey_id': 1,
			'include_reviewed': False,
		}
		query_string = urllib.parse.urlencode(params, doseq=True)
		print(query_string)

		response = auth_client.get(f'/api/v1/reviewed-area?{query_string}')
		print(response.text)

		assert response.status_code == 200