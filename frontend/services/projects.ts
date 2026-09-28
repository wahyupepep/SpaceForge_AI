import { apiClient, ApiClient } from "@/services/api-client";

import type { Project, ProjectInput } from "@/types/api";

export class ProjectsService {
  constructor(private readonly client: ApiClient = apiClient) {}

  list(): Promise<Project[]> {
    return this.client.request<Project[]>("/projects", { cache: "no-store" });
  }

  get(projectId: string): Promise<Project> {
    return this.client.request<Project>(`/projects/${projectId}`, { cache: "no-store" });
  }

  create(payload: ProjectInput): Promise<Project> {
    return this.client.request<Project>("/projects", { method: "POST", body: payload });
  }

  update(projectId: string, payload: Partial<ProjectInput>): Promise<Project> {
    return this.client.request<Project>(`/projects/${projectId}`, {
      method: "PATCH",
      body: payload,
    });
  }

  submitForAnalysis(projectId: string): Promise<Project> {
    return this.client.request<Project>(`/projects/${projectId}/submit-for-analysis`, {
      method: "POST",
    });
  }

  delete(projectId: string): Promise<void> {
    return this.client.request<void>(`/projects/${projectId}`, { method: "DELETE" });
  }
}

export const projectsService = new ProjectsService();

