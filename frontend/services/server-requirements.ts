import "server-only";

import { ApiClient } from "@/services/api-client";
import { ArtifactsService } from "@/services/artifacts";
import { DevelopmentHandoffService } from "@/services/development-handoff";
import { RequirementsService } from "@/services/requirements";
import { RequirementAnalysisService } from "@/services/requirement-analysis";
import { QualityGateService } from "@/services/quality-gate";
import { OrchestratorService } from "@/services/orchestrator";
import { SolutionAnalysisService } from "@/services/solution-analysis";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
const serverClient = new ApiClient(`${backendUrl}/api/v1`);

export const serverRequirementsService = new RequirementsService(serverClient);
export const serverArtifactsService = new ArtifactsService(serverClient);
export const serverRequirementAnalysisService = new RequirementAnalysisService(serverClient);
export const serverSolutionAnalysisService = new SolutionAnalysisService(serverClient);
export const serverQualityGateService = new QualityGateService(serverClient);
export const serverDevelopmentHandoffService = new DevelopmentHandoffService(serverClient);
export const serverOrchestratorService = new OrchestratorService(serverClient);
