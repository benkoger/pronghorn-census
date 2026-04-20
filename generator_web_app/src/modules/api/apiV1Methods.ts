// Methods for interacting with the version 1 of the crop generator API 
// Author: Michael B. Lance

// ---------------------------------------------------------------------------------------------------------------------------

import {
	Prediction, ReviewedArea, Label, Annotation
} from '@/types/generatorobjects.ts';
import type { apiError } from '@/modules/api/errors.ts';

const api_url_base = import.meta.env.VITE_API_URL || 'https://pronghorn-count.arcc.uwyo.edu/api/v1';

export const api_url: URL = new URL(api_url_base);




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
