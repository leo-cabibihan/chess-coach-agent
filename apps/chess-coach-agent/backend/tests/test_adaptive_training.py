import uuid

from chess_coach_agent.db import init_db, session_scope
from chess_coach_agent.db_models import QuizAttemptRow, TrainingPlanRow, TrainingPositionRow
from chess_coach_agent.repositories import get_or_create_player
from chess_coach_agent.training import difficulty_for


def test_difficulty_uses_rating_then_demonstrated_theme_performance():
    init_db()
    with session_scope() as session:
        player = get_or_create_player(session, "chess.com", f"difficulty-{uuid.uuid4().hex}")
        player.current_rating = 1900
        assert difficulty_for(session, player, "loose_pieces") == "advanced"

        plan = TrainingPlanRow(
            player_id=player.id,
            focus_themes=["loose_pieces"],
            difficulty="advanced",
        )
        session.add(plan)
        session.flush()
        position = TrainingPositionRow(
            plan_id=plan.id,
            position_order=1,
            fen="8/8/8/8/8/3k4/8/3K4 w - - 0 1",
            correct_move="Kc1",
            choices=["Kc1"],
            theme="loose_pieces",
            difficulty="advanced",
        )
        session.add(position)
        session.flush()
        for _ in range(3):
            session.add(
                QuizAttemptRow(
                    player_id=player.id,
                    position_id=position.id,
                    submitted_move="Ke1",
                    correct=False,
                    legal=True,
                )
            )
        session.flush()
        assert difficulty_for(session, player, "loose_pieces") == "beginner"
