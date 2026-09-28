import { apiClient, ApiClient } from "@/services/api-client";
import type { Clarification, RequirementAnalysisResponse } from "@/types/api";

export class RequirementAnalysisService {
  constructor(private readonly client: ApiClient = apiClient) {}

  analyze(projectId: string, requirementId: string): Promise<RequirementAnalysisResponse> {
    return this.client.request<RequirementAnalysisResponse>(
      `/projects/${projectId}/analyze-requirement`,
      { method: "POST", body: { requirement_id: requirementId } },
    );
  }

  listClarifications(projectId: string, requirementId: string): Promise<Clarification[]> {
    return this.client.request<Clarification[]>(
      `/projects/${projectId}/requirements/${requirementId}/clarifications`,
      { cache: "no-store" },
    );
  }

  answer(
    projectId: string,
    requirementId: string,
    answers: Array<{ clarification_id: string; answer: string }>,
  ): Promise<RequirementAnalysisResponse> {
    return this.client.request<RequirementAnalysisResponse>(
      `/projects/${projectId}/requirements/${requirementId}/clarifications/answer`,
      { method: "POST", body: { answers, answered_by: "USER" } },
    );
  }
}

export const requirementAnalysisService = new RequirementAnalysisService();

