// API methods for managing survey objects
// Author: Michael B. Lance

//---------------------------------------------------------------------------------------------------------------------------//

import { HerdUnit, Survey } from '@/types/generatorobjects.ts';
import type { HerdUnitIntf, Survey_intf } from '@/types/generatorobjects.ts';
import type { apiError } from '@/modules/api/apiV1Methods';

const api_url_base = import.meta.env.VITE_API_URL || 'https://pronghorn-count.arcc.uwyo.edu/api/v1';

const api_url: URL = new URL(api_url_base);

//---------------------------------------------------------------------------------------------------------------------------//

export async function getSurveyHerdUnits(survey_id: string): Promise<HerdUnit[] | undefined> {
    try {
        const response = await fetch(`${api_url}/surveys/${survey_id}/herd-units`, {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
            },
        });
        if (!response.ok) throw new Error(`${(await response.json() as apiError).message}`)
        const resp = await response.json();
        let herd_units = [];
        for (const herd_unit of resp) herd_units.push(new HerdUnit(herd_unit as HerdUnitIntf));
        return herd_units;
    } catch (error: any) {
        console.error("Error: ", error)
        return undefined;
    }
}

//---------------------------------------------------------------------------------------------------------------------------//

export async function createSurvey(project_id: number, herd_unit_id: number, name: string, survey_date: string, additional_info: string): Promise<Survey> {
    console.log(survey_date)
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
    if (!response.ok) throw new Error(`${(await response.json() as apiError).message}`);
    const resp = await response.json();
    let survey = new Survey(resp as Survey_intf);
    return survey;
}