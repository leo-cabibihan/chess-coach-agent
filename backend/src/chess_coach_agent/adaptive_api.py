from __future__ import annotations

import asyncio

from fastapi import APIRouter, BackgroundTasks, HTTPException
from sqlalchemy import select

from .db import session_scope
from .agent import ChessCoachAgent
from .analysis import ANALYSIS_VERSION
from .db_models import (
    AnalysisRow,
    GameRow,
    SyncJobRow,
)
from .importers import fetch_platform_pgn, preview_pgn_games
from .models import (
    AnalyzeResponse,
    EvaluationPanel,
    PlayerProfile,
    ProgressSummary,
    QuizAttemptCreate,
    SyncGamesRequest,
    SyncJobView,
    TrainingSessionCreate,
    TrainingSessionView,
)
from .monitoring import log_event
from .repositories import (
    get_or_create_player,
    load_analyses,
    player_profile,
    persist_analyses,
    progress_summary,
    training_session_view,
)
from .training import build_training_session, evaluate_attempt


router = APIRouter(prefix="/api")
coach_agent = ChessCoachAgent()


def _sync_job_view(row: SyncJobRow) -> SyncJobView:
    return SyncJobView(
        id=row.id,
        platform=row.platform,
        username=row.username,
        status=row.status,  # type: ignore[arg-type]
        total_games=row.total_games,
        analyzed_games=row.analyzed_games,
        skipped_games=row.skipped_games,
        error=row.error,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def _process_sync_job(job_id: str, request: SyncGamesRequest) -> None:
    try:
        with session_scope() as session:
            job = session.get(SyncJobRow, job_id)
            if job is None:
                return
            job.status = "fetching"
        pgn = await fetch_platform_pgn(request.platform, request.username, request.max_games)
        previews = preview_pgn_games(
            pgn, request.username, request.platform, request.max_games
        )
        previews.sort(
            key=lambda game: (game.player_result == "loss", game.date), reverse=True
        )
        with session_scope() as session:
            job = session.get(SyncJobRow, job_id)
            if job is None:
                return
            job.status = "analyzing"
            job.total_games = len(previews)

        for preview in previews:
            with session_scope() as session:
                job = session.get(SyncJobRow, job_id)
                if job is None:
                    return
                existing = session.scalar(
                    select(GameRow)
                    .where(
                        GameRow.player_id == job.player_id,
                        GameRow.external_game_id == preview.game_id,
                    )
                )
                if existing and ANALYSIS_VERSION in (
                    session.scalar(
                        select(AnalysisRow.retrieval_notes).where(
                            AnalysisRow.game_id == existing.id
                        )
                    )
                    or []
                ):
                    job.skipped_games += 1
                    continue

            response = await asyncio.to_thread(
                coach_agent.import_pgn_text,
                preview.pgn,
                request.username,
                1,
            )
            with session_scope() as session:
                persist_analyses(
                    session, request.platform, request.username, response
                )
                job = session.get(SyncJobRow, job_id)
                if job:
                    job.analyzed_games += len(response.analyses)

        with session_scope() as session:
            job = session.get(SyncJobRow, job_id)
            if job:
                job.status = "complete"
        log_event(
            "games_sync_completed",
            {"job_id": job_id, "platform": request.platform, "username": request.username},
        )
    except Exception as exc:
        with session_scope() as session:
            job = session.get(SyncJobRow, job_id)
            if job:
                job.status = "failed"
                job.error = str(exc)
        log_event("games_sync_failed", {"job_id": job_id, "error": str(exc)})


@router.post("/games/sync", response_model=SyncJobView)
async def sync_games(
    request: SyncGamesRequest, background_tasks: BackgroundTasks
) -> SyncJobView:
    with session_scope() as session:
        player = get_or_create_player(session, request.platform, request.username)
        active = session.scalar(
            select(SyncJobRow)
            .where(
                SyncJobRow.player_id == player.id,
                SyncJobRow.status.in_(["queued", "fetching", "analyzing"]),
            )
            .order_by(SyncJobRow.created_at.desc())
        )
        if active:
            return _sync_job_view(active)
        job = SyncJobRow(
            player_id=player.id,
            platform=request.platform,
            username=request.username,
        )
        session.add(job)
        session.flush()
        view = _sync_job_view(job)
    background_tasks.add_task(_process_sync_job, job.id, request)
    return view


@router.get("/games/sync/{job_id}", response_model=SyncJobView)
def get_sync_job(job_id: str) -> SyncJobView:
    with session_scope() as session:
        job = session.get(SyncJobRow, job_id)
        if job is None:
            raise HTTPException(404, "Sync job not found")
        return _sync_job_view(job)


@router.get("/games/{platform}/{username}", response_model=AnalyzeResponse)
def get_analyzed_games(platform: str, username: str) -> AnalyzeResponse:
    with session_scope() as session:
        return load_analyses(session, platform, username)


@router.get("/players/{platform}/{username}", response_model=PlayerProfile)
def get_player(platform: str, username: str) -> PlayerProfile:
    with session_scope() as session:
        player = get_or_create_player(session, platform, username)
        return player_profile(session, player)


@router.post("/training/sessions", response_model=TrainingSessionView)
def create_training_session(request: TrainingSessionCreate) -> TrainingSessionView:
    with session_scope() as session:
        plan = build_training_session(
            session,
            request.platform,
            request.username,
            request.theme,
            request.position_count,
            request.moment_id,
        )
        view = training_session_view(session, plan.id)
        if view is None:
            raise HTTPException(500, "Training session could not be created")
        log_event(
            "training_session_created",
            {"training_session_id": plan.id, "positions": len(view.positions), "difficulty": plan.difficulty},
        )
        return view


@router.get("/training/sessions/{training_session_id}", response_model=TrainingSessionView)
def get_training_session(training_session_id: str) -> TrainingSessionView:
    with session_scope() as session:
        view = training_session_view(session, training_session_id)
        if view is None:
            raise HTTPException(404, "Training session not found")
        return view


@router.post(
    "/training/sessions/{training_session_id}/attempts",
    response_model=EvaluationPanel,
)
def submit_training_attempt(
    training_session_id: str, request: QuizAttemptCreate
) -> EvaluationPanel:
    with session_scope() as session:
        view = training_session_view(session, training_session_id)
        if view is None or request.position_id not in {item.id for item in view.positions}:
            raise HTTPException(404, "Training position not found in this session")
        try:
            result = evaluate_attempt(
                session,
                request.position_id,
                request.move,
                request.hints_used,
                request.elapsed_ms,
            )
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        log_event(
            "quiz_attempted",
            {
                "training_session_id": training_session_id,
                "position_id": request.position_id,
                "correct": result.correct,
                "legal": result.legal,
                "hints_used": request.hints_used,
            },
        )
        return result


@router.get("/progress/{platform}/{username}", response_model=ProgressSummary)
def get_progress(platform: str, username: str) -> ProgressSummary:
    with session_scope() as session:
        return progress_summary(session, platform, username)
