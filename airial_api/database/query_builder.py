# Psycopg3 sql based helpers
# Author: Michael B. Lance

#---------------------------------------------------------------------------------------------------------------------------#

from typing import List, Tuple, Dict, Union
from uuid import UUID

import psycopg.sql as sql

#---------------------------------------------------------------------------------------------------------------------------#

class QueryBuilder:
	'''Still not an ORM -ML'''
	@staticmethod
	def filter_by_object_ids(pfx: str, id_field: str, ids: Union[List[int], List[UUID], List[Union[int, UUID]]]) -> Tuple[sql.Composable, Dict]:
		'''
		
		'''
		data = { f'{pfx}_ints': [], f'{pfx}_uuids': [] }

		for id_val in ids:
			if isinstance(id_val, int):
				data[f'{pfx}_ints'].append(id_val)
			elif isinstance(id_val, UUID):
				data[f'{pfx}_uuids'].append(id_val)

		return sql.SQL(
				'{prefix}.{ident} = ANY({i_placehodler}::int[]) OR {prefix}.uuid = ANY({u_placeholder}::uuid[])'
			).format(
				prefix=sql.Identifier(pfx), 
				ident=sql.Identifier(id_field),
				i_placehodler=sql.Placeholder(f'{pfx}_ints'),
				u_placeholder=sql.Placeholder(f'{pfx}_uuids'),
			), data
