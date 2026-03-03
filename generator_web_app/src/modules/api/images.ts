// API methods for managing image objects
// Author: Michael B. Lance

//---------------------------------------------------------------------------------------------------------------------------//

import { Image } from '@/types/generatorobjects.ts';
import type { ImageIntf } from '@/types/generatorobjects.ts';
import { ApiError } from '@/modules/api/errors.ts'
import { api_url } from '@/modules/api/apiV1Methods.ts';

//---------------------------------------------------------------------------------------------------------------------------//

interface createImageOptions{
	survey_id: string | number;
	herd_unit_id: string | number;
	name: string;
	img_key: string;
	image_length_px: number;
	image_width_px: number;
}

export async function createImage(options: createImageOptions): Promise<Image> {
		const response = await fetch(`${api_url}/images`, {
			method: 'POST',
			credentials: 'include',
			headers: {
				'Content-Type': 'application/json',
			},
			body: JSON.stringify(options),
		});
		if (!response.ok) throw new ApiError(await response.json());

		return new Image(await response.json() as ImageIntf);
}

//---------------------------------------------------------------------------------------------------------------------------//

interface presignedPutOptions {
	upload_id: string;
	part_number: number;
	image_id: number | string;
	chunk_size: number;
	chunk_md5: string;
}

export async function createImagePresignedPut(options: presignedPutOptions): Promise<string> {

	const response = await fetch(`${api_url}/images/presigned-put-url`, {
		method: 'POST',
		credentials: 'include',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify(options),
	});
	if (!response.ok) throw new ApiError(await response.json());
	
	return await response.text();
}

//---------------------------------------------------------------------------------------------------------------------------//

export async function createMultiPartUpload(image_key: string): Promise<string> {

	const response = await fetch(`${api_url}/images/create-multipart-upload`, {
		method: 'POST',
		credentials: 'include',
		headers: {
			'Content-Type': 'application/json',
		},
		body: JSON.stringify({
			'image_key': image_key,
		}),
	});
	if (!response.ok) throw new ApiError(await response.json());

	return await response.text()
}

//---------------------------------------------------------------------------------------------------------------------------//

export async function completeMultiPartUpload(image_key: string, parts: any[], upload_id: string): Promise<string> {
	const response = await fetch(`${api_url}/images/complete-multipart-upload`, {
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
if (!response.ok) throw new ApiError(await response.json());

	return await response.json() as string;
}

//---------------------------------------------------------------------------------------------------------------------------//

export async function abortMultipartUpload(image_key: string, upload_id: string): Promise<string> {
	const response = await fetch(`${api_url}/images/abort-multipart-upload`, {
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
	if (!response.ok) throw new ApiError(await response.json());

	return await response.json() as string;
}

//---------------------------------------------------------------------------------------------------------------------------//

export interface updateImageOptions {
	name?: string;
	herd_unit_id?: number;
	survey_id?: number;
	img_key?: string;
	image_length_px?: number;
	image_width_px?: number;
	area?: number;
	viewshed_polygon?: number[][];
	has_detection?: boolean;
	dem_name?: string;
	bbox_wsen?: number[]; 
	opened_by_user_id?: number; 
}

export async function updateImage(image_id: string, options: updateImageOptions): Promise<Image> {
	const response = await fetch(`${api_url}/images/${image_id}`, {
		method: 'PATCH',
		credentials: 'include',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify(options),
	});
	if (!response.ok) throw new ApiError(await response.json());
	
	return new Image(await response.json() as ImageIntf);

}

//---------------------------------------------------------------------------------------------------------------------------//

export async function closeUserImages(): Promise<boolean> {
	const response = await fetch(`${api_url}/images/close-user-images`, {
		method: 'PATCH',
		credentials: 'include',
		headers: {
			'Content-Type': 'application/json'
		},
	});
	if (!response.ok) throw new ApiError(await response.json());

	return true;
}

//---------------------------------------------------------------------------------------------------------------------------//

export async function deleteImage(image_id: string): Promise<boolean> {
	const response = await fetch(`${api_url}/images/${image_id}`, {
		method: 'DELETE',
		credentials: 'include',
		headers: {
			'Content-Type': 'application/json'
		},
	});
	if (!response.ok) throw new ApiError(await response.json());

	return true;
}

//---------------------------------------------------------------------------------------------------------------------------//
