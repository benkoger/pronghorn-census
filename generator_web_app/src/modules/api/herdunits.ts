// API methods for managing herd unit objects
// Author: Michael B. Lance

//---------------------------------------------------------------------------------------------------------------------------//

import {
	Image, Prediction, ReviewedArea, PredictionCrop, Project, Organization, User, Schema,
	Label, HerdUnit, Survey, Model, Annotation
} from '@/types/generatorobjects.ts';
import type { PredictionIntf, User_intf, ImageIntf, PredictionCrop_intf, ReviewedArea_intf, Annotation_intf, HerdUnitIntf } from '@/types/generatorobjects.ts';
import type { apiError } from '@/modules/api/apiV1Methods';


const api_url_base = import.meta.env.VITE_API_URL || 'https://pronghorn-count.arcc.uwyo.edu/api/v1';

const api_url: URL = new URL(api_url_base);

//---------------------------------------------------------------------------------------------------------------------------//

export async function createHerdUnit(project_id: number, name: string): Promise<HerdUnit> {
    const response = await fetch(`${api_url}/herd-units`, {
        method: 'POST',
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            'project_id': project_id,
            'name': name
        }),
    });
    if (!response.ok) throw new Error(`${(await response.json() as apiError).message}`);
        const resp = await response.json();
        let herd_unit = new HerdUnit(resp as HerdUnitIntf);
        return herd_unit;
}