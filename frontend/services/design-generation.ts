import { apiClient, ApiClient } from "@/services/api-client";
import type { Artifact } from "@/types/api";

export type DesignAgentResponse = {
  execution_id: string;
  artifacts: Artifact[];
};

export class DesignGenerationService {
  constructor(private readonly client: ApiClient = apiClient) {}

  private run(projectId: string, requirementId: string, stage: string): Promise<DesignAgentResponse> {
    return this.client.request(`/projects/${projectId}/design/${stage}`, {
      method: "POST",
      body: { requirement_id: requirementId },
    });
  }

  flow(projectId: string, requirementId: string): Promise<DesignAgentResponse> {
    return this.run(projectId, requirementId, "flow");
  }

  uiPrototype(projectId: string, requirementId: string): Promise<DesignAgentResponse> {
    return this.run(projectId, requirementId, "ui-prototype");
  }

  technicalArchitecture(projectId: string, requirementId: string): Promise<DesignAgentResponse> {
    return this.run(projectId, requirementId, "technical-architecture");
  }
}

export const designGenerationService = new DesignGenerationService();
