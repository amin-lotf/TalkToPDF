from __future__ import annotations

from uuid import uuid4

import pytest

from talk_to_pdf.backend.app.application.indexing.dto import StartIndexingInputDTO
from talk_to_pdf.backend.app.application.indexing.use_cases.start_indexing import StartIndexingUseCase
from talk_to_pdf.backend.app.domain.indexing.enums import IndexStatus
from talk_to_pdf.backend.app.domain.indexing.errors import FailedToStartIndexing
from talk_to_pdf.backend.app.domain.indexing.value_objects import EmbedConfig
from talk_to_pdf.backend.app.domain.projects.entities import Project, ProjectDocument
from talk_to_pdf.backend.app.domain.projects.errors import ProjectNotFound, DocumentNotFound
from talk_to_pdf.backend.app.domain.projects.value_objects import ProjectName
from tests.unit.fakes.indexing_runner import FakeIndexingRunner
from tests.unit.fakes.uow import FakeUnitOfWork


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def runner() -> FakeIndexingRunner:
    return FakeIndexingRunner()


@pytest.fixture
def embed_config() -> EmbedConfig:
    return EmbedConfig(
        provider="openai",
        model="text-embedding-3-small",
        batch_size=100,
        dimensions=1536,
    )


@pytest.fixture
def use_case(uow: FakeUnitOfWork, runner: FakeIndexingRunner, embed_config: EmbedConfig) -> StartIndexingUseCase:
    return StartIndexingUseCase(
        uow=uow,
        runner=runner,
        chunker_version="v1.0",
        embed_config=embed_config,
    )


@pytest.fixture
def project_with_document(uow: FakeUnitOfWork) -> Project:
    """Creates a project with a document attached."""
    owner_id = uuid4()
    project = Project(
        name=ProjectName("Test Project"),
        owner_id=owner_id,
    )

    document = ProjectDocument(
        project_id=project.id,
        original_filename="test.pdf",
        storage_path=f"{owner_id}/{project.id}/test.pdf",
        content_type="application/pdf",
        size_bytes=1024,
    )

    project = project.attach_main_document(document)
    uow.project_repo._add_raw(project)
    return project


class TestStartIndexingUseCase:
    """Tests for StartIndexingUseCase."""

    async def test_creates_new_index_and_enqueues_job(
        self,
        use_case: StartIndexingUseCase,
        runner: FakeIndexingRunner,
        uow: FakeUnitOfWork,
        project_with_document: Project,
    ) -> None:
        """Should create a new index and enqueue the indexing job."""
        dto = StartIndexingInputDTO(
            project_id=project_with_document.id,
            document_id=project_with_document.primary_document.id,
        )

        result = await use_case.execute(dto)

        # Check result
        assert result.project_id == project_with_document.id
        assert result.document_id == project_with_document.primary_document.id
        assert result.status == IndexStatus.PENDING
        assert result.progress == 0
        assert result.storage_path == project_with_document.primary_document.storage_path

        # Check index was created in repo
        index = await uow.index_repo.get_by_id(index_id=result.index_id)
        assert index is not None
        assert index.project_id == project_with_document.id
        assert index.document_id == project_with_document.primary_document.id
        assert index.status == IndexStatus.PENDING
        assert index.chunker_version == "v1.0"

        # Check job was enqueued
        assert len(runner.enqueued) == 1
        assert runner.enqueued[0] == result.index_id

    async def test_returns_existing_active_index(
        self,
        use_case: StartIndexingUseCase,
        runner: FakeIndexingRunner,
        uow: FakeUnitOfWork,
        project_with_document: Project,
        embed_config: EmbedConfig,
    ) -> None:
        """Should return existing active index without creating a new one."""
        # Create an existing PENDING index
        existing = await uow.index_repo.create_pending(
            project_id=project_with_document.id,
            document_id=project_with_document.primary_document.id,
            storage_path=project_with_document.primary_document.storage_path,
            chunker_version="v1.0",
            embed_config=embed_config,
        )

        dto = StartIndexingInputDTO(
            project_id=project_with_document.id,
            document_id=project_with_document.primary_document.id,
        )

        result = await use_case.execute(dto)

        # Should return the existing index
        assert result.index_id == existing.id
        assert result.status == IndexStatus.PENDING

        # Should NOT enqueue a new job
        assert len(runner.enqueued) == 0

        # Should NOT create a new index
        assert len(uow.index_repo._by_id) == 1

    async def test_creates_new_index_when_previous_is_terminal(
        self,
        use_case: StartIndexingUseCase,
        runner: FakeIndexingRunner,
        uow: FakeUnitOfWork,
        project_with_document: Project,
        embed_config: EmbedConfig,
    ) -> None:
        """Should create a new index if the previous one is in a terminal state."""
        # Create a completed index
        existing = await uow.index_repo.create_pending(
            project_id=project_with_document.id,
            document_id=project_with_document.primary_document.id,
            storage_path=project_with_document.primary_document.storage_path,
            chunker_version="v1.0",
            embed_config=embed_config,
        )

        # Mark it as READY (terminal state)
        await uow.index_repo.update_progress(
            index_id=existing.id,
            status=IndexStatus.READY,
            progress=100,
        )

        dto = StartIndexingInputDTO(
            project_id=project_with_document.id,
            document_id=project_with_document.primary_document.id,
        )

        result = await use_case.execute(dto)

        # Should create a new index
        assert result.index_id != existing.id
        assert result.status == IndexStatus.PENDING

        # Should enqueue the new job
        assert len(runner.enqueued) == 1
        assert runner.enqueued[0] == result.index_id

        # Should have 2 indexes now
        assert len(uow.index_repo._by_id) == 2

    async def test_raises_project_not_found(
        self,
        use_case: StartIndexingUseCase,
        uow: FakeUnitOfWork,
    ) -> None:
        """Should raise ProjectNotFound if project doesn't exist."""
        dto = StartIndexingInputDTO(
            project_id=uuid4(),
            document_id=uuid4(),
        )

        with pytest.raises(FailedToStartIndexing) as exc_info:
            await use_case.execute(dto)

        assert isinstance(exc_info.value.__cause__, ProjectNotFound)

    async def test_raises_document_not_found(
        self,
        use_case: StartIndexingUseCase,
        uow: FakeUnitOfWork,
        project_with_document: Project,
    ) -> None:
        """Should raise DocumentNotFound if document ID doesn't match project's primary document."""
        dto = StartIndexingInputDTO(
            project_id=project_with_document.id,
            document_id=uuid4(),  # Wrong document ID
        )

        with pytest.raises(FailedToStartIndexing) as exc_info:
            await use_case.execute(dto)

        assert isinstance(exc_info.value.__cause__, DocumentNotFound)

    async def test_marks_index_failed_when_enqueue_fails(
        self,
        uow: FakeUnitOfWork,
        embed_config: EmbedConfig,
        project_with_document: Project,
    ) -> None:
        """Should mark index as FAILED if enqueue operation fails."""
        # Create a runner that raises an exception
        runner = FakeIndexingRunner(raise_on_enqueue=RuntimeError("Queue unavailable"))

        use_case = StartIndexingUseCase(
            uow=uow,
            runner=runner,
            chunker_version="v1.0",
            embed_config=embed_config,
        )

        dto = StartIndexingInputDTO(
            project_id=project_with_document.id,
            document_id=project_with_document.primary_document.id,
        )

        with pytest.raises(FailedToStartIndexing) as exc_info:
            await use_case.execute(dto)

        assert "failed to enqueue job" in str(exc_info.value).lower()

        # Check that an index was created
        indexes = list(uow.index_repo._by_id.values())
        assert len(indexes) == 1

        # Check it was marked as FAILED
        failed_index = indexes[0]
        assert failed_index.status == IndexStatus.FAILED
        assert failed_index.message == "Failed to enqueue indexing job"
        assert "Queue unavailable" in failed_index.error

    async def test_respects_embed_signature_for_idempotency(
        self,
        use_case: StartIndexingUseCase,
        runner: FakeIndexingRunner,
        uow: FakeUnitOfWork,
        project_with_document: Project,
    ) -> None:
        """Should only return existing index if embed_signature matches."""
        # Create an index with a different embed config
        different_config = EmbedConfig(
            provider="openai",
            model="text-embedding-3-large",  # Different model
            batch_size=100,
            dimensions=3072,
        )

        existing = await uow.index_repo.create_pending(
            project_id=project_with_document.id,
            document_id=project_with_document.primary_document.id,
            storage_path=project_with_document.primary_document.storage_path,
            chunker_version="v1.0",
            embed_config=different_config,
        )

        dto = StartIndexingInputDTO(
            project_id=project_with_document.id,
            document_id=project_with_document.primary_document.id,
        )

        result = await use_case.execute(dto)

        # Should create a new index (different signature)
        assert result.index_id != existing.id
        assert result.status == IndexStatus.PENDING

        # Should enqueue the new job
        assert len(runner.enqueued) == 1

        # Should have 2 indexes now
        assert len(uow.index_repo._by_id) == 2

    async def test_includes_storage_path_in_created_index(
        self,
        use_case: StartIndexingUseCase,
        uow: FakeUnitOfWork,
        project_with_document: Project,
    ) -> None:
        """Should include the document's storage path in the created index."""
        dto = StartIndexingInputDTO(
            project_id=project_with_document.id,
            document_id=project_with_document.primary_document.id,
        )

        result = await use_case.execute(dto)

        # Check storage_path is set correctly
        assert result.storage_path == project_with_document.primary_document.storage_path

        # Verify in the repository
        index = await uow.index_repo.get_by_id(index_id=result.index_id)
        assert index.storage_path == project_with_document.primary_document.storage_path

    async def test_uow_commits_on_success(
        self,
        use_case: StartIndexingUseCase,
        uow: FakeUnitOfWork,
        project_with_document: Project,
    ) -> None:
        """Should commit the unit of work on successful execution."""
        dto = StartIndexingInputDTO(
            project_id=project_with_document.id,
            document_id=project_with_document.primary_document.id,
        )

        await use_case.execute(dto)

        assert uow.committed is True
        assert uow.rolled_back is False

    async def test_returns_running_index_as_active(
        self,
        use_case: StartIndexingUseCase,
        runner: FakeIndexingRunner,
        uow: FakeUnitOfWork,
        project_with_document: Project,
        embed_config: EmbedConfig,
    ) -> None:
        """Should return existing RUNNING index without creating a new one."""
        # Create a RUNNING index
        existing = await uow.index_repo.create_pending(
            project_id=project_with_document.id,
            document_id=project_with_document.primary_document.id,
            storage_path=project_with_document.primary_document.storage_path,
            chunker_version="v1.0",
            embed_config=embed_config,
        )

        # Update to RUNNING
        await uow.index_repo.update_progress(
            index_id=existing.id,
            status=IndexStatus.RUNNING,
            progress=50,
        )

        dto = StartIndexingInputDTO(
            project_id=project_with_document.id,
            document_id=project_with_document.primary_document.id,
        )

        result = await use_case.execute(dto)

        # Should return the existing RUNNING index
        assert result.index_id == existing.id
        assert result.status == IndexStatus.RUNNING
        assert result.progress == 50

        # Should NOT enqueue a new job
        assert len(runner.enqueued) == 0
