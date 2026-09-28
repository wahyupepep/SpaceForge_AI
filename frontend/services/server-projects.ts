import "server-only";

import { ApiClient } from "@/services/api-client";
import { ProjectsService } from "@/services/projects";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

export const serverProjectsService = new ProjectsService(
  new ApiClient(`${backendUrl}/api/v1`),
);

