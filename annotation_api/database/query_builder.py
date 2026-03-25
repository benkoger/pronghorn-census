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
	def filter_by_object_ids(prefix: sql.Composable, id_field: sql.Composable, ids: List[Union[int, UUID]]) -> Tuple[sql.Composable, Dict]:
		'''
		
		'''
		pfx = prefix.as_string()
		data = { f'{pfx}_ints': [], f'{pfx}_uuids': [] }

		for id_val in ids:
			if isinstance(id_val, int):
				data['ints'].append(id_val)
			elif isinstance(id_val, UUID):
				data['uuids'].append(id_val)

		return sql.SQL(
			'{prefix}.{ident} = ANY(%({i_keys})s) OR {prefix}.uuid = ANY(%({u_keys})s)'
			).format(
				prefix=prefix, 
				ident=id_field,
				i_keys=sql.Identifier(f'{pfx}_ints'),
				u_keys=sql.Identifier(f'{pfx}_uuids'),
			), data