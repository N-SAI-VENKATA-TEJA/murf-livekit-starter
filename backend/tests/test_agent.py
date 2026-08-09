from unittest.mock import AsyncMock, patch

import pytest

from agent import Assistant


@pytest.mark.asyncio
async def test_memory_security_consent_flow() -> None:
    """Verifies all security and consent state transition requirements for Day 4."""
    with patch("agent.children_col.update_one", new_callable=AsyncMock) as mock_update:
        assistant = Assistant(child_id="111111111111111111111111")

        # C: update_child_memory without GRANTED consent fails
        res = await assistant.update_child_memory(None, word_learned="apple")
        assert "Permission denied" in res
        mock_update.assert_not_called()

        # Invalid transition: record_consent_decision when not PENDING does not change state
        res = await assistant.record_consent_decision(None, granted=True)
        assert "Cannot record decision" in res
        assert assistant.consent_state == "NO_CONSENT"

        # D: Asking for consent, followed by refusal
        await assistant.request_memory_save_consent(None)
        assert assistant.consent_state == "PENDING"
        await assistant.record_consent_decision(None, granted=False)
        assert assistant.consent_state == "DENIED"
        res = await assistant.update_child_memory(None, word_learned="apple")
        assert "Permission denied" in res
        mock_update.assert_not_called()

        # Reset state for next scenario
        assistant.consent_state = "NO_CONSENT"

        # E: Asking for consent, followed by approval
        await assistant.request_memory_save_consent(None)
        assert assistant.consent_state == "PENDING"
        await assistant.record_consent_decision(None, granted=True)
        assert assistant.consent_state == "GRANTED"

        # Save should now succeed and target the correct child_id
        mock_update.return_value.matched_count = 1
        res = await assistant.update_child_memory(None, word_learned="apple")
        assert "success" in res
        assert mock_update.call_count >= 1
        args, _kwargs = mock_update.call_args_list[0]
        # A & B: Ensure DB operation uses internal child_id
        assert str(args[0]["_id"]) == "111111111111111111111111"

        # F: After saving, consent resets and subsequent saves are blocked
        assert assistant.consent_state == "NO_CONSENT"
        mock_update.reset_mock()
        res = await assistant.update_child_memory(None, word_learned="ball")
        assert "Permission denied" in res
        mock_update.assert_not_called()
