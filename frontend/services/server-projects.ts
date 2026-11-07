import "server-only";

import { ServerApiClient } from "@/services/server-api-client";
import { ProjectsService } from "@/services/projects";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

export const serverProjectsService = new ProjectsService(
  new ServerApiClient(`${backendUrl}/api/v1`),
);

