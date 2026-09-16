"""16-09-2026: a turn the engine completed normally is never shown as
"No response from provider" because the transcript heuristic lost track."""
import api.streaming as streaming


def _healthy(**extra):
    result = {"final_response": "Je hebt gelijk: dit is het antwoord.", "messages": [], "completed": True,
              "failed": False, "partial": False, "interrupted": False,
              "turn_exit_reason": "text_response(finish_reason=stop)"}
    result.update(extra)
    return result


def test_engine_verdict_wins_over_the_transcript_heuristic():
    assert streaming._turn_is_terminal_failure(_healthy(), True, "no_response") is False


def test_a_real_silent_failure_is_still_a_failure():
    silent = _healthy(final_response="", turn_exit_reason="all_retries_exhausted_no_response")
    assert streaming._turn_is_terminal_failure(silent, True, "no_response") is True


def test_failed_partial_and_error_results_stay_failures():
    assert streaming._turn_is_terminal_failure(_healthy(failed=True), False, "no_response") is True
    assert streaming._turn_is_terminal_failure(_healthy(partial=True), True, "no_response") is True
    assert streaming._turn_is_terminal_failure(_healthy(error="boom"), True, "no_response") is True


def test_cancelled_and_interrupted_are_not_failures():
    assert streaming._turn_is_terminal_failure(_healthy(), True, "cancelled") is False
    assert streaming._turn_is_terminal_failure(_healthy(), True, "interrupted") is False


def test_a_healthy_transcript_needs_no_override():
    assert streaming._turn_is_terminal_failure(_healthy(), False, "no_response") is False
