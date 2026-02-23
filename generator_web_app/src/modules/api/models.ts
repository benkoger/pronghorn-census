// API methods for managing models
// Author: Michael B. Lance

//---------------------------------------------------------------------------------------------------------------------------//

import { Schema, Label } from '@/types/generatorobjects.ts';
import type { SchemaIntf, LabelIntf} from '@/types/generatorobjects.ts';
import { ApiError } from '@/modules/api/errors.ts'
import { api_url } from '@/modules/api/apiV1Methods.ts';

//---------------------------------------------------------------------------------------------------------------------------//

export async function getModelSchema(model_id: string): Promise<Schema> {
    const response = await fetch(`${api_url}/models/${model_id}/schema`, {
        method: 'GET',
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json',
        },
    });
    if (!response.ok) throw new ApiError(await response.json());

    return new Schema(await response.json() as SchemaIntf)
}