// API methods for managing projects
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

import { apiClient } from "./client";
import {
  Project,
  Model,
  HerdUnit,
  Schema,
  type ProjectIntf,
  type ModelIntf,
  type HerdUnitIntf,
  type SchemaIntf,
} from "@/types/models";

// ---------------------------------------------------------------------------------------------------------------------------

export interface createProjectOptions {
  name: string;
  organization_id: string;
}

// ---------------------------------------------------------------------------------------------------------------------------
// GET

export async function getAllProjects(): Promise<Project[]> {
  return apiClient.getAll("projects", Project);
}

export async function getProject(projectId: string | number): Promise<Project> {
  return apiClient.get("projects", projectId, Project);
}

export async function getProjectModels(projectId: string): Promise<Model[]> {
  return apiClient.getChildren("projects", projectId, "models", Model);
}

export async function getProjectHerdUnits(projectId: string): Promise<HerdUnit[]> {
  return apiClient.getChildren("projects", projectId, "herd-units", HerdUnit);
}

export async function getProjectSchemas(projectId: string): Promise<Schema[]> {
  return apiClient.getChildren("projects", projectId, "schemas", Schema);
}

export async function getProjectImageCount(projectId: string): Promise<number> {
  const resp = await apiClient.get<{ count: number }>(
    "projects",
    `${projectId}/image-count`,
  );
  return resp?.count ?? 0;
}

export async function getProjectPredictionCount(projectId: string): Promise<number> {
  const resp = await apiClient.get<{ count: number }>(
    "projects",
    `${projectId}/prediction-count`,
  );
  return resp?.count ?? 0;
}

// ---------------------------------------------------------------------------------------------------------------------------
// POST

export async function createProject(
  options: createProjectOptions,
): Promise<Project> {
  return apiClient.insert("projects", options, Project);
}

// ---------------------------------------------------------------------------------------------------------------------------
// DELETE

export async function deleteProject(projectId: string): Promise<boolean> {
  return apiClient.delete("projects", projectId);
}
