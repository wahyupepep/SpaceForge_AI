import { apiClient, ApiClient } from "@/services/api-client";
import type { Artifact, ArtifactInput } from "@/types/api";

export class ArtifactsService {
  constructor(private readonly client: ApiClient = apiClient) {}

  list(projectId: string): Promise<Artifact[]> {
    return this.client.request<Artifact[]>(`/projects/${projectId}/artifacts`, {
      cache: "no-store",
    });
  }

  create(projectId: string, payload: ArtifactInput): Promise<Artifact> {
    return this.client.request<Artifact>(`/projects/${projectId}/artifacts`, {
      method: "POST",
      body: payload,
    });
  }

  createVersion(
    projectId: string,
    artifactId: string,
    payload: Pick<ArtifactInput, "content_json" | "created_by" | "status">,
  ): Promise<Artifact> {
    return this.client.request<Artifact>(
      `/projects/${projectId}/artifacts/${artifactId}/versions`,
      { method: "POST", body: payload },
    );
  }
}

export const artifactsService = new ArtifactsService();

