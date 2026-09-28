import { apiClient, ApiClient } from "@/services/api-client";
import type { Requirement, RequirementInput } from "@/types/api";

export class RequirementsService {
  constructor(private readonly client: ApiClient = apiClient) {}

  list(projectId: string): Promise<Requirement[]> {
    return this.client.request<Requirement[]>(`/projects/${projectId}/requirements`, {
      cache: "no-store",
    });
  }

  create(projectId: string, payload: RequirementInput): Promise<Requirement> {
    return this.client.request<Requirement>(`/projects/${projectId}/requirements`, {
      method: "POST",
      body: payload,
    });
  }

  update(
    projectId: string,
    requirementId: string,
    payload: Partial<RequirementInput>,
  ): Promise<Requirement> {
    return this.client.request<Requirement>(
      `/projects/${projectId}/requirements/${requirementId}`,
      { method: "PATCH", body: payload },
    );
  }

  delete(projectId: string, requirementId: string): Promise<void> {
    return this.client.request<void>(
      `/projects/${projectId}/requirements/${requirementId}`,
      { method: "DELETE" },
    );
  }
}

export const requirementsService = new RequirementsService();

