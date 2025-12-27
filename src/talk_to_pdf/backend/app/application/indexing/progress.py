from talk_to_pdf.backend.app.domain.indexing.enums import IndexStatus, IndexStep, STEP_PROGRESS


async def report(
    *,
    uow,
    index_id,
    status: IndexStatus,
    step: IndexStep | None = None,
    message: str | None = None,
    error: str | None = None,
    meta: dict | None = None,
    progress: int | None = None,
):
    if progress is None:
        if status in {IndexStatus.READY}:
            progress = 100
        elif status in {IndexStatus.FAILED, IndexStatus.CANCELLED}:
            progress = 0
        elif step is not None:
            progress = STEP_PROGRESS[step]
        else:
            progress = 0  # safe fallback

    await uow.index_repo.update_progress(
        index_id=index_id,
        status=status,
        progress=progress,
        message=message,
        error=error,
        meta=meta,
    )
