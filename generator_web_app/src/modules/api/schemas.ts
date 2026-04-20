// API methods for managing schema objects
// Author: Michael B. Lance

// ---------------------------------------------------------------------------------------------------------------------------

import { Schema, Label } from '@/types/generatorobjects.ts';
import type { SchemaIntf, LabelIntf } from '@/types/generatorobjects.ts';
import { ApiError } from '@/modules/api/errors.ts'
import { api_url } from '@/modules/api/apiV1Methods.ts';

// ---------------------------------------------------------------------------------------------------------------------------

export async function getSchemaLabels(schema_id: string): Promise<Label[]> {
    const response = await fetch(`${api_url}/schemas/${schema_id}/labels`, {
        method: 'GET',
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json'
        },
    });
    if (!response.ok) throw new ApiError(await response.json());
    const resp = await response.json();
    let labels = [];
    for (const label of resp) labels.push(new Label(label as Label));
    return labels;
}