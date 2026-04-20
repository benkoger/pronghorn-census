// API methods for managing projects
// Author: Michael B. Lance

// ---------------------------------------------------------------------------------------------------------------------------

import { Project, Model, HerdUnit } from '@/types/generatorobjects.ts';
import type { ProjectIntf, ModelIntf , HerdUnitIntf} from '@/types/generatorobjects.ts';
import { ApiError } from '@/modules/api/errors.ts'
import { api_url } from '@/modules/api/apiV1Methods.ts';

// ---------------------------------------------------------------------------------------------------------------------------

export async function getAllProjects(): Promise<Project[]> {
  const response = await fetch(`${api_url}/projects`, {
	  method: 'GET',
	  credentials: 'include',
	  headers: {
		  'Content-Type': 'application/json',
	  },
	});
	if (!response.ok) throw new ApiError(await response.json());
	const resp = await response.json();
	let projects = [];
	for (const project of resp) projects.push(new Project(project as ProjectIntf));
	return projects;
}

// ---------------------------------------------------------------------------------------------------------------------------

export async function getProjectModels(project_id: string): Promise<Model[]> {
  const response = await fetch(`${api_url}/projects/${project_id}/models`, {
    method: 'GET',
    credentials: 'include',
    headers: {
            'Content-Type': 'application/json',
    },
    });
    if (!response.ok) throw new ApiError(await response.json());

    const resp = await response.json();
    let models = [];
    for (const model of resp) models.push(new Model(model as ModelIntf));

    return models;
}

// ---------------------------------------------------------------------------------------------------------------------------

export async function getProjectHerdUnits(project_id: string): Promise<HerdUnit[]> {
  const response = await fetch(`${api_url}/projects/${project_id}/herd-units`, {
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
