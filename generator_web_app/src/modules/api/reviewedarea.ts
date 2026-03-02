// API methods for managing reviewed area objects
// Author: Michael B. Lance

//---------------------------------------------------------------------------------------------------------------------------//

import { ReviewedArea } from '@/types/generatorobjects.ts';
import type { ReviewedAreaIntf } from '@/types/generatorobjects.ts';
import { ApiError } from '@/modules/api/errors.ts'
import { api_url } from '@/modules/api/apiV1Methods.ts';

//---------------------------------------------------------------------------------------------------------------------------//

interface getReviewedAreasOptions {
    'herd_unit_id': number[];
    'survey_id': number[];
    'include_reviewed': boolean;
}

export async function getReviewedAreas(options: getReviewedAreasOptions): Promise<ReviewedArea[]> {
    const params = new URLSearchParams()
    options.herd_unit_id.forEach(id => params.append('herd_unit_id', id.toString()));
    options.survey_id.forEach(id => params.append('survey_id', id.toString()));
    params.append('include_reviewed', options.include_reviewed.toString());

    const response = await fetch(`${api_url}/reviewed-area?${params}`, {
        method: 'GET',
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json'
        }
    });
    if (!response.ok) throw new ApiError(await response.json());
    const resp = await response.json();
    let reviewed_areas = [];
    for (const reviewed_area of resp) reviewed_areas.push(new ReviewedArea(reviewed_area as ReviewedAreaIntf));
    return reviewed_areas;
}   

//---------------------------------------------------------------------------------------------------------------------------//

export async function getRAPresignedUrl(ra_key: string): Promise<string> {
    const response = await fetch(`${api_url}/reviewed-area/presigned-get-url`, {
        method: 'POST',
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            'ra_key': ra_key
        }),
    });
    if (!response.ok) throw new ApiError(await response.json());

    return await response.text();
}