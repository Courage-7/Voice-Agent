"""Comprehensive test runner for all unit tests across Phase 1 through Phase 8, and existing modules."""

import asyncio
import os
import sys
import types

# Ensure app package is discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Provide lightweight mock for pytest if pytest is not installed in the environment
if "pytest" not in sys.modules:
    try:
        import pytest
    except ImportError:
        mock_pytest = types.ModuleType("pytest")
        mock_pytest.mark = types.SimpleNamespace(asyncio=lambda f: f)
        sys.modules["pytest"] = mock_pytest

from tests.unit.test_prompts import test_system_prompt_builder, test_persona_retrieval, test_persona_service_prompt
from tests.unit.test_tools import (
    test_tool_registry_initialization,
    test_tool_metadata_contract,
    test_capability_routing_subsets,
    test_write_action_confirmation_policy,
    test_current_time_tool,
    test_memory_tools_execution,
    test_perplexity_tool_fallback,
)
from tests.unit.test_agent_graph import test_user_service_profile, test_agent_graph_execution
from tests.run_phase1_tests import run_tests as run_phase1_tests
from tests.unit.test_phase2_tools_and_identity import (
    test_email_provider_resolution_gmail_only,
    test_email_provider_resolution_outlook_only,
    test_email_provider_resolution_both_explicit,
    test_email_provider_resolution_both_ambiguous,
    test_calendar_provider_resolution_google_only,
    test_calendar_provider_resolution_both_ambiguous,
    test_dynamic_action_write_safety_boundary,
    test_workspace_tools_pass_entity_id,
    test_deepgram_schemas_exclude_meta_tools,
    test_search_emails_preserves_identifiers,
)
from tests.unit.test_phase3_composio_sessions import (
    test_get_or_create_user_session_caching,
    test_discover_user_tools,
    test_composio_fallback_mode_when_unconfigured,
)
from tests.unit.test_phase4_tts_and_voice_selection import (
    test_voice_catalog_allowlist_validation,
    test_user_voice_preference_persistence,
    test_deepgram_session_settings_with_active_voice,
    test_deepgram_session_update_speak,
    test_realtime_client_session_handles_update_speak,
)
from tests.unit.test_phase5_companion_prompts import (
    test_companion_default_persona_resolution,
    test_plain_text_no_markdown_rule,
    test_adaptive_sentence_length_rule,
    test_reset_loop_elimination_rule,
    test_tool_transitions_and_write_confirmation_rule,
    test_friendly_error_translation_rule,
    test_system_prompt_builder_integration,
)
from tests.unit.test_phase6_memory_and_context import (
    test_memory_summary_retrieval_and_prompt_injection,
    test_user_profile_context_injection,
    test_memory_service_graceful_fallback_on_error,
    test_interrupted_turn_transcript_reconciliation,
)
from tests.unit.test_phase7_complex_tasks import (
    test_complex_task_planner_decomposition,
    test_complex_task_execution_flow,
    test_complex_task_confirmation_pause_and_resume,
    test_complex_task_cancellation_on_declined_confirmation,
    test_run_complex_task_tool_integration,
)
from tests.unit.test_phase8_turn_taking_and_telemetry import (
    test_deepgram_session_settings_includes_endpointing,
    test_latency_telemetry_recording_and_percentiles,
    test_telemetry_endpoints_response_contracts,
)


def run_all():
    passed = 0
    failed = 0
    print("Running Full Voice Agent Test Suite...\n")

    # 1. Prompt tests (sync)
    print("[1] PROMPT & PERSONA TESTS:")
    for test_fn in [test_system_prompt_builder, test_persona_retrieval, test_persona_service_prompt]:
        try:
            test_fn()
            print(f"  [PASS] {test_fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {test_fn.__name__}: {e}")
            failed += 1

    # 2. Tool tests (sync & async)
    print("\n[2] TOOL REGISTRY & CONTRACT TESTS:")
    sync_tool_tests = [
        test_tool_registry_initialization,
        test_tool_metadata_contract,
        test_capability_routing_subsets,
    ]
    for test_fn in sync_tool_tests:
        try:
            test_fn()
            print(f"  [PASS] {test_fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {test_fn.__name__}: {e}")
            failed += 1

    async_tool_tests = [
        test_write_action_confirmation_policy,
        test_current_time_tool,
        test_memory_tools_execution,
        test_perplexity_tool_fallback,
    ]
    for test_fn in async_tool_tests:
        try:
            asyncio.run(test_fn())
            print(f"  [PASS] {test_fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {test_fn.__name__}: {e}")
            failed += 1

    # 3. Graph tests (async)
    print("\n[3] AGENT GRAPH & USER TESTS:")
    for test_fn in [test_user_service_profile, test_agent_graph_execution]:
        try:
            asyncio.run(test_fn())
            print(f"  [PASS] {test_fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {test_fn.__name__}: {e}")
            failed += 1

    # 4. Phase 1 Async tests
    print("\n[4] PHASE 1 VOICE STABILIZATION TESTS:")
    phase1_success = asyncio.run(run_phase1_tests())
    if not phase1_success:
        failed += 1
    else:
        passed += 5

    # 5. Phase 2 Async & Sync tests
    print("\n[5] PHASE 2 TOOLS, IDENTITY & SAFETY TESTS:")
    phase2_tests = [
        test_email_provider_resolution_gmail_only,
        test_email_provider_resolution_outlook_only,
        test_email_provider_resolution_both_explicit,
        test_email_provider_resolution_both_ambiguous,
        test_calendar_provider_resolution_google_only,
        test_calendar_provider_resolution_both_ambiguous,
        test_dynamic_action_write_safety_boundary,
        test_workspace_tools_pass_entity_id,
        test_search_emails_preserves_identifiers,
    ]
    for test_fn in phase2_tests:
        try:
            asyncio.run(test_fn())
            print(f"  [PASS] {test_fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {test_fn.__name__}: {e}")
            failed += 1

    try:
        test_deepgram_schemas_exclude_meta_tools()
        print(f"  [PASS] test_deepgram_schemas_exclude_meta_tools")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] test_deepgram_schemas_exclude_meta_tools: {e}")
        failed += 1

    # 6. Phase 3 Async tests
    print("\n[6] PHASE 3 COMPOSIO SESSIONS TESTS:")
    phase3_tests = [
        test_get_or_create_user_session_caching,
        test_discover_user_tools,
        test_composio_fallback_mode_when_unconfigured,
    ]
    for test_fn in phase3_tests:
        try:
            asyncio.run(test_fn())
            print(f"  [PASS] {test_fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {test_fn.__name__}: {e}")
            failed += 1

    # 7. Phase 4 TTS & Voice Selection tests
    print("\n[7] PHASE 4 TTS & VOICE SELECTION TESTS:")
    for test_fn in [test_voice_catalog_allowlist_validation, test_user_voice_preference_persistence]:
        try:
            test_fn()
            print(f"  [PASS] {test_fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {test_fn.__name__}: {e}")
            failed += 1

    phase4_async_tests = [
        test_deepgram_session_settings_with_active_voice,
        test_deepgram_session_update_speak,
        test_realtime_client_session_handles_update_speak,
    ]
    for test_fn in phase4_async_tests:
        try:
            asyncio.run(test_fn())
            print(f"  [PASS] {test_fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {test_fn.__name__}: {e}")
            failed += 1

    # 8. Phase 5 Companion Prompt & Conversational Behavior tests
    print("\n[8] PHASE 5 COMPANION PROMPT & CONVERSATIONAL TESTS:")
    phase5_tests = [
        test_companion_default_persona_resolution,
        test_plain_text_no_markdown_rule,
        test_adaptive_sentence_length_rule,
        test_reset_loop_elimination_rule,
        test_tool_transitions_and_write_confirmation_rule,
        test_friendly_error_translation_rule,
        test_system_prompt_builder_integration,
    ]
    for test_fn in phase5_tests:
        try:
            test_fn()
            print(f"  [PASS] {test_fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {test_fn.__name__}: {e}")
            failed += 1

    # 9. Phase 6 Memory & Context Integration tests
    print("\n[9] PHASE 6 MEMORY & CONTEXT INTEGRATION TESTS:")
    phase6_tests = [
        test_memory_summary_retrieval_and_prompt_injection,
        test_user_profile_context_injection,
        test_memory_service_graceful_fallback_on_error,
        test_interrupted_turn_transcript_reconciliation,
    ]
    for test_fn in phase6_tests:
        try:
            asyncio.run(test_fn())
            print(f"  [PASS] {test_fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {test_fn.__name__}: {e}")
            failed += 1

    # 10. Phase 7 LangGraph Complex Task Engine tests
    print("\n[10] PHASE 7 COMPLEX TASK ENGINE TESTS:")
    try:
        test_complex_task_planner_decomposition()
        print(f"  [PASS] test_complex_task_planner_decomposition")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] test_complex_task_planner_decomposition: {e}")
        failed += 1

    phase7_async_tests = [
        test_complex_task_execution_flow,
        test_complex_task_confirmation_pause_and_resume,
        test_complex_task_cancellation_on_declined_confirmation,
        test_run_complex_task_tool_integration,
    ]
    for test_fn in phase7_async_tests:
        try:
            asyncio.run(test_fn())
            print(f"  [PASS] {test_fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {test_fn.__name__}: {e}")
            failed += 1

    # 11. Phase 8 Advanced Turn-Taking & Telemetry tests
    print("\n[11] PHASE 8 ADVANCED TURN-TAKING & TELEMETRY TESTS:")
    phase8_tests = [
        test_deepgram_session_settings_includes_endpointing,
        test_latency_telemetry_recording_and_percentiles,
        test_telemetry_endpoints_response_contracts,
    ]
    for test_fn in phase8_tests:
        try:
            asyncio.run(test_fn())
            print(f"  [PASS] {test_fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {test_fn.__name__}: {e}")
            failed += 1

    print(f"\n==========================================")
    print(f"TOTAL UNIT TESTS: {passed} passed, {failed} failed.")
    print(f"==========================================")
    return failed == 0


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
