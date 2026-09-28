import { apiClient, ApiClient } from "@/services/api-client";
import type { Artifact, ExistingEvidenceInput } from "@/types/api";

type SpecialistResponse = { execution_id: string; artifact: Artifact };

export class DiscoveryAnalysisService {
  constructor(private readonly client: ApiClient = apiClient) {}

  research(projectId: string, requirementId: string): Promise<SpecialistResponse> {
    return this.client.request<SpecialistResponse>(`/projects/${projectId}/research`, {
      method: "POST",
      body: { requirement_id: requirementId },
    });
  }

  analyzeExistingSystem(
    projectId: string,
    requirementId: string,
    evidence: ExistingEvidenceInput[],
  ): Promise<SpecialistResponse> {
    return this.client.request<SpecialistResponse>(
      `/projects/${projectId}/analyze-existing-system`,
      { method: "POST", body: { requirement_id: requirementId, evidence } },
    );
  }
}

export const discoveryAnalysisService = new DiscoveryAnalysisService();

