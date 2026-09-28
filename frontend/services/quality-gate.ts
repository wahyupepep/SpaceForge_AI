import { apiClient, ApiClient } from "@/services/api-client";
import type { Artifact, ArtifactType, QualityWorkflow } from "@/types/api";

export type QualityAgentResponse = {
  execution_id: string;
  workflow: QualityWorkflow;
  artifacts: Artifact[];
};

export class QualityGateService {
  constructor(private readonly client: ApiClient = apiClient) {}

  qa(projectId: string, requirementId: string): Promise<QualityAgentResponse> {
    return this.client.request(`/projects/${projectId}/quality/qa`, {
      method: "POST",
      body: { requirement_id: requirementId },
    });
  }

  review(projectId: string, requirementId: string): Promise<QualityAgentResponse> {
    return this.client.request(`/projects/${projectId}/quality/review`, {
      method: "POST",
      body: { requirement_id: requirementId },
    });
  }

  revise(
    projectId: string,
    requirementId: string,
    artifactType: ArtifactType,
  ): Promise<QualityAgentResponse> {
    return this.client.request(
      `/projects/${projectId}/requirements/${requirementId}/quality/revise`,
      { method: "POST", body: { artifact_type: artifactType } },
    );
  }

  list(projectId: string): Promise<QualityWorkflow[]> {
    return this.client.request(`/projects/${projectId}/quality-workflows`);
  }
}

export const qualityGateService = new QualityGateService();
