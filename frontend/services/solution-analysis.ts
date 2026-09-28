import { apiClient, ApiClient } from "@/services/api-client";
import type {
  SolutionApprovalAction,
  SolutionWorkflow,
} from "@/types/api";

export class SolutionAnalysisService {
  constructor(private readonly client: ApiClient = apiClient) {}

  list(projectId: string): Promise<SolutionWorkflow[]> {
    return this.client.request<SolutionWorkflow[]>(`/projects/${projectId}/solution-workflows`, {
      cache: "no-store",
    });
  }

  generate(projectId: string, requirementId: string): Promise<{ execution_id: string; workflow: SolutionWorkflow }> {
    return this.client.request(`/projects/${projectId}/generate-solution`, {
      method: "POST",
      body: { requirement_id: requirementId },
    });
  }

  act(
    projectId: string,
    requirementId: string,
    action: SolutionApprovalAction,
    expectedVersion: number,
    note?: string,
  ): Promise<SolutionWorkflow> {
    return this.client.request(
      `/projects/${projectId}/requirements/${requirementId}/solution-approval`,
      {
        method: "POST",
        body: { action, expected_version: expectedVersion, note: note || null, acted_by: "USER" },
      },
    );
  }

  retryRevision(
    projectId: string,
    requirementId: string,
  ): Promise<{ execution_id: string; workflow: SolutionWorkflow }> {
    return this.client.request(
      `/projects/${projectId}/requirements/${requirementId}/solution-revision/retry`,
      { method: "POST" },
    );
  }
}

export const solutionAnalysisService = new SolutionAnalysisService();
