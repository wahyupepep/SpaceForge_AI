from __future__ import annotations

from pathlib import PurePath
from typing import Optional
from uuid import UUID, uuid4

from app.core.errors import ContextIncompleteError, EvidenceInvalidError, NotFoundError
from app.domain.projects import (
    ENHANCEMENT_EVIDENCE_FIELD,
    ProjectStatus,
    ProjectType,
    missing_enhancement_context,
)
from app.models.project import Project, ProjectContext, ProjectEvidence
from app.repositories.projects import ProjectRepository
from app.schemas.project import (
    ProjectCreate,
    ProjectEvidenceResponse,
    ProjectResponse,
    ProjectUpdate,
)
from app.services.file_storage import FileStorageService

MAX_EVIDENCE_BYTES = 4 * 1024 * 1024
ALLOWED_EVIDENCE_CATEGORIES = {
    "UI_SCREENSHOT",
    "SOURCE_CODE",
    "API_DOCUMENTATION",
    "DATABASE_SCHEMA",
    "PROCESS_DOCUMENT",
    "OTHER",
}


class ProjectService:
    def __init__(
        self,
        repository: ProjectRepository,
        storage: Optional[FileStorageService] = None,
    ) -> None:
        self._repository = repository
        self._storage = storage

    @staticmethod
    def _response(project: Project) -> ProjectResponse:
        missing_fields = (
            missing_enhancement_context(project.context)
            if project.project_type == ProjectType.ENHANCEMENT
            else []
        )
        if project.project_type == ProjectType.ENHANCEMENT and not project.evidence:
            missing_fields.append(ENHANCEMENT_EVIDENCE_FIELD)
        response = ProjectResponse.model_validate(project)
        return response.model_copy(
            update={
                "missing_context_fields": missing_fields,
                "evidence_count": len(project.evidence),
            }
        )

    async def create(self, payload: ProjectCreate) -> ProjectResponse:
        project = Project(
            name=payload.name,
            description=payload.description,
            project_type=payload.project_type,
            business_objective=payload.business_objective,
            status=ProjectStatus.DRAFT,
            owner_id=getattr(self._repository, "owner_id", None),
            context=ProjectContext(**payload.context.model_dump()),
        )
        await self._repository.add(project)
        await self._repository.commit()
        await self._repository.refresh(project)
        return self._response(project)

    async def get(self, project_id: UUID) -> ProjectResponse:
        return self._response(await self._require_project(project_id))

    async def list(self, offset: int, limit: int) -> list[ProjectResponse]:
        projects = await self._repository.list(offset=offset, limit=limit)
        return [self._response(project) for project in projects]

    async def update(self, project_id: UUID, payload: ProjectUpdate) -> ProjectResponse:
        project = await self._require_project(project_id)
        updates = payload.model_dump(exclude_unset=True, exclude={"context"})
        for field, value in updates.items():
            setattr(project, field, value)

        if payload.context is not None:
            for field, value in payload.context.model_dump(exclude_unset=True).items():
                setattr(project.context, field, value)

        missing_fields = (
            missing_enhancement_context(project.context)
            if project.project_type == ProjectType.ENHANCEMENT
            else []
        )
        if project.project_type == ProjectType.ENHANCEMENT and not project.evidence:
            missing_fields.append(ENHANCEMENT_EVIDENCE_FIELD)
        project.status = ProjectStatus.CONTEXT_INCOMPLETE if missing_fields else ProjectStatus.DRAFT
        await self._repository.commit()
        await self._repository.refresh(project)
        return self._response(project)

    async def submit_for_analysis(self, project_id: UUID) -> ProjectResponse:
        project = await self._require_project(project_id)
        missing_fields = (
            missing_enhancement_context(project.context)
            if project.project_type == ProjectType.ENHANCEMENT
            else []
        )
        if project.project_type == ProjectType.ENHANCEMENT and not project.evidence:
            missing_fields.append(ENHANCEMENT_EVIDENCE_FIELD)
        if missing_fields:
            project.status = ProjectStatus.CONTEXT_INCOMPLETE
            await self._repository.commit()
            raise ContextIncompleteError(missing_fields)

        project.status = ProjectStatus.READY_FOR_ANALYSIS
        await self._repository.commit()
        await self._repository.refresh(project)
        return self._response(project)

    async def delete(self, project_id: UUID) -> None:
        project = await self._require_project(project_id)
        await self._repository.delete(project)
        await self._repository.commit()

    async def add_evidence(
        self,
        project_id: UUID,
        *,
        category: str,
        title: str,
        description: Optional[str],
        filename: str,
        content_type: str,
        content: bytes,
    ) -> ProjectEvidenceResponse:
        project = await self._require_project(project_id)
        if self._storage is None:
            raise RuntimeError("File storage is not configured.")
        normalized_category = category.strip().upper()
        if normalized_category not in ALLOWED_EVIDENCE_CATEGORIES:
            raise EvidenceInvalidError("Unsupported evidence category.")
        if not content or len(content) > MAX_EVIDENCE_BYTES:
            raise EvidenceInvalidError("Evidence file must contain 1 byte to 4 MB.")
        safe_filename = PurePath(filename).name[:255] or "evidence"
        evidence_id = uuid4()
        storage_key = f"projects/{project.id}/evidence/{evidence_id}/{safe_filename}"
        stored = await self._storage.put(storage_key, content, content_type)
        evidence = ProjectEvidence(
            id=evidence_id,
            project_id=project.id,
            category=normalized_category,
            title=title.strip()[:200],
            description=description.strip() if description else None,
            original_filename=safe_filename,
            storage_key=stored.key,
            content_type=stored.content_type,
            size_bytes=stored.size_bytes,
        )
        self._repository.add_evidence(evidence)
        try:
            await self._repository.commit()
        except Exception:
            await self._storage.delete(storage_key)
            raise
        return ProjectEvidenceResponse.model_validate(evidence)

    async def list_evidence(self, project_id: UUID) -> list[ProjectEvidenceResponse]:
        project = await self._require_project(project_id)
        return [ProjectEvidenceResponse.model_validate(item) for item in project.evidence]

    async def delete_evidence(self, project_id: UUID, evidence_id: UUID) -> None:
        await self._require_project(project_id)
        evidence = await self._repository.get_evidence(project_id, evidence_id)
        if evidence is None:
            raise NotFoundError("Project evidence")
        await self._repository.delete_evidence(evidence)
        await self._repository.commit()
        if self._storage is not None:
            await self._storage.delete(evidence.storage_key)

    async def get_evidence_content(
        self, project_id: UUID, evidence_id: UUID
    ) -> tuple[bytes, str, str]:
        await self._require_project(project_id)
        evidence = await self._repository.get_evidence(project_id, evidence_id)
        if evidence is None:
            raise NotFoundError("Project evidence")
        if self._storage is None:
            raise RuntimeError("File storage is not configured.")
        return (
            await self._storage.read(evidence.storage_key),
            evidence.content_type,
            evidence.original_filename,
        )

    async def _require_project(self, project_id: UUID) -> Project:
        project = await self._repository.get(project_id)
        if project is None:
            raise NotFoundError("Project")
        return project
