// Methods for interacting with the version 1 of the crop generator API 
// Author: Michael B. Lance

//---------------------------------------------------------------------------------------------------------------------------//

import {
	Image, Prediction, ReviewedArea, PredictionCrop, Project, Label, Annotation
} from '@/types/generatorobjects.ts';
import type { PredictionIntf, UserIntf, ImageIntf, PredictionCropIntf } from '@/types/generatorobjects.ts';
import type { apiError } from '@/modules/api/errors.ts';


const api_url_base = import.meta.env.VITE_API_URL || 'https://pronghorn-count.arcc.uwyo.edu/api/v1';

export const api_url: URL = new URL(api_url_base);

//---------------------------------------------------------------------------------------------------------------------------//
// Project Crud



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
			const predCrop = row as PredictionCropIntf
			pred_crops.push(new PredictionCrop(
				predCrop,
				`${api_url}/request/image/${image_id}/pred_crop/${predCrop.uuid}`));
		}
		return pred_crops;
	} catch (error: any) {
		console.error("Error: ", error)
		return undefined;
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

		return false;
	}
}

//---------------------------------------------------------------------------------------------------------------------------//
// Area reviewing

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
		return false;
	}
}
