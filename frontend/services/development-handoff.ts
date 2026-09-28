import { apiClient, ApiClient } from "@/services/api-client";
import type { HandoffWorkflow } from "@/types/api";

export type DevelopmentPlanResponse = {
  execution_id: string;
  workflow: HandoffWorkflow;
};

export class DevelopmentHandoffService {
  constructor(private readonly client: ApiClient = apiClient) {}

  plan(projectId: string, requirementId: string): Promise<DevelopmentPlanResponse> {
    return this.client.request(`/projects/${projectId}/handoff/plan`, {
      method: "POST",
      body: { requirement_id: requirementId },
    });
  }

  generate(
    projectId: string,
    requirementId: string,
    expectedTaskVersion: number,
  ): Promise<HandoffWorkflow> {
    return this.client.request(
      `/projects/${projectId}/requirements/${requirementId}/handoff/generate`,
      { method: "POST", body: { expected_task_version: expectedTaskVersion } },
    );
  }

  get(projectId: string, requirementId: string): Promise<HandoffWorkflow> {
    return this.client.request(
      `/projects/${projectId}/requirements/${requirementId}/handoff`,
    );
  }
}

export const developmentHandoffService = new DevelopmentHandoffService();
