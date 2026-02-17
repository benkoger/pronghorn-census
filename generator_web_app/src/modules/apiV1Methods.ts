// Methods for interacting with the version 1 of the crop generator API 
// Author: Michael B. Lance
// Created: April 20, 2025
// Updated: November 11, 2025
//---------------------------------------------------------------------------------------------------------------------------//

import {
	Image, Prediction, ReviewedArea, PredictionCrop, Project, Organization, User, Schema,
	Label, HerdUnit, Survey, Model, Annotation
} from '@/types/generatorobjects.ts';
import type { PredictionIntf, User_intf, ImageIntf, PredictionCrop_intf, ReviewedArea_intf, Annotation_intf } from '@/types/generatorobjects.ts';
import { useToast } from 'vue-toastification'


const api_url_base = import.meta.env.VITE_API_URL || 'https://pronghorn-count-dev.arcc.uwyo.edu/api/v1';
const api_url: URL = new URL(api_url_base);

const toast = useToast()

//---------------------------------------------------------------------------------------------------------------------------//

type apiError = {
	error: string
	message: string
	code: number
}

//---------------------------------------------------------------------------------------------------------------------------//
// User authentication
export async function authUser(external_id: string): Promise<User | undefined> {
	try {
		const response = await fetch(`${api_url}/authenticate`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
			},
			body: JSON.stringify({
				'external-id': external_id
			}),
			credentials: 'include',
		});
		if (!response.ok) throw new Error(`${(await response.json() as apiError).message}`)
		const user = new User(await response.json() as User_intf);
		return user;
	} catch (error: any) {
		console.error("Error: ", error)
		toast.error(`${error.message}`);
		return undefined;
	}
}

export async function checkAuth(): Promise<boolean> {
	try {
		const response = await fetch(`${api_url}/check_auth`, {
			method: 'GET',
			headers: {
				'Content-Type': 'application/json',
			},
			credentials: 'include',
		});
		if (response.status == 401) return false;
		if (!response.ok) throw new Error(`${(await response.json() as apiError).message}`)
		else return true;
	} catch (error: any) {
		console.error("Error: ", error)
		toast.error(`${error.message}`);
		return false;
	}
}

export async function getCurrentUser(): Promise<User | undefined> {
	try {
		const response = await fetch(`${api_url}/users/getCurrentUser`, {
			method: 'GET',
			headers: {
				'Content-Type': 'application/json',
			},
			credentials: 'include',
		});
		if (response.status == 401) return undefined;
		const user = new User(await response.json() as User_intf);
		return user;
	} catch (error: any) {
		console.error("Error: ", error)
		toast.error(`${error.message}`);
		return undefined;
	}
}

export async function deauthUser(): Promise<boolean> {
	try {
		const response = await fetch(`${api_url}/deauthenticate`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
			},
			credentials: 'include'
		});
		if (response.status == 200) {
			return true;
		} else {
			return false;
		}
	} catch (error: any) {
		console.error("Error: ", error)
		toast.error(`${error.message}`);
		return false;
	}
}

//---------------------------------------------------------------------------------------------------------------------------//
// Organization Crud

export async function getUserOrganizations(): Promise<Organization[] | undefined> {
	try {
		const response = await fetch(`${api_url}/request/organizations/all`, {
			method: 'GET',
			credentials: 'include',
			headers: {
				'Content-Type': 'application/json',
			},
		});
		if (!response.ok) throw new Error(`${(await response.json() as apiError).message}`)
		const resp = await response.json();
		let organizations = [];
		for (const organization of resp) organizations.push(new Organization(organization));
		return organizations;
	} catch (error: any) {
		console.error("Error: ", error)
		toast.error(`${error.message}`);
		return undefined;
	}
}

//---------------------------------------------------------------------------------------------------------------------------//
// Role Crud

//---------------------------------------------------------------------------------------------------------------------------//
//  User Crud

//---------------------------------------------------------------------------------------------------------------------------//
// Project Crud

export async function getProjects(): Promise<Project[] | undefined> {
	try {
		const response = await fetch(`${api_url}/request/projects/all`, {
			method: 'GET',
			credentials: 'include',
			headers: {
				'Content-Type': 'application/json',
			},
		});
		if (!response.ok) throw new Error(`${(await response.json() as apiError).message}`)
		const resp = await response.json();
		let projects = [];
		for (const project of resp) projects.push(new Project(project));
		return projects;
	} catch (error: any) {
		console.error("Error: ", error)
		toast.error(`${error.message}`);
		return undefined;
	}
}

//---------------------------------------------------------------------------------------------------------------------------//
// Schema Crud

export async function getProjectSchemas(project_id: string | undefined): Promise<Schema[] | undefined> {
	try {
		const response = await fetch(`${api_url}/request/projects/${project_id}/schemas/all`, {
			method: 'GET',
			credentials: 'include',
			headers: {
				'Content-Type': 'application/json',
			},
		});
		if (!response.ok) throw new Error(`${(await response.json() as apiError).message}`)
		const resp = await response.json();
		let schemas = [];
		for (const schema of resp) schemas.push(new Schema(schema));
		return schemas;
	} catch (error: any) {
		console.error("Error: ", error)
		toast.error(`${error.message}`);
		return undefined;
	}
}

//---------------------------------------------------------------------------------------------------------------------------//
// Label Crud

export async function getSchemaLabels(project_id: string | undefined, schema_id: string | undefined): Promise<Label[] | undefined> {
	try {
		const response = await fetch(`${api_url}/request/projects/${project_id}/schemas/${schema_id}/labels/all`, {
			method: 'GET',
			credentials: 'include',
			headers: {
				'Content-Type': 'application/json',
			},
		});
		if (!response.ok) throw new Error(`${(await response.json() as apiError).message}`)
		const resp = await response.json();
		let labels = [];
		for (const label of resp) labels.push(new Label(label));
		return labels;
	} catch (error: any) {
		console.error("Error: ", error)
		toast.error(`${error.message}`);
		return undefined;
	}
}

//---------------------------------------------------------------------------------------------------------------------------//
// Herd Unit Crud

export async function getProjectHerdUnits(project_id: string | undefined): Promise<HerdUnit[] | undefined> {
	try {
		const response = await fetch(`${api_url}/request/projects/${project_id}/herd_units/all`, {
			method: 'GET',
			credentials: 'include',
			headers: {
				'Content-Type': 'application/json',
			},
		});
		if (!response.ok) throw new Error(`${(await response.json() as apiError).message}`)
		const resp = await response.json();
		let herd_units = [];
		for (const herd_unit of resp) herd_units.push(new HerdUnit(herd_unit));
		return herd_units;
	} catch (error: any) {
		console.error("There was an error fetching the data:", error);
		toast.error(`${error.message}`);
		return undefined;
	}
}

export async function getCropperHerdUnits(survey_id: string | undefined): Promise<HerdUnit[] | undefined> {
	try {
		const response = await fetch(`${api_url}/request/surveys/${survey_id}/herd_units/all`, {
			method: 'GET',
			credentials: 'include',
			headers: {
				'Content-Type': 'application/json',
			},
		});
		if (!response.ok) throw new Error(`${(await response.json() as apiError).message}`)
		const resp = await response.json();
		let herd_units = [];
		for (const herd_unit of resp) herd_units.push(new HerdUnit(herd_unit));
		return herd_units;
	} catch (error: any) {
		console.error("Error: ", error)
		toast.error(`${error.message}`);
		return undefined;
	}
}

//---------------------------------------------------------------------------------------------------------------------------//
// Model Crud

export async function getProjectModels(project_id: string | undefined): Promise<Model[] | undefined> {
	try {
		const response = await fetch(`${api_url}/request/projects/${project_id}/models/all`, {
			method: 'GET',
			credentials: 'include',
			headers: {
				'Content-Type': 'application/json',
			},
		});
		if (!response.ok) throw new Error(`${(await response.json() as apiError).message}`)
		const resp = await response.json();
		let models = [];
		for (const model of resp) models.push(new Model(model));
		return models;
	} catch (error: any) {
		console.error("Error: ", error)
		toast.error(`${error.message}`);
		return undefined;
	}
}

export async function getCropperModels(survey_id: string | undefined, herd_unit_id: string | undefined, schema_id: string | undefined): Promise<Model[] | undefined> {
	try {
		const response = await fetch(`${api_url}/request/surveys/${survey_id}/herd_units/${herd_unit_id}/schemas/${schema_id}/models/all`, {
			method: 'GET',
			credentials: 'include',
			headers: {
				'Content-Type': 'application/json'
			},
		});
		if (!response.ok) throw new Error(`${(await response.json() as apiError).message}`)
		const resp = await response.json();
		let models = [];
		for (const model of resp) models.push(new Model(model));
		return models;
	} catch (error: any) {
		console.error("Error: ", error)
		toast.error(`${error.message}`);
		return undefined;
	}
}

//---------------------------------------------------------------------------------------------------------------------------//
// Survey Crud

export async function getProjectSurveys(project_id: string | undefined): Promise<Survey[] | undefined> {
	try {
		const response = await fetch(`${api_url}/request/projects/${project_id}/surveys/all`, {
			method: 'GET',
			credentials: 'include',
			headers: {
				'Content-Type': 'application/json',
			},
		});
		if (!response.ok) throw new Error(`${(await response.json() as apiError).message}`)
		const resp = await response.json();
		let surveys = [];
		for (const survey of resp) surveys.push(new Survey(survey));
		return surveys;
	} catch (error: any) {
		console.error("Error: ", error)
		toast.error(`${error.message}`);
		return undefined;
	}
}

//---------------------------------------------------------------------------------------------------------------------------//
// Image Crud

export async function createImage(project_id: string | undefined, survey_id: string | undefined,
	herd_unit_id: string | undefined, name: string, img_key: string, image_length: number, image_width: number
): Promise<Image | undefined> {
	try {
		const response = await fetch(`${api_url}/create/image`, {
			method: 'POST',
			credentials: 'include',
			headers: {
				'Content-Type': 'application/json',
			},
			body: JSON.stringify({
				'project_id': project_id,
				'survey_id': survey_id,
				'herd_unit_id': herd_unit_id,
				'img_key': img_key,
				'name': name,
				'image_length': image_length,
				'image_width': image_width,
			}),
		});
		if (!response.ok) throw new Error(`${(await response.json() as apiError).message}`)
		const resp = await response.json();
		const image = new Image(resp)
		return image;
	} catch (error: any) {
		console.error("Error: ", error)
		toast.error(`${error.message}`);
		return undefined;
	}
}

//---------------------------------------------------------------------------------------------------------------------------//
// Multipart image upload

export async function createMultiPartUpload(image_key: string): Promise<string | undefined> {
	try {
		const response = await fetch(`${api_url}/upload/image/create_multipart_upload`, {
			method: 'POST',
			credentials: 'include',
			headers: {
				'Content-Type': 'application/json',
			},
			body: JSON.stringify({
				'image_key': image_key,
			}),
		});
		if (!response.ok) throw new Error(`${(await response.json() as apiError).message}`)
		const resp = await response.json();
		return resp.upload_id as string;
	} catch (error: any) {
		console.error("There was an error creating the upload:", error);
		toast.error(`${error.message}`);
		return undefined;
	}
}

export async function getImagePresignedPostUrl(upload_id: string, part_number: number, image_key: string, chunk_size: number, chunk_md5: string): Promise<string | undefined> {
	try {
		const response = await fetch(`${api_url}/create/image/presigned-put-url`, {
			method: 'POST',
			credentials: 'include',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				'upload_id': upload_id,
				'part_number': part_number,
				'image_key': image_key,
				'chunk_size': chunk_size,
				'chunk_md5': chunk_md5,
			}),
		});
		if (!response.ok) throw new Error(`${(await response.json() as apiError).message}`);
		const resp = await response.json();
		return resp as string;
	} catch (error: any) {
		console.error("Error: ", error)
		toast.error(`${error.message}`);
		return undefined;
	}
}

export async function abortMultipartUpload(image_key: string, upload_id: string): Promise<string | undefined> {
	try {
		const response = await fetch(`${api_url}/upload/image/abort`, {
			method: 'POST',
			credentials: 'include',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				'image_key': image_key,
				'upload_id': upload_id,
			}),
		});
		if (!response.ok) throw new Error(`${(await response.json() as apiError).message}`)
		const resp = await response.json()
		return resp as string;
	} catch (error: any) {
		console.error("There was an error aborting the multipart upload:", error);
		toast.error(`${error.message}`);
		return undefined;
	}
}

export async function completeMultiPartUpload(image_key: string, parts: any[], upload_id: string): Promise<string | undefined> {
	try {
		const response = await fetch(`${api_url}/upload/image/complete`, {
			method: 'POST',
			credentials: 'include',
			headers: {
				'Content-Type': 'application/json',
			},
			body: JSON.stringify({
				'image_key': image_key,
				'parts': parts,
				'upload_id': upload_id
			}),
		});
		if (!response.ok) throw new Error(`${(await response.json() as apiError).message}`);
		return await response.json() as string;
	} catch (error: any) {
		console.error("Error: ", error)
		toast.error(`${error.message}`);
		return undefined;
	}

}

//---------------------------------------------------------------------------------------------------------------------------//
// Auto Cropping

export async function fetchAutoCropperBatch(survey_id: string | undefined, herd_unit_id: string | undefined, size: number,
	score: number, labels: number[] | undefined, model_id: string | undefined): Promise<[Image[], Prediction[][]] | undefined> {
	try {
		const response = await fetch(`${api_url}/create/auto-crop-batch`, {
			method: 'POST',
			credentials: 'include',
			headers: {
				'Content-Type': 'application/json',
			},
			body: JSON.stringify({
				'survey_id': survey_id,
				'herd_unit_id': herd_unit_id,
				'size': size,
				'score': score,
				'labels': labels,
				'model_id': model_id,
			}),
		});
		if (!response.ok) throw new Error(`${(await response.json() as apiError).message}`);
		const resp = await response.json();
		const images: Image[] = [];
		const predictions: Prediction[][] = [];
		for (const img of resp) {
			images.push(new Image(img as ImageIntf));
			const preds: Prediction[] = []
			for (const pred of img['predictions']) {
				preds.push(new Prediction(pred as PredictionIntf))
			}
			predictions.push(preds);
		}
		return [images as Image[], predictions as Prediction[][]];
	} catch (error: any) {
		console.error("Error: ", error)
		toast.error(`${error.message}`);
		return undefined;
	}

}

export async function fetchPredCrops(image_id: string | undefined, survey_id: string | undefined,
	herd_unit_id: string | undefined, predictions: Prediction[] | undefined): Promise<PredictionCrop[] | undefined> {
	try {
		const response = await fetch(`${api_url}/create/predictionCrops`, {
			method: 'POST',
			credentials: 'include',
			headers: {
				'Content-Type': 'application/json',
			},
			body: JSON.stringify({
				'image_id': image_id,
				'survey_id': survey_id,
				'herd_unit_id': herd_unit_id,
				'predictions': predictions,
			}),
		});
		if (!response.ok) throw new Error(`${(await response.json() as apiError).message}`)
		const resp = await response.json();
		const pred_crops: PredictionCrop[] = []
		for (const row of resp) {
			const predCrop = row as PredictionCrop_intf
			pred_crops.push(new PredictionCrop(
				predCrop,
				`${api_url}/request/image/${image_id}/pred_crop/${predCrop.uuid}`));
		}
		return pred_crops;
	} catch (error: any) {
		console.error("Error: ", error)
		toast.error(`${error}`);
		return undefined;
	}
}

export async function closeImage(image_id: string): Promise<boolean> {
	try {
		const response = await fetch(`${api_url}/update/image/set-closed`, {
			method: 'POST',
			credentials: 'include',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				'image_id': image_id,
			}),
		});
		if (!response.ok) {
			throw new Error(`${(await response.json() as apiError).message}`);
		} else {
			return true;
		}
	} catch (error: any) {
		console.error("Error: ", error);
		toast.error(`${error}`);
		return false;
	}
}

export async function setPredicionsReviewed(prediction_ids: string[]): Promise<boolean> {
	try {
		const response = await fetch(`${api_url}/update/predictions/set-reviewed`, {
			method: 'POST',
			credentials: 'include',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				'prediction_ids': prediction_ids
			}),
		});
		if (!response.ok) {
			throw new Error(`${(await response.json() as apiError).message}`);
		} else {
			return true;
		}
	} catch (error: any) {
		console.error("Error: ", error);
		toast.error(`${error}`);
		return false;
	}
}

export async function autoCrop(image_uuid: string, predictions: Prediction[], herd_unit_id: string, survey_id: string, labels: Label[]): Promise<boolean> {
	try {
		const response = await fetch(`${api_url}/create/reviewed-area-and-annotations`, {
			method: 'PUT',
			credentials: 'include',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				'image_uuid': image_uuid,
				'predictions': predictions,
				'herd_unit_id': herd_unit_id,
				'survey_id': survey_id,
				'labels': labels
			}),
		});
		if (!response.ok) {
			throw new Error(`${(await response.json() as apiError).message}`);
		} else {
			return true;
		}
	} catch (error: any) {
		console.error("Error: ", error)
		toast.error(`${error}`);
		return false;
	}
}

export async function closeCropSession(): Promise<boolean> {
	try {
		const response = await fetch(`${api_url}/end/crop_session`, {
			method: 'POST',
			credentials: 'include',
			headers: {
				'Content-Type': 'application/json'
			}
		});
		if (!response.ok) {
			throw new Error(`${(await response.json() as apiError).message}`);
		} else {
			return true;
		}

	} catch (error: any) {
		console.error("Error: ", error)
		toast.error(`${error}`);
		return false;
	}

}

//---------------------------------------------------------------------------------------------------------------------------//
// Area reviewing

export async function fetchReviewedArea(herd_unit_id: string | undefined, survey_id: string | undefined): Promise<ReviewedArea | undefined> {
	try {
		const response = await fetch(`${api_url}/create/reviewed-area-batch`, {
			method: 'POST',
			credentials: 'include',
			headers: {
				'Content-Type': 'application/json',
			},
			body: JSON.stringify({
				'herd_unit_id': herd_unit_id,
				'survey_id': survey_id,
			}),
		});
		if (!response.ok) throw new Error(`${(await response.json() as apiError).message}`);

		const resp = await response.json();
		let revieweArea = new ReviewedArea(resp as ReviewedArea_intf);
		return revieweArea as ReviewedArea;

	} catch (error: any) {
		console.error("Error: ", error)
		toast.error(`${error}`);
		return undefined;
	}
}

export async function getReviewedAreaPresignedGetUrl(ra_key: string): Promise<string | undefined> {
	try {
		const response = await fetch(`${api_url}/create/reviewed-area/presigned-get-url`, {
			method: 'POST',
			credentials: 'include',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				'ra_key': ra_key
			}),
		});
		if (!response.ok) throw new Error(`${(await response.json() as apiError).message}`);
		const resp = await response.json();
		return resp as string;
	} catch (error: any) {
		console.error("Error: ", error)
		toast.error(`${error.message}`);
		return undefined;
	}
}

export async function getReviewedAreaAnnotations(ra_id: string): Promise<Annotation[] | undefined> {
	try {
		const response = await fetch(`${api_url}/get/reviewed-area/${ra_id}/annotations`, {
			method: 'GET',
			credentials: 'include',
			headers: {
				'Content-Type': 'application/json'
			},
		});
		if (!response.ok) throw new Error(`${(await response.json() as apiError).message}`);
		const resp = await response.json();
		let annotations: Annotation[] = [];
		for (const annot of resp) annotations.push(new Annotation(annot));
		return annotations;

	} catch (error: any) {
		console.error("Error: ", error)
		toast.error(`${error.message}`);
		return undefined;
	}
}

export async function submitApprovedAreaAnnotations(reviewedArea: ReviewedArea, annotations: Annotation[], deletedAnnotations: Annotation[]): Promise<boolean> {
	try {
		const response = await fetch(`${api_url}/update/reviewed-area/approve-annotations`, {
			method: 'POST',
			credentials: 'include',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				reviewed_area: reviewedArea,
				annotations: annotations,
				deleted_annotations: deletedAnnotations,
			})
		});
		if (!response.ok) {
			throw new Error(`${(await response.json() as apiError).message}`);
		} else {
			return true;
		}

	} catch (error: any) {
		console.error("Error: ", error)
		toast.error(`${error.message}`);
		return false;
	}
}