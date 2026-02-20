// API methods for managing image objects
// Author: Michael B. Lance

//---------------------------------------------------------------------------------------------------------------------------//

import { Image } from '@/types/generatorobjects.ts';
import type { ImageIntf } from '@/types/generatorobjects.ts';
import { ApiError } from '@/modules/api/errors.ts'

const api_url_base = import.meta.env.VITE_API_URL || 'https://pronghorn-count.arcc.uwyo.edu/api/v1';

const api_url: URL = new URL(api_url_base);

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
if (!response.ok) throw new ApiError(await response.json());

    return await response.json() as string;
}

//---------------------------------------------------------------------------------------------------------------------------//

export async function abortMultipartUpload(image_key: string, upload_id: string): Promise<string> {
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
    if (!response.ok) throw new ApiError(await response.json());

    return await response.json() as string;
}

//---------------------------------------------------------------------------------------------------------------------------//

interface uploadImagePartOptions {
    presigned_url: string;
    chunk_size: string;
    chunk_md5: string;
    chunk: Blob;
}

export async function uploadImagePart(options: uploadImagePartOptions ): Promise<string> {
    const response = await fetch(options.presigned_url, {
        method: 'PUT',
        headers: {
            'Content-Length': options.chunk_size,
            'Content-MD5': options.chunk_md5,
        },
        body: options.chunk
    });
    if (!response.ok) throw new Error(await response.json());
    
    const etag = response.headers.get("Etag");

    if (etag === null) throw new Error('No Etag Provided');
    return etag;
}