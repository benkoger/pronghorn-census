# Generate high quality crops of training data with model assisted labeling and Kmeans clustering
# Authors: Ben Koger, Michael B. Lance
# Created: November 11, 2024
# Updated: September 5, 2025

#---------------------------------------------------------------------------------------------------------------------------#

import cv2
import matplotlib.pyplot as plt
import numpy as np
from ..generatorobjects.generatorobjects import Box, HerdUnit, Model, Prediction, PredictionCrop, Image, ReviewedArea,\
Annotation
from sklearn.cluster import KMeans
from uuid import UUID
from typing import Any, List

#---------------------------------------------------------------------------------------------------------------------------#

# def load_training_image_names(train_json_path: str, prefix: str, suffix:str, crop_suffix: bool = False) -> set:
# 	''' Loads training image names into a list

# 	Returns a set of filenames that were used to train the model 
# 	''' 
# 	with open(train_json_path) as f:
# 		train_json = json.load(f)
# 	if crop_suffix:
# 		return set(os.path.splitext(image_info['file_name'])[0][prefix:] for image_info in train_json['images'])
# 	else:
# 		return set(os.path.splitext(image_info['file_name'])[0][prefix:-suffix] for image_info in train_json['images'])

#---------------------------------------------------------------------------------------------------------------------------#

# def load_prediction(image_name: str, model: Model, source_folder: str) -> list[Prediction]:
# 	''' Load model predictions for a given image name

# 	Args:
# 		image_file: string file path to an image

# 	Returns a dictionary containing the predictions
# 	'''
# 	# Get corresponding box file for image
# 	predictions_folder = os.path.join(source_folder, model.name, 'data')
# 	box_file = os.path.join(predictions_folder, f'{image_name}_boxes.npy') #type: ignore


# 	if not os.path.exists(box_file):
# 		raise Exception(f'{image_name} missing box file.')
# 	else:
# 		boxes = np.load(box_file)
# 	# Get corresponding score file for image
# 	score_file = os.path.join(predictions_folder, f'{image_name}_scores.npy') #type: ignore
# 	if not os.path.exists(score_file):
# 		raise Exception(f'{image_name} missing score file.')
# 	else:
# 		scores = np.load(score_file)
# 	# Get corresponding object class file for image
# 	label_file = os.path.join(predictions_folder, f'{image_name}_labels.npy') #type: ignore
# 	if not os.path.exists(label_file):
# 		raise Exception(f'{image_name} missing labels file.')
# 	else:
# 		labels = np.load(label_file)

# 	predictions = []

# 	for box, score, label in zip(boxes, scores, labels):
# 		if len(box) == 0:
# 			print('empty box')
# 			continue
# 		pred = Prediction(
# 			model = model,
# 			dimensions = Box (top_left=(int(box[0]),int(box[1])), bottom_right=(int(box[2]),int(box[3]))),
# 			score = float(score),
# 			label = int(label),
# 		)
# 		predictions.append(pred)
# 	return predictions

#---------------------------------------------------------------------------------------------------------------------------#

# def load_from_npy(herd_unit: HerdUnit, model: Model, source_folder: str) -> list[dict[Image, Prediction]]:
# 	''' Create Image and Predictions objects from .npy files

# 	Returns a dictionary contianing images and predictions
# 	'''

# 	images_folder = os.path.join(source_folder, 'Images', herd_unit.survey_year, herd_unit.name)
# 	train_json_path = os.path.join(source_folder, model.name, 'annotations', 'train.json')
# 	image_files = sorted(glob.glob(os.path.join(images_folder, f'*.[jJ][pP][gG]'))) # type: ignore
# 	training = load_training_image_names(train_json_path, len("high-altitude-pronghorn-survey-"), len("_crop_xx"))
# 	print(f'{len(image_files)} files found.')
# 	images = []
# 	for image_file in image_files:
# 		image_name = os.path.splitext(os.path.basename(image_file))[0]
# 		image = Image (
# 			name = image_name,
# 			herd_unit = herd_unit,
# 			in_training= True if image_name in training else False,
# 			local_path= images_folder,
# 		)
# 		try:
# 			predictions = load_prediction(image_name, model, source_folder)
# 		except Exception as e:
# 			print(e)
# 			continue
# 		image_dict = {
# 			'image': image,
# 			'predictions': predictions
# 		}
# 		images.append(image_dict.copy())

# 	return images

#---------------------------------------------------------------------------------------------------------------------------#

def sort_by_class_confidence(predictions: list, pred_class: int, minConfidence: float) -> list[str]:
	''' Sort a list of predictions based on confidence scores for a given class (not really useful with database)
	
	Args:
		predictions: list of predictions (dictionary)
		pred_class: integer representing a desired class
		minConfidence: floating point value for the min score to show predictions
	
	Returns a list of predictions sorted by confidence 
	'''
	count = 0
	for pred in predictions:
		pred['max_class_score'] = -1
		if len(pred['labels']) == 0:
			continue
		is_class = pred['labels'] == pred_class
		if not np.any(is_class):
			continue
		max_score = np.max(pred['scores'][is_class])
		pred['max_class_score'] = max_score
		if max_score > minConfidence:
			count += 1
	print(f'{count} images with pronghorn above min confidence score.')

	# Sort images based on max pronghorn score
	predictions = sorted(predictions, key=lambda x: x['max_class_score'], reverse=True)
	return predictions

#---------------------------------------------------------------------------------------------------------------------------#

def auto_crop(image: Image, predictions: list[Prediction], labels_ids: dict[int, int], num_clusters: int=1, crop_size: int=2100) -> list[List[ReviewedArea | list[Annotation]]]:
	''' Automatically create crops of a given size containing all images with approved annotations 
	
	Args:
		image: source image that predictions were made from
		points: List of coordinate points of the approximate center for each prediction associated with the image
		crop_size: dimension for crop (note only square crops are currently supported)
		num_clusters: number of centers for kmeans to determine clusters 

	Returns list of crops based on original image
	'''
	
	points = []
	centers = []
	crops = [] # Structure to be returned
	img = image.getImage()
	if img is None:
		raise Exception('could not get image')

	# Get centers for all predictions 
	for pred in predictions:
		points.append(pred.dimensions.getCenter())

	if len(points) == 0:
		print('no points')
		return crops
	elif len(points) == 1:
		centers.append(points[0])

	elif num_clusters == 1:
		x_min = x_max = int(points[0][0])
		y_min = y_max = int(points[0][1])
		for point in points:
			x_min = min(x_min, int(point[0]))
			x_max = max(x_max, int(point[0]))
			y_min = min(y_min, int(point[1]))
			y_max = max(y_max, int(point[1]))

		if (x_max - x_min <= 2100 ) and (y_max - y_min <= 2100):
			x_center = (x_min + x_max) // 2
			y_center = (y_min + y_max) // 2 
			centers.append([x_center, y_center])
	
	elif num_clusters > 1:
		points_array = np.array(points)
		kmeans = KMeans(n_clusters = num_clusters)
		if len(points) >= num_clusters:
			kmeans.fit(points_array)
		else:
			#TODO Raise an error
			return crops 

		centers = kmeans.cluster_centers_

	points_in_crop = np.zeros(len(points))

	for crop_num, center in enumerate(centers):
		x_start = max(0, int(center[0]) - crop_size // 2)
		y_start = max(0, int(center[1]) - crop_size // 2)
		x_end = min(img.shape[1], x_start + crop_size)
		y_end = min(img.shape[0], y_start + crop_size)
	
		if x_end == img.shape[1]:
			x_start -= (x_start + crop_size) - img.shape[1]

		if y_end == img.shape[0]:
			y_start -= (y_start + crop_size) - img.shape[0]
		
		crop = ReviewedArea(
			image_id = image.image_id,
			name = f'{image.name[0:50]}_crop_{crop_num}.JPG',
			area_tx =  x_start,
			area_ty = y_start,
			area_bx = x_end,
			area_by = y_end,
			reviewed_area_length_px = abs(y_start - y_end),
			reviewed_area_width_px= abs(x_start - x_end)
		)
		crop.setImage(img[y_start:y_end, x_start:x_end].copy())
		annotations = []

		for p_index, pred in enumerate(predictions):
			box = pred.dimensions.getPoints()
			if ((box[0] >= x_start) and (box[2] <= x_end)) and ((box[1] >= y_start) and (box[3] <= y_end)): 
				points_in_crop[p_index] += 1
				annotations.append(Annotation(
					label_id = labels_ids[pred.label],
					image_id = image.image_id,
					herd_unit_id = image.herd_unit_id,
					box_tx = box[0],
					box_ty = box[1],
					box_bx = box[2],
					box_by = box[3],
				))
		
		crops.append([crop, annotations])

	if np.all(points_in_crop >= 1):
		return crops

	elif num_clusters + 1 <= len(points):
		return auto_crop(image=image, predictions=predictions, labels_ids=labels_ids, crop_size=crop_size, num_clusters=num_clusters +1)

	else:
		raise Exception('Could not generate any crops...')
		return crops 
	
#---------------------------------------------------------------------------------------------------------------------------#

def create_subcrop(image: Image, predictions: list[dict[str, Any]], crop_size: int=150, drawBox: bool=False) -> list[PredictionCrop]:
		crops = []
		img = image.getImage()
		if len(predictions) == 0:        
			raise Exception('Predictions cannot be zero')
		
		if img is None:
			raise Exception('Could not get image')

		img_height, img_width = img.shape[:2]

		for pred in predictions:
			box = pred['dimensions']['top_left'] + pred['dimensions']['bottom_right']
			center_x = (box[0] + box[2]) / 2
			center_y = (box[1] + box[3]) / 2

			xmin = int(center_x - crop_size)
			ymin = int(center_y - crop_size)
			xmax = int(center_x + crop_size)
			ymax = int(center_y + crop_size)

			if xmin < 0:
				xmax -= xmin 
				xmin = 0
			elif xmax > img_width:
				xmin -= (xmax - img_width) 
				xmax = img_width
				
			if ymin < 0:
				ymax -= ymin  
				ymin = 0
			elif ymax > img_height:
				ymin -= (ymax - img_height) 
				ymax = img_height

			crop = PredictionCrop(
				image_id = image.image_id,
				pred_id = pred['pred_id'],
				name = f'{image.name}_pred_crop_{pred['uuid']}',
				score = pred['score'],
				label = pred['label'],
				dimensions = Box((int(xmin), int(ymax)), (int(xmax), int(ymin))),
				boundingBox = Box((int(box[0] - xmin), int(box[1] - ymin)), (int(box[2] - xmin), int(box[3] - ymin))),
				uuid = pred['uuid']
			)
			crop.setImage(img[ymin:ymax, xmin:xmax].copy())
			crops.append(crop)

			if drawBox:
				cv2.rectangle(img, (box[0], box[1]), (box[2], box[3]), (255, 0, 0), 3)

		return crops

#---------------------------------------------------------------------------------------------------------------------------#

# def generate_crops(image: Image, predictions: list[Prediction], crop_size: int, model_id: int,
#                    base: database.Database) -> dict[Crop, list[Prediction]]:
#     ''' Present the user with cropped images and their predictions for validation '''

#     crops = auto_crop(image=image, predictions=predictions, crop_size=crop_size)  
#     query = '''
#         SELECT *
#         FROM Crops
#         WHERE ModelID != ? AND ImageId = ?
#     '''
#     #TODO: Move IOU check to own function that takes both 
#     """
#     existing_crops = base.query(query, (model_id, image.id))

#     # Perform Iou check to prevent duplicate data
#     for crop in crops.keys():
#         for ecrop in existing_crops:
#             if crop.calcIou(Box(ecrop[5], ecrop[6], ecrop[7], ecrop[8])) >= 0.9:
#                 print('duplicate crop')
#                 crops.pop(crop, None)
#     """
#     return crops

#---------------------------------------------------------------------------------------------------------------------------#

# def save_crop(crop: Crop, save_folder: str):
# 		cv2.imwrite(f'{save_folder}/{crop.name}.jpg', cv2.cvtColor(crop.getImage(), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 100])

#---------------------------------------------------------------------------------------------------------------------------#
