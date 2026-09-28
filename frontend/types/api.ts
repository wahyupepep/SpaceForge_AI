export type ApiErrorResponse = {
  error: {
    code: string;
    message: string;
    details: Array<Record<string, unknown>>;
  };
};

export type HealthResponse = {
  status: "ok";
  service: string;
  environment: string;
  database: "ok";
};

export type ProjectType = "NEW_SYSTEM" | "NEW_FEATURE" | "ENHANCEMENT";
export type ProjectStatus = "DRAFT" | "CONTEXT_INCOMPLETE" | "READY_FOR_ANALYSIS";

export type ProjectContext = {
  id: string;
  current_flow: string | null;
  current_actors: string | null;
  current_rules: string | null;
  current_problem: string | null;
  requested_change: string | null;
  constraints: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type Project = {
  id: string;
  name: string;
  description: string;
  project_type: ProjectType;
  business_objective: string;
  status: ProjectStatus;
  owner_id: string | null;
  context: ProjectContext;
  missing_context_fields: string[];
  created_at: string;
  updated_at: string;
};

export type ProjectContextInput = Omit<ProjectContext, "id" | "created_at" | "updated_at">;

export type ProjectInput = {
  name: string;
  description: string;
  project_type: ProjectType;
  business_objective: string;
  context: ProjectContextInput;
};

export type RequirementStatus = "DRAFT" | "BASELINED";
export type RequirementReadiness = "READY" | "NEEDS_CLARIFICATION" | "BLOCKED";

export type Requirement = {
  id: string;
  project_id: string;
  title: string;
  raw_requirement: string;
  business_objective: string | null;
  actors: string[];
  known_rules: string[];
  constraints: string[];
  dependencies: string[];
  status: RequirementStatus;
  analysis_readiness: RequirementReadiness | null;
  created_at: string;
  updated_at: string;
};

export type RequirementInput = Pick<
  Requirement,
  | "title"
  | "raw_requirement"
  | "business_objective"
  | "actors"
  | "known_rules"
  | "constraints"
  | "dependencies"
>;

export type ArtifactType =
  | "PROJECT_CONTEXT"
  | "REQUIREMENT_BASELINE"
  | "RESEARCH"
  | "EXISTING_SYSTEM_ANALYSIS"
  | "SOLUTION"
  | "PROCESS_FLOW"
  | "UI_PROTOTYPE"
  | "DATABASE_DESIGN"
  | "API_SPECIFICATION"
  | "TEST_SCENARIO"
  | "ACCEPTANCE_CRITERIA"
  | "DEVELOPMENT_TASK";

export type ArtifactVersion = {
  id: string;
  version: number;
  content_json: Record<string, unknown>;
  created_by: string;
  created_at: string;
};

export type Artifact = {
  id: string;
  project_id: string;
  requirement_id: string | null;
  artifact_type: ArtifactType;
  version: number;
  content_json: Record<string, unknown>;
  status: "DRAFT" | "VALIDATED";
  created_by: string;
  created_at: string;
  updated_at: string;
  versions: ArtifactVersion[];
};

export type ArtifactInput = {
  artifact_type: ArtifactType;
  content_json: Record<string, unknown>;
  created_by?: string;
  requirement_id?: string | null;
  status?: "DRAFT" | "VALIDATED";
};

export type Clarification = {
  id: string;
  project_id: string;
  requirement_id: string;
  agent_execution_id: string;
  question: string;
  answer: string | null;
  status: "PENDING" | "ANSWERED";
  answered_by: string | null;
  answered_at: string | null;
  created_at: string;
  updated_at: string;
};

export type RequirementAnalysisResponse = {
  execution_id: string;
  readiness: RequirementReadiness;
  requirement: Requirement;
  artifact: Artifact;
  clarifications: Clarification[];
};

export type ExistingEvidenceType =
  | "USER_DESCRIPTION"
  | "SOURCE_CODE_METADATA"
  | "DATABASE_SCHEMA"
  | "API_DOCUMENTATION"
  | "EXISTING_DOCUMENTATION"
  | "SCREENSHOT_DESCRIPTION"
  | "PREVIOUS_ARTIFACT";

export type ExistingEvidenceInput = {
  source_type: ExistingEvidenceType;
  title: string;
  content: string;
};

export type SolutionWorkflowStatus =
  | "WAITING_USER_APPROVAL"
  | "REVISION_REQUESTED"
  | "APPROVED"
  | "REJECTED";
export type SolutionApprovalAction = "APPROVE" | "REQUEST_REVISION" | "REJECT";

export type SolutionApproval = {
  id: string;
  artifact_version_id: string;
  action: SolutionApprovalAction;
  note: string | null;
  acted_by: string;
  created_at: string;
};

export type SolutionWorkflow = {
  id: string;
  project_id: string;
  requirement_id: string;
  status: SolutionWorkflowStatus;
  current_version: number;
  technical_design_allowed: boolean;
  artifact: Artifact;
  approvals: SolutionApproval[];
  created_at: string;
  updated_at: string;
};

export type QualityWorkflowStatus =
  | "READY_FOR_REVIEW"
  | "REVISION_REQUIRED"
  | "PASSED"
  | "MAX_REVISIONS_REACHED";
export type ReviewSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type ReviewIssue = {
  artifact: ArtifactType;
  issue: string;
  severity: ReviewSeverity;
  reason: string;
  recommended_revision: string;
};

export type QualityWorkflow = {
  id: string;
  project_id: string;
  requirement_id: string;
  status: QualityWorkflowStatus;
  decision: "PASS" | "REVISION_REQUIRED" | null;
  revision_count: number;
  max_revisions: number;
  development_handoff_allowed: boolean;
  reviewed_versions: Record<string, number>;
  issues: ReviewIssue[];
  created_at: string;
  updated_at: string;
};

export type DevelopmentWorkstream =
  | "DATABASE"
  | "BACKEND"
  | "FRONTEND"
  | "INTEGRATION"
  | "QA"
  | "DOCUMENTATION"
  | "GENERAL";

export type DevelopmentTask = {
  id: string;
  title: string;
  workstream: DevelopmentWorkstream;
  objective: string;
  scope: string[];
  requirement: string;
  technical_notes: string[];
  dependency: string[];
  acceptance_criteria: string[];
  reference_artifact: ArtifactType[];
};

export type HandoffSection = {
  number: string;
  slug: string;
  title: string;
  source_artifacts: Array<{
    artifact_type: string;
    artifact_id: string;
    version: number;
  }>;
  content: unknown;
};

export type HandoffPackage = {
  id: string;
  version: number;
  development_task_version_id: string;
  source_versions: Record<string, number>;
  content_json: {
    package_name: string;
    project_id: string;
    requirement_id: string;
    source_versions: Record<string, number>;
    sections: HandoffSection[];
    traceability: Array<{
      task_id: string;
      requirement: string;
      acceptance_criteria: string[];
      reference_artifacts: string[];
    }>;
    trello_ready: {
      board_name: string;
      lists: Array<{ name: string; position: number }>;
      cards: Array<Record<string, unknown>>;
    };
  };
  created_at: string;
};

export type HandoffWorkflow = {
  id: string;
  project_id: string;
  requirement_id: string;
  status: "TASKS_READY" | "PACKAGE_READY";
  current_task_version: number;
  current_package_version: number;
  task_artifact: Artifact;
  current_package: HandoffPackage | null;
  packages: HandoffPackage[];
  created_at: string;
  updated_at: string;
};

export type OrchestratorStage =
  | "PROJECT_CONTEXT"
  | "REQUIREMENT_ANALYSIS"
  | "CLARIFICATION"
  | "REQUIREMENT_READY"
  | "RESEARCH"
  | "EXISTING_SYSTEM_ANALYSIS"
  | "SOLUTION_DESIGN"
  | "USER_APPROVAL"
  | "FLOW_UI_TECHNICAL_DESIGN"
  | "QA"
  | "SA_REVIEW"
  | "REVISION_LOOP"
  | "HANDOFF_READY"
  | "COMPLETED";

export type OrchestratorExecution = {
  id: string;
  workflow_id: string;
  stage: OrchestratorStage;
  agent_name: string | null;
  status: "RUNNING" | "SUCCEEDED" | "WAITING" | "FAILED";
  input_json: Record<string, unknown>;
  output_json: Record<string, unknown>;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
};

export type OrchestratorWorkflow = {
  id: string;
  project_id: string;
  requirement_id: string;
  current_stage: OrchestratorStage;
  status: "ACTIVE" | "WAITING_USER_ACTION" | "FAILED" | "COMPLETED";
  current_agent: string | null;
  completed_stages: OrchestratorStage[];
  pending_user_action: string | null;
  artifact_status: Record<string, { version: number; status: string }>;
  revision_history: Array<Record<string, unknown>>;
  last_error: string | null;
  created_at: string;
  updated_at: string;
  executions: OrchestratorExecution[];
};
