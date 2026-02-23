// API methods for managing survey objects
// Author: Michael B. Lance

//---------------------------------------------------------------------------------------------------------------------------//

import { HerdUnit, Survey } from '@/types/generatorobjects.ts';
import type { HerdUnitIntf, SurveyIntf } from '@/types/generatorobjects.ts';
import { ApiError } from '@/modules/api/errors.ts'
import { api_url } from '@/modules/api/apiV1Methods.ts';

//---------------------------------------------------------------------------------------------------------------------------//

export async function getSurveyHerdUnits(survey_id: string): Promise<HerdUnit[] | undefined> {
    const response = await fetch(`${api_url}/surveys/${survey_id}/herd-units`, {
        method: 'GET',
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json',
        },
    });
    if (!response.ok) throw new ApiError(await response.json());
    const resp = await response.json();
    let herd_units = [];
    for (const herd_unit of resp) herd_units.push(new HerdUnit(herd_unit as HerdUnitIntf));
    return herd_units;
}

//---------------------------------------------------------------------------------------------------------------------------//

export async function createSurvey(project_id: number, herd_unit_id: number, name: string, survey_date: string, additional_info: string): Promise<Survey> {
    const response = await fetch(`${api_url}/surveys`, {
        method: 'POST',
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            'project_id': project_id,
            'herd_unit_ids': [herd_unit_id],
            'survey_date': survey_date,
            'name': name,
            'additional_info': additional_info
        }),
    });
    if (!response.ok) throw new ApiError(await response.json());
    const resp = await response.json();
    let survey = new Survey(resp as SurveyIntf);
    return survey;
}