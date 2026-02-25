// API methods for the crop verifier
// Author: Michael B. Lance

//---------------------------------------------------------------------------------------------------------------------------//

import { ReviewedArea } from '@/types/generatorobjects.ts';
import type { ReviewedAreaIntf } from '@/types/generatorobjects.ts';
import { ApiError } from '@/modules/api/errors.ts'
import { api_url } from '@/modules/api/apiV1Methods.ts';

//---------------------------------------------------------------------------------------------------------------------------//

interface getReviewedAreaOptions {
    'herd_unit_id': number[];
    'survey_id': number[];
    'include_reviewed': boolean;
}

export async function getReviewedArea(options: getReviewedAreaOptions): Promise<ReviewedArea> {
    const params = new URLSearchParams()
    options.herd_unit_id.forEach(id => params.append('herd_unit_id', id.toString()));
    options.survey_id.forEach(id => params.append('survey_id', id.toString()));
    params.append('include_reviewed', options.include_reviewed.toString());

    const response = await fetch(`${api_url}/verifier/reviewed-area?${params}`, {
        method: 'GET',
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json'
        }
    });
    if (!response.ok) throw new ApiError(await response.json());
    return new ReviewedArea(await response.json() as ReviewedAreaIntf);
}   
