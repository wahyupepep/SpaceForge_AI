import { apiClient, ApiClient } from "@/services/api-client";
import type { OrchestratorWorkflow } from "@/types/api";

export class OrchestratorService {
  constructor(private readonly client: ApiClient = apiClient) {}

  list(projectId: string): Promise<OrchestratorWorkflow[]> {
    return this.client.request(`/projects/${projectId}/orchestrator-workflows`, {
      cache: "no-store",
    });
  }

  start(projectId: string, requirementId: string): Promise<OrchestratorWorkflow> {
    return this.client.request(`/projects/${projectId}/orchestrator/start`, {
      method: "POST",
      body: { requirement_id: requirementId, existing_system_evidence: [] },
    });
  }

  resume(projectId: string, requirementId: string): Promise<OrchestratorWorkflow> {
    return this.client.request(
      `/projects/${projectId}/requirements/${requirementId}/orchestrator/resume`,
      { method: "POST" },
    );
  }
}

export const orchestratorService = new OrchestratorService();
