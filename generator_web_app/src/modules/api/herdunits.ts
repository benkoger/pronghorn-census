// API methods for managing herd unit objects
// Author: Michael B. Lance

//---------------------------------------------------------------------------------------------------------------------------//

import { HerdUnit } from '@/types/generatorobjects.ts';
import type { HerdUnitIntf } from '@/types/generatorobjects.ts';
import { ApiError } from '@/modules/api/errors.ts'

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
    if (!response.ok) throw new ApiError(await response.json());
    
    return new HerdUnit(await response.json() as HerdUnitIntf);
}