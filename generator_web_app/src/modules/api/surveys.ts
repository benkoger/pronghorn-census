// Methods for interacting with the version 1 of the crop generator API 
// Author: Michael B. Lance

//---------------------------------------------------------------------------------------------------------------------------//

import {
	Image, Prediction, ReviewedArea, PredictionCrop, Project, Organization, User, Schema,
	Label, HerdUnit, Survey, Model, Annotation
} from '@/types/generatorobjects.ts';
import type { PredictionIntf, User_intf, ImageIntf, PredictionCrop_intf, ReviewedArea_intf, Annotation_intf } from '@/types/generatorobjects.ts';
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
        for (const herd_unit of resp) herd_units.push(new HerdUnit(herd_unit));
        return herd_units;
    } catch (error: any) {
        console.error("Error: ", error)
        return undefined;
    }
}