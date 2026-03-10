# Class definition for objects used in the crop_generator module and database
# Author: Michael B. Lance
# created: April 4, 2025
# updated: February 3, 2026
#---------------------------------------------------------------------------------------------------------------------------#

import numpy as np
from flask.json.provider import JSONProvider
import cv2
from abc import ABC, abstractmethod
from datetime import datetime
import io
import PIL.Image as PillowImage
from dataclasses import dataclass
from uuid import UUID
from flask_login import UserMixin 
from typing import Optional, List 

#---------------------------------------------------------------------------------------------------------------------------#
# ABC for easy serialization of child classes

class CgOBJ(ABC):
	@abstractmethod
	def to_dict(self) -> dict:
		pass

fmt = lambda dt: dt.strftime('%Y-%m-%d %H:%M:%S%z') if isinstance(dt, datetime) else None	

#---------------------------------------------------------------------------------------------------------------------------#
# Project Management -- For Database use only

@dataclass
class Project(CgOBJ):
	''' Dataclass for representing projects from the databse
	
	'''
	project_id: int
	name: str
	created: datetime
	modified: datetime
	uuid: UUID

	def to_dict(self):
		return {
			'project_id': self.project_id,
			'name': self.name,
			'created': fmt(self.created),
			'modified': fmt(self.modified),
			'uuid': str(self.uuid)
		}

@dataclass
class Schema(CgOBJ):
	''' Dataclass for representing scehmas from the databse
	
	'''
	schema_id: int
	name: str
	created: datetime
	modified: datetime
	uuid: UUID

	def to_dict(self):
		return {
			'schema_id': self.schema_id,
			'name': self.name,
			'created': fmt(self.created),
			'modified': fmt(self.modified),
			'uuid': str(self.uuid)
		}

@dataclass
class Label(CgOBJ):
	''' Dataclass for representing labels from the databse
	
	'''
	label_id: int
	schema_id: int
	label: int
	name: str
	image_link: str
	created: datetime
	modified: datetime
	color: str
	uuid: UUID

	def to_dict(self):
		return {
			'label_id': self.label_id,
			'label': self.label,
			'name': self.name,
			'image_link': self.image_link,
			'color': self.color,
			'created': fmt(self.created),
			'modified': fmt(self.modified),
			'uuid': str(self.uuid)
		}

@dataclass
class HerdUnit(CgOBJ):
	''' Dataclass for representing Herd Units from the database
	
	'''
	herd_unit_id: int
	name: str
	created: datetime
	modified: datetime
	uuid: UUID

	def to_dict(self):
		return {
			'herd_unit_id': self.herd_unit_id,
			'name': self.name,
			'created': fmt(self.created),
			'modified': fmt(self.modified),
			'uuid': str(self.uuid)
		}

@dataclass
class Model(CgOBJ):
	''' Dataclass for representing Models from the database
	
	'''
	model_id: int
	schema_id: int
	name: str
	created: datetime
	modified: datetime
	uuid: UUID

	def to_dict(self):
		return {
			'model_id': self.model_id,
			'schema_id': self.schema_id,
			'name': self.name,
			'created': fmt(self.created),
			'modified': fmt(self.modified),
			'uuid': str(self.uuid)
		}
	
@dataclass
class Survey(CgOBJ):
	''' Dataclass for representing Surveys from the database
	
	'''
	survey_id: int
	survey_date: datetime
	name: str
	additional_info: str
	created: datetime
	modified: datetime
	uuid: UUID

	def to_dict(self):
		return {
			'survey_id': self.survey_id,
			'survey_date': self.survey_date,
			'name': self.name,
			'additional_info': self.additional_info,
			'created': fmt(self.created),
			'modified': fmt(self.modified),
			'uuid': str(self.uuid)
		}
	
#---------------------------------------------------------------------------------------------------------------------------#
# User Management -- For Database use only
	
@dataclass
class Role(CgOBJ):
	role_id: int
	name: str
	created: datetime
	modified: datetime
	uuid: UUID

	def to_dict(self):
		return {
			'role_id': self.role_id,
			'name': self.name,
			'created': fmt(self.created),
			'modified': fmt(self.modified),
			'uuid': str(self.uuid)
		}
	
@dataclass
class Organization(CgOBJ):
	organization_id: int
	name: str
	created: datetime
	modified: datetime
	logo_url: str | None
	uuid: UUID

	def to_dict(self):
		return {
			'organization_id': self.organization_id,
			'name': self.name,
			'created': fmt(self.created),
			'modified': fmt(self.modified),
			'logo_url': self.logo_url,
			'uuid': str(self.uuid)
		}

class User(UserMixin, CgOBJ):
	def __init__(
			self, user_id: int, username: str, email: str, external_auth_id: str, external_auth_provider: str, 
			status: str, created: datetime, modified: datetime, last_login: datetime,  locale: str,
			uuid: UUID, password_hash: Optional[str]=None, roles: Optional[set[str]]=None
		):
		self.id = str(uuid) # this is this way to make Flask-Login happy
		self.user_id = user_id
		self.email = email
		self.username = username
		self.external_auth_id = external_auth_id
		self.external_auth_provider = external_auth_provider
		self.status = status
		self.created = created
		self.modified = modified
		self.last_login = last_login
		self.locale = locale
		self.uuid = uuid
		self.password_hash = password_hash
		self.roles = roles
	
	def getId(self) -> str:
		return self.id
	
	def hasRole(self, role_name: str) -> bool:
		if self.roles:
			return role_name in self.roles
		else:
			return False

	def to_dict(self):
		return {
			'user_id': self.user_id,
			'username': self.username,
			'email': self.email,
			'status': self.status,
			'created': fmt(self.created),
			'modified': fmt(self.modified),
			'last_login': fmt(self.last_login),
			'locale': self.locale,
			'uuid': str(self.uuid),
		}

	def to_cache(self):
		return {
			**self.to_dict(),
			'external_auth_id': self.external_auth_id,
			'external_auth_provider': self.external_auth_provider,
			'roles': self.roles
		}

#---------------------------------------------------------------------------------------------------------------------------#
# Core 

class Box(CgOBJ):
	''' A Box contains dimensional data for crops and predictions
	
	'''
	def __init__(self, top_left: tuple[int, int], bottom_right: tuple[int, int]):
		self.top_left = top_left
		self.bottom_right = bottom_right

	def getCenter(self) -> tuple:
		x = np.mean([self.top_left[0], self.bottom_right[0]])
		y = np.mean([self.top_left[1], self.bottom_right[1]])

		return ((abs(x), abs(y)))

	def getPoints(self) -> list[int]:
		return [self.top_left[0], self.top_left[1], self.bottom_right[0], self.bottom_right[1]]

	def calcIou(self, box_2) -> float:
		# Slightly modified from https://machinelearningspace.com/intersection-over-union-iou-a-comprehensive-guide/
		#Extract bounding boxes coordinates
		x0_A, y0_A, x1_A, y1_A = self.getPoints()
		x0_B, y0_B, x1_B, y1_B = box_2.getPoints()
		
		# Get the coordinates of the intersection rectangle
		x0_I = max(x0_A, x0_B)
		y0_I = max(y0_A, y0_B)
		x1_I = min(x1_A, x1_B)
		y1_I = min(y1_A, y1_B)
		#Calculate width and height of the intersection area.
		width_I = x1_I - x0_I 
		height_I = y1_I - y0_I

		# Handle the negative value width or height of the intersection area
		width_I = 0 if width_I < 0 else width_I
		height_I = 0 if height_I < 0 else height_I
		# Calculate the intersection area:
		intersection = width_I * height_I
		# Calculate the union area:
		width_A, height_A = x1_A - x0_A, y1_A - y0_A
		width_B, height_B = x1_B - x0_B, y1_B - y0_B
		union = (width_A * height_A) + (width_B * height_B) - intersection
		# Calculate the IoU:
		return intersection/union
	
	def to_dict(self) -> dict:
		return {
			'top_left': {'x': self.top_left[0], 'y': self.top_left[1]},
			'bottom_right': {'x': self.bottom_right[0], 'y': self.bottom_right[1]},
		}

@dataclass
class Image(CgOBJ):
	def __init__(
			self, image_id: int, herd_unit_id: int, survey_id: int, name: str, img_key: str,
			in_training: bool, crops_generated: int, opened_by_user_id: int,
			created: datetime, modified: datetime, image_length_px: int, image_width_px: int,
			area: float, viewshed_polygon: List[List[float]], has_detection: bool, dem_name: str, 
			bbox_wsen: List[int], uuid: UUID
		):
		self.image_id = image_id
		self.herd_unit_id = herd_unit_id
		self.survey_id = survey_id
		self.img_key = img_key
		self.name = name
		self.in_training = in_training
		self.crops_generated = crops_generated
		self.opened_by_user_id = opened_by_user_id
		self.created = created
		self.modified = modified
		self.image_length_px = image_length_px
		self.image_width_px = image_width_px
		self.area = area
		#TODO: Change to use shapely.polygon class
		self.viewshed_polygon = viewshed_polygon
		self.has_detections = has_detection
		self.dem_name = dem_name 
		self.bbox_wsen = bbox_wsen
		self.uuid = uuid
		self.image = None

	def set_image(self, imageData: np.ndarray):
		if isinstance(imageData, bytes):
			try:
				pilImage = PillowImage.open(io.BytesIO(imageData))
				pilImage = pilImage.convert('RGB')
				self.image = cv2.cvtColor(np.array(pilImage), cv2.COLOR_RGB2BGR)
			except Exception as e:
				print(f"Error converting bytes to image: {e}")
				self.image = None
		elif isinstance(imageData, np.ndarray):
			self.image = imageData
		else:
			print(f"Unsupported type: {type(imageData)}")
			self.image = None

	def get_image(self) -> Optional[np.ndarray]:
		if self.image is not None:
			return self.image

	def deleteImage(self):
		del self.image

	def serve(self, img_format: str):
		if self.image is not None:
			_, self.img_encoded = cv2.imencode(img_format, self.get_image(), [cv2.IMWRITE_JPEG_QUALITY, 100]) #type: ignore
		else:
			raise Exception(f'{self.name} has no image data')
		return self.img_encoded.tobytes()
		
	def to_dict(self) -> dict:
		return {
			'image_id': self.image_id,
			'herd_unit_id': self.herd_unit_id,
			'survey_id': self.survey_id,
			'img_key': self.img_key,
			'name': self.name,
			'in_training': self.in_training,
			'crops_generated': self.crops_generated,
			'created': self.created,
			'modified': self.modified,
			'image_length_px': self.image_length_px,
			'image_width_px': self.image_width_px,
			'uuid': str(self.uuid)
		}

class Prediction(CgOBJ):
	def __init__(self, pred_id: int, image_id: int, model_id: int, label: int, score: float, box_tx: int, box_ty: int,
				box_bx: int, box_by: int, created: datetime | None, reviewed_by_user_id: int, uuid: UUID):
		self.pred_id = pred_id
		self.image_id = image_id
		self.model_id = model_id
		self.label = label
		self.score = score
		self.dimensions = Box((box_tx, box_ty), (box_bx, box_by))
		self.reviewed_by_user_id = reviewed_by_user_id
		self.created = created 
		self.uuid = uuid
	
	def to_dict(self) -> dict:
		return {
			'pred_id': self.pred_id,
			'image_id': self.image_id,
			'model_id': self.model_id,
			'dimensions': self.dimensions.to_dict(),
			'score': self.score,
			'label': self.label,
			'created': fmt(self.created),
			'reviewed_by_user_id': self.reviewed_by_user_id,
			'uuid': str(self.uuid)
		}
	
class Annotation(CgOBJ):
	def __init__(self, label_id: int, image_id: int, herd_unit_id: int,
				box_tx: int, box_ty: int, box_bx: int, box_by: int, annotation_id: int | None =None, created_by_user_id: int | None =None, 
				created: datetime | None =None, modified: datetime | None =None, uuid: UUID | None =None, pred_id: int | None=None):
		self.annotation_id = annotation_id
		self.label_id = label_id
		self.pred_id = pred_id
		self.image_id = image_id
		self.herd_unit_id = herd_unit_id
		self.dimensions = Box((box_tx, box_ty), (box_bx, box_by))
		self.created_by_user_id = created_by_user_id
		self.created = created
		self.modified = modified
		self.uuid = uuid
	
	def to_dict(self) -> dict:
		return {
			'annotation_id': self.annotation_id,
			'label_id': self.label_id,
			'image_id': self.image_id,
			'herd_unit_id': self.herd_unit_id,
			'dimensions': self.dimensions.to_dict(),
			'created': fmt(self.created),
			'modified': fmt(self.modified),
			'uuid': str(self.uuid)
		}


class ReviewedArea(Image):
	def __init__(self,  image_id: int, name: str,  area_tx: int, area_ty: int, area_bx: int, 
				area_by: int, reviewed_area_length_px: int, reviewed_area_width_px: int,
				reviewed_area_id: int | None = None, created: datetime | None = None , 
				modified: datetime | None = None, reviewed_by_user_id: int | None = None, 
				uuid: UUID | None = None, ra_key: str | None = None):
		self.reviewed_area_id = reviewed_area_id
		self.image_id = image_id
		self.name = name
		self.dimensions = Box((area_tx, area_ty), (area_bx, area_by))
		self.created = created
		self.modified = modified
		self.reviewed_area_length_px = abs(area_ty - area_by)
		self.reviewed_area_width_px = abs(area_tx - area_bx)
		self.reviewed_by_user_id = reviewed_by_user_id
		self.uuid = uuid
		self.ra_key = ra_key

	def to_dict(self) -> dict:
		return {
			'reviewed_area_id': self.reviewed_area_id,
			'image_id': self.image_id,
			'name': self.name,
			'dimensions': self.dimensions.to_dict(),
			'created': fmt(self.created),
			'modified': fmt(self.modified),
			'reviewed_area_length_px': self.reviewed_area_length_px,
			'reviewed_area_width_px': self.reviewed_area_width_px,
			'ra_key': self.ra_key,
			'uuid': str(self.uuid),
		}
	
class PredictionCrop(Image):
	def __init__(self, image_id: int, pred_id: int, name: str, score: float, label: int, dimensions: Box, 
				boundingBox: Box, uuid: UUID, url: Optional[str]=None):
		self.image_id = image_id
		self.pred_id = pred_id
		self.name = name
		self.score = score
		self.label = label 
		self.dimensions = dimensions
		self.boundingBox = boundingBox
		self.approved = False
		self.uuid = uuid
	
	def to_dict(self) -> dict:
		return {
			'image_id': self.image_id,
			'pred_id': self.pred_id,
			'name': self.name,
			'score': self.score,
			'label': self.label,
			'dimensions': self.dimensions.to_dict(),
			'boundingBox': self.boundingBox.to_dict(),
			'approved': self.approved,
			'uuid': str(self.uuid),
		}
#---------------------------------------------------------------------------------------------------------------------------#

class CropgenJSONPRovider(JSONProvider):
	def default(self, obj):
		if isinstance(obj, CgOBJ):
			return obj.to_dict()
		raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

#---------------------------------------------------------------------------------------------------------------------------#