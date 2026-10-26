# D4 final acceptance follow-ups

Status: D4 accepted in substance at 40b269a3; final Q1-Q4 acceptance pending.

1. Q1: observe startup cancel-winner storage failure and fresh held-reason mapping reds, then contain the failure per item. Mutation-check both properties.
2. Q2: align reservation_resume contract with existing no-private-brief-read behavior.
3. Q3: explicitly retain and test the cross-file body-orphan seam without changing the measured write path.
4. Q4: document intentional private invariants and regression seams. Run focused modules, artifact selection and one full builder discovery after the fix. Send final pin for independent review.

No timing limits change. No R3 implementation, operator routes, capacity, activation or push.

## Implemented delta and provenance

Only artifact_service.py changes product behavior: recover_startup catches storage failures in its cancel-winner handler and continues selected items; its generic error projection uses a fresh request read, falling back to storage_unavailable if refresh fails. The lookup is observational and uses the store getter's own lock outside the engine boundary. Ordinary A/B/C paths and the diagnostic writer remain unchanged.

Q2 is contract-only: reservation_resume does not require a private brief, which may not yet exist on its source failure path. Q3 keeps the existing cross-file body-orphan seam, now explicitly documented and covered at candidate encoding. Q4 keeps the private compatibility keyword, regression wrapper, internal code and fail-closed origin invariant, with the one-block A1 lifetime and plain ArtifactUnavailable rethrow documented in PHASES.

Historical final gate: product4968, toolsf2a6e52, all190 raw comparisons passed. No new timing run: no Q2 brief read or Q3 body-path check was added. Q1 affects exceptional startup warning handling only. Every prior miss and invalid attempt stays in TICKET-20-D4-FINAL-GATE.md. Unknown earlier roughly1.1s stalls remain unattributed. Max-source admit_saved A was median0.1608s/max0.1749s in the final gate.

## Observed red before source

Two new test methods, four assertion failures,0.679s. The cancel-winner test uses a real B-phase cancellation and injected repair storage fault; before the fix it returns an error instead of a recovery result. The mapping test injects fresh fulfilled/cancelled/unreadable observations after an item failure and verifies the new read and warning projection.

```text
FFFF
======================================================================
FAIL: test_startup_cancel_winner_storage_fault_is_held_per_item (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_startup_cancel_winner_storage_fault_is_held_per_item)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_diagnostic_phases.py", line 284, in test_startup_cancel_winner_storage_fault_is_held_per_item
    self.assertEqual(other[0],'ok');self.assertEqual(outcome[0],'ok')
                                    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
AssertionError: 'error' != 'ok'
- error
+ ok


======================================================================
FAIL: test_startup_storage_mapping_reads_fresh_state_and_falls_back_on_read_failure (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_startup_storage_mapping_reads_fresh_state_and_falls_back_on_read_failure) (fresh_state='fulfilled')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_diagnostic_phases.py", line 306, in test_startup_storage_mapping_reads_fresh_state_and_falls_back_on_read_failure
    self.assertEqual(result['scanned'],1);self.assertEqual(fresh_reads,[audit['dispatch_id']])
                                          ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Lists differ: [] != ['453b0fa209a4532f8a3eba140b8632ea']

Second list contains 1 additional elements.
First extra element 0:
'453b0fa209a4532f8a3eba140b8632ea'

- []
+ ['453b0fa209a4532f8a3eba140b8632ea']

======================================================================
FAIL: test_startup_storage_mapping_reads_fresh_state_and_falls_back_on_read_failure (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_startup_storage_mapping_reads_fresh_state_and_falls_back_on_read_failure) (fresh_state='cancelled')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_diagnostic_phases.py", line 306, in test_startup_storage_mapping_reads_fresh_state_and_falls_back_on_read_failure
    self.assertEqual(result['scanned'],1);self.assertEqual(fresh_reads,[audit['dispatch_id']])
                                          ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Lists differ: [] != ['6207df6bdac7522886b363e005202cd3']

Second list contains 1 additional elements.
First extra element 0:
'6207df6bdac7522886b363e005202cd3'

- []
+ ['6207df6bdac7522886b363e005202cd3']

======================================================================
FAIL: test_startup_storage_mapping_reads_fresh_state_and_falls_back_on_read_failure (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_startup_storage_mapping_reads_fresh_state_and_falls_back_on_read_failure) (fresh_state='unreadable')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_diagnostic_phases.py", line 306, in test_startup_storage_mapping_reads_fresh_state_and_falls_back_on_read_failure
    self.assertEqual(result['scanned'],1);self.assertEqual(fresh_reads,[audit['dispatch_id']])
                                          ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Lists differ: [] != ['9cc41181533750c48229f68d3ae877e3']

Second list contains 1 additional elements.
First extra element 0:
'9cc41181533750c48229f68d3ae877e3'

- []
+ ['9cc41181533750c48229f68d3ae877e3']

----------------------------------------------------------------------
Ran 2 tests in 0.679s

FAILED (failures=4)

```

## Functional and mutation verification

- Q1 methods plus Q3 baseline seam:3 tests OK0.894s.
- D4/A1/MCP/R1/R2 owner/integration/oversize/saturation focused selection:161 tests OK44.170s, shellbe8cf19c.
- Mutation harness:17 assertion-based kills, zero error-only kills; source unchanged by harness. New mutants remove cancel-winner storage containment and revert warning projection to snapshot state. Initial anchor attempt was INSTRUMENT-INVALID, not a kill; retained in .audit-tmp/d4-q-mutation-invalid-anchor.json and shell30b24e78. Corrected anchor is the only harness correction, successful shell349bcdd5.
- Artifact selection:50 modules,437 tests OK231.042s. The embedded import benchmark max0.196578s is in-suite regression evidence, not a new D4 timing gate. ONE builder full root discovery followed sequentially in shell349bcdd5:221 modules,1817 tests OK337.595s,4 skips. No suites overlapped and no timing gate was rerun.

```json
{
  "kind": "D4 in-process mutation proof, no product edits, not a timing gate",
  "mutations": [
    {
      "label": "startup cancel-winner storage containment",
      "test": "test_startup_cancel_winner_storage_fault_is_held_per_item",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_startup_cancel_winner_storage_fault_is_held_per_item (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_startup_cancel_winner_storage_fault_is_held_per_item)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 284, in test_startup_cancel_winner_storage_fault_is_held_per_item\n    self.assertEqual(other[0],'ok');self.assertEqual(outcome[0],'ok')\n                                    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\nAssertionError: 'error' != 'ok'\n- error\n+ ok\n\n\n----------------------------------------------------------------------\nRan 1 test in 0.252s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "startup fresh warning mapping",
      "test": "test_startup_storage_mapping_reads_fresh_state_and_falls_back_on_read_failure",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_startup_storage_mapping_reads_fresh_state_and_falls_back_on_read_failure (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_startup_storage_mapping_reads_fresh_state_and_falls_back_on_read_failure) (fresh_state='fulfilled')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 308, in test_startup_storage_mapping_reads_fresh_state_and_falls_back_on_read_failure\n    self.assertEqual(result['held'],[{'request_id':audit['request_id'],\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n        'dispatch_id':audit['dispatch_id'],'reason':expected}])\n        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: Lists differ: [{'re[75 chars]5b5487c940c29fecbe61', 'reason': 'storage_unavailable'}] != [{'re[75 chars]5b5487c940c29fecbe61', 'reason': 'operator_recovery_required'}]\n\nFirst differing element 0:\n{'req[73 chars]c5b5487c940c29fecbe61', 'reason': 'storage_unavailable'}\n{'req[73 chars]c5b5487c940c29fecbe61', 'reason': 'operator_recovery_required'}\n\n  [{'dispatch_id': '8867685edc7c5b5487c940c29fecbe61',\n-   'reason': 'storage_unavailable',\n+   'reason': 'operator_recovery_required',\n    'request_id': 'f7023a214da34f0b8fbc23cbc7415cc0'}]\n\n----------------------------------------------------------------------\nRan 1 test in 0.426s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "receipt intent identity",
      "test": "test_foreign_receipt_and_second_settlement_are_refused_without_effect",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_foreign_receipt_and_second_settlement_are_refused_without_effect (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_foreign_receipt_and_second_settlement_are_refused_without_effect)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 513, in test_foreign_receipt_and_second_settlement_are_refused_without_effect\n    with patch.object(case.authority,'_settle_diagnostic_intent',settle):action()\n                                                                         ~~~~~~^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 95, in <lambda>\n    'reject':lambda:case.authority.reject_response(audit['brief_id'],'invalid structured response',instance),\n                    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_service.py\", line 130, in invoke\n    return self._packet_invocation(lambda: method(self, *args, **kwargs))\n           ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_service.py\", line 137, in _packet_invocation\n    return step()\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_service.py\", line 130, in <lambda>\n    return self._packet_invocation(lambda: method(self, *args, **kwargs))\n                                           ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_service.py\", line 775, in reject_response\n    return self._run_diagnostic_operation(lambda: self._reject_response_locked(brief_id, content, instance, received_truncated=received_truncated), origin='worker')\n           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_service.py\", line 167, in _run_diagnostic_operation\n    return self._settle_diagnostic_intent(intent, receipt, invocation_key=key)\n           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 510, in settle\n    with self.assertRaises(storage.ArtifactConflict):\n         ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: ArtifactConflict not raised\n\n----------------------------------------------------------------------\nRan 1 test in 0.272s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "receipt token",
      "test": "test_foreign_receipt_and_second_settlement_are_refused_without_effect",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_foreign_receipt_and_second_settlement_are_refused_without_effect (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_foreign_receipt_and_second_settlement_are_refused_without_effect)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 513, in test_foreign_receipt_and_second_settlement_are_refused_without_effect\n    with patch.object(case.authority,'_settle_diagnostic_intent',settle):action()\n                                                                         ~~~~~~^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 95, in <lambda>\n    'reject':lambda:case.authority.reject_response(audit['brief_id'],'invalid structured response',instance),\n                    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_service.py\", line 130, in invoke\n    return self._packet_invocation(lambda: method(self, *args, **kwargs))\n           ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_service.py\", line 137, in _packet_invocation\n    return step()\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_service.py\", line 130, in <lambda>\n    return self._packet_invocation(lambda: method(self, *args, **kwargs))\n                                           ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_service.py\", line 775, in reject_response\n    return self._run_diagnostic_operation(lambda: self._reject_response_locked(brief_id, content, instance, received_truncated=received_truncated), origin='worker')\n           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_service.py\", line 167, in _run_diagnostic_operation\n    return self._settle_diagnostic_intent(intent, receipt, invocation_key=key)\n           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 507, in settle\n    with self.assertRaises(storage.ArtifactConflict):\n         ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: ArtifactConflict not raised\n\n----------------------------------------------------------------------\nRan 1 test in 0.261s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "authority audit comparison",
      "test": "test_corrupt_guard_proof_pairs_cannot_become_terminal_winner_results",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_corrupt_guard_proof_pairs_cannot_become_terminal_winner_results (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_corrupt_guard_proof_pairs_cannot_become_terminal_winner_results) (field='audit_bytes')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 981, in test_corrupt_guard_proof_pairs_cannot_become_terminal_winner_results\n    self.assertEqual(outcome[0],'error');self.assertIsInstance(outcome[1],storage.ArtifactConflict)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'ok' != 'error'\n- ok\n+ error\n\n\n----------------------------------------------------------------------\nRan 1 test in 0.655s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "record digest pair",
      "test": "test_corrupt_guard_proof_pairs_cannot_become_terminal_winner_results",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_corrupt_guard_proof_pairs_cannot_become_terminal_winner_results (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_corrupt_guard_proof_pairs_cannot_become_terminal_winner_results) (field='record_digest')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 981, in test_corrupt_guard_proof_pairs_cannot_become_terminal_winner_results\n    self.assertEqual(outcome[0],'error');self.assertIsInstance(outcome[1],storage.ArtifactConflict)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'ok' != 'error'\n- ok\n+ error\n\n\n----------------------------------------------------------------------\nRan 1 test in 0.638s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "queue projection",
      "test": "test_reservation_resume_queue_changes_and_existing_fence_precedence",
      "killed": true,
      "failures": 3,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_reservation_resume_queue_changes_and_existing_fence_precedence (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_reservation_resume_queue_changes_and_existing_fence_precedence) (transition='absent_present')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 792, in test_reservation_resume_queue_changes_and_existing_fence_precedence\n    self.assertEqual(outcome[0],'error');self.assertIsInstance(outcome[1],storage.ArtifactConflict)\n                                         ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: ArtifactUnavailable('Artifact source packet is unavailable.') is not an instance of <class 'artifact_store.ArtifactConflict'>\n\n======================================================================\nFAIL: test_reservation_resume_queue_changes_and_existing_fence_precedence (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_reservation_resume_queue_changes_and_existing_fence_precedence) (transition='queued_claimed')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 792, in test_reservation_resume_queue_changes_and_existing_fence_precedence\n    self.assertEqual(outcome[0],'error');self.assertIsInstance(outcome[1],storage.ArtifactConflict)\n                                         ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: ArtifactUnavailable('Artifact source packet is unavailable.') is not an instance of <class 'artifact_store.ArtifactConflict'>\n\n======================================================================\nFAIL: test_reservation_resume_queue_changes_and_existing_fence_precedence (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_reservation_resume_queue_changes_and_existing_fence_precedence) (transition='new_fence')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 795, in test_reservation_resume_queue_changes_and_existing_fence_precedence\n    self.assertEqual(outcome[0],'ok');self.assertIsNone(outcome[1]['admission'])\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\nAssertionError: 'error' != 'ok'\n- error\n+ ok\n\n\n----------------------------------------------------------------------\nRan 1 test in 0.871s\n\nFAILED (failures=3)\n"
    },
    {
      "label": "saved result digest",
      "test": "test_saved_proof_ack_and_disposition_changes_refuse_c",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_saved_proof_ack_and_disposition_changes_refuse_c (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_saved_proof_ack_and_disposition_changes_refuse_c) (changed='record')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 879, in test_saved_proof_ack_and_disposition_changes_refuse_c\n    self.assertEqual(outcome[0],'error');self.assertIsInstance(outcome[1],storage.ArtifactConflict)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'ok' != 'error'\n- ok\n+ error\n\n\n----------------------------------------------------------------------\nRan 1 test in 0.888s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "ACK observation",
      "test": "test_saved_proof_ack_and_disposition_changes_refuse_c",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_saved_proof_ack_and_disposition_changes_refuse_c (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_saved_proof_ack_and_disposition_changes_refuse_c) (changed='ack')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 879, in test_saved_proof_ack_and_disposition_changes_refuse_c\n    self.assertEqual(outcome[0],'error');self.assertIsInstance(outcome[1],storage.ArtifactConflict)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'ok' != 'error'\n- ok\n+ error\n\n\n----------------------------------------------------------------------\nRan 1 test in 0.876s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "disposition observation",
      "test": "test_saved_proof_ack_and_disposition_changes_refuse_c",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_saved_proof_ack_and_disposition_changes_refuse_c (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_saved_proof_ack_and_disposition_changes_refuse_c) (changed='disposition')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 879, in test_saved_proof_ack_and_disposition_changes_refuse_c\n    self.assertEqual(outcome[0],'error');self.assertIsInstance(outcome[1],storage.ArtifactConflict)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'ok' != 'error'\n- ok\n+ error\n\n\n----------------------------------------------------------------------\nRan 1 test in 0.949s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "C active channel",
      "test": "test_resume_inactive_at_c_is_409_for_reservation_and_retained_modes",
      "killed": true,
      "failures": 2,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_resume_inactive_at_c_is_409_for_reservation_and_retained_modes (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_resume_inactive_at_c_is_409_for_reservation_and_retained_modes) (mode='resume')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 812, in test_resume_inactive_at_c_is_409_for_reservation_and_retained_modes\n    self.assertEqual(outcome[0],'error');self.assertIsInstance(outcome[1],storage.ArtifactConflict)\n                                         ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: ArtifactUnavailable('Artifact source packet is unavailable.') is not an instance of <class 'artifact_store.ArtifactConflict'>\n\n======================================================================\nFAIL: test_resume_inactive_at_c_is_409_for_reservation_and_retained_modes (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_resume_inactive_at_c_is_409_for_reservation_and_retained_modes) (mode='retained')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 812, in test_resume_inactive_at_c_is_409_for_reservation_and_retained_modes\n    self.assertEqual(outcome[0],'error');self.assertIsInstance(outcome[1],storage.ArtifactConflict)\n                                         ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: ArtifactUnavailable('Artifact source packet is unavailable.') is not an instance of <class 'artifact_store.ArtifactConflict'>\n\n----------------------------------------------------------------------\nRan 1 test in 0.408s\n\nFAILED (failures=2)\n"
    },
    {
      "label": "pre-B ownership check",
      "test": "test_pre_b_guard_rechecks_current_thread_ownership",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_pre_b_guard_rechecks_current_thread_ownership (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_pre_b_guard_rechecks_current_thread_ownership)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 765, in test_pre_b_guard_rechecks_current_thread_ownership\n    self.assertEqual(len(calls),2);self.assertEqual(writer.call_count,0)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^\nAssertionError: 1 != 2\n\n----------------------------------------------------------------------\nRan 1 test in 0.255s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "pre-A ownership check",
      "test": "test_diagnostic_driver_refuses_caller_held_boundary",
      "killed": true,
      "failures": 3,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_diagnostic_driver_refuses_caller_held_boundary (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_diagnostic_driver_refuses_caller_held_boundary) (lock='engine')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 394, in test_diagnostic_driver_refuses_caller_held_boundary\n    with lock,self.assertRaises(storage.ArtifactUnavailable) as caught:\n              ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: ArtifactUnavailable not raised\n\n======================================================================\nFAIL: test_diagnostic_driver_refuses_caller_held_boundary (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_diagnostic_driver_refuses_caller_held_boundary) (lock='catalog')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 394, in test_diagnostic_driver_refuses_caller_held_boundary\n    with lock,self.assertRaises(storage.ArtifactUnavailable) as caught:\n              ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: ArtifactUnavailable not raised\n\n======================================================================\nFAIL: test_diagnostic_driver_refuses_caller_held_boundary (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_diagnostic_driver_refuses_caller_held_boundary) (lock='authoring')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 394, in test_diagnostic_driver_refuses_caller_held_boundary\n    with lock,self.assertRaises(storage.ArtifactUnavailable) as caught:\n              ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: ArtifactUnavailable not raised\n\n----------------------------------------------------------------------\nRan 1 test in 0.482s\n\nFAILED (failures=3)\n"
    },
    {
      "label": "B failure must not fabricate receipt",
      "test": "test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry",
      "killed": true,
      "failures": 12,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry) (caller='cli')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 713, in test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry\n    self.assertEqual(len(at_b),1);self.assertEqual(settle.call_count,0)\n                                  ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 1 != 0\n\n======================================================================\nFAIL: test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry) (caller='reject')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 713, in test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry\n    self.assertEqual(len(at_b),1);self.assertEqual(settle.call_count,0)\n                                  ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 1 != 0\n\n======================================================================\nFAIL: test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry) (caller='brief')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 713, in test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry\n    self.assertEqual(len(at_b),1);self.assertEqual(settle.call_count,0)\n                                  ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 1 != 0\n\n======================================================================\nFAIL: test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry) (caller='delivery')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 713, in test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry\n    self.assertEqual(len(at_b),1);self.assertEqual(settle.call_count,0)\n                                  ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 1 != 0\n\n======================================================================\nFAIL: test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry) (caller='resume')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 713, in test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry\n    self.assertEqual(len(at_b),1);self.assertEqual(settle.call_count,0)\n                                  ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 1 != 0\n\n======================================================================\nFAIL: test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry) (caller='retained')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 713, in test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry\n    self.assertEqual(len(at_b),1);self.assertEqual(settle.call_count,0)\n                                  ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 1 != 0\n\n======================================================================\nFAIL: test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry) (caller='saved')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 713, in test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry\n    self.assertEqual(len(at_b),1);self.assertEqual(settle.call_count,0)\n                                  ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 1 != 0\n\n======================================================================\nFAIL: test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry) (caller='fulfilled')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 713, in test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry\n    self.assertEqual(len(at_b),1);self.assertEqual(settle.call_count,0)\n                                  ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 1 != 0\n\n======================================================================\nFAIL: test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry) (caller='ack')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 713, in test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry\n    self.assertEqual(len(at_b),1);self.assertEqual(settle.call_count,0)\n                                  ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 1 != 0\n\n======================================================================\nFAIL: test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry) (caller='startup')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 713, in test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry\n    self.assertEqual(len(at_b),1);self.assertEqual(settle.call_count,0)\n                                  ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 1 != 0\n\n======================================================================\nFAIL: test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry) (caller='unmatched')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 713, in test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry\n    self.assertEqual(len(at_b),1);self.assertEqual(settle.call_count,0)\n                                  ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 1 != 0\n\n======================================================================\nFAIL: test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry) (caller='startup_unmatched')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 713, in test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry\n    self.assertEqual(len(at_b),1);self.assertEqual(settle.call_count,0)\n                                  ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 1 != 0\n\n----------------------------------------------------------------------\nRan 1 test in 2.416s\n\nFAILED (failures=12)\n"
    },
    {
      "label": "summary receipt id",
      "test": "test_overflow_summary_id_is_the_receipt_id",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_overflow_summary_id_is_the_receipt_id (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_overflow_summary_id_is_the_receipt_id)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 964, in test_overflow_summary_id_is_the_receipt_id\n    self.assertEqual(result['diagnostic_id'],summary['id']);self.assertNotEqual(result['diagnostic_id'],summary['latest_diagnostic_id'])\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: 'bb4e38ea39df5db6a34516f2cd38965d' != '6268fecd41245a4c8798929d90441828'\n- bb4e38ea39df5db6a34516f2cd38965d\n+ 6268fecd41245a4c8798929d90441828\n\n\n----------------------------------------------------------------------\nRan 1 test in 0.309s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "pre-C guard",
      "test": "test_second_writer_during_diagnostic_io_refuses_stale_settlement",
      "killed": true,
      "failures": 1,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_second_writer_during_diagnostic_io_refuses_stale_settlement (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_second_writer_during_diagnostic_io_refuses_stale_settlement) (caller='cli')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 193, in test_second_writer_during_diagnostic_io_refuses_stale_settlement\n    self.assertEqual(outcome[0],'error');self.assertIsInstance(outcome[1],storage.ArtifactConflict)\n                                         ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError: ArtifactInputError('Invalid Markdown. Correct the argument and submit again within the byte limit.') is not an instance of <class 'artifact_store.ArtifactConflict'>\n\n----------------------------------------------------------------------\nRan 1 test in 0.521s\n\nFAILED (failures=1)\n"
    },
    {
      "label": "origin capture",
      "test": "test_continuation_origins_and_all_guard_proofs_are_captured",
      "killed": true,
      "failures": 10,
      "errors": 0,
      "evidence": "assertion",
      "output": "======================================================================\nFAIL: test_continuation_origins_and_all_guard_proofs_are_captured (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_continuation_origins_and_all_guard_proofs_are_captured) (caller='reject')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 742, in test_continuation_origins_and_all_guard_proofs_are_captured\n    self.assertEqual(len(captured),1)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\nAssertionError: 0 != 1\n\n======================================================================\nFAIL: test_continuation_origins_and_all_guard_proofs_are_captured (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_continuation_origins_and_all_guard_proofs_are_captured) (caller='delivery')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 742, in test_continuation_origins_and_all_guard_proofs_are_captured\n    self.assertEqual(len(captured),1)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\nAssertionError: 0 != 1\n\n======================================================================\nFAIL: test_continuation_origins_and_all_guard_proofs_are_captured (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_continuation_origins_and_all_guard_proofs_are_captured) (caller='resume')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 742, in test_continuation_origins_and_all_guard_proofs_are_captured\n    self.assertEqual(len(captured),1)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\nAssertionError: 0 != 1\n\n======================================================================\nFAIL: test_continuation_origins_and_all_guard_proofs_are_captured (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_continuation_origins_and_all_guard_proofs_are_captured) (caller='retained')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 742, in test_continuation_origins_and_all_guard_proofs_are_captured\n    self.assertEqual(len(captured),1)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\nAssertionError: 0 != 1\n\n======================================================================\nFAIL: test_continuation_origins_and_all_guard_proofs_are_captured (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_continuation_origins_and_all_guard_proofs_are_captured) (caller='saved')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 742, in test_continuation_origins_and_all_guard_proofs_are_captured\n    self.assertEqual(len(captured),1)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\nAssertionError: 0 != 1\n\n======================================================================\nFAIL: test_continuation_origins_and_all_guard_proofs_are_captured (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_continuation_origins_and_all_guard_proofs_are_captured) (caller='fulfilled')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 742, in test_continuation_origins_and_all_guard_proofs_are_captured\n    self.assertEqual(len(captured),1)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\nAssertionError: 0 != 1\n\n======================================================================\nFAIL: test_continuation_origins_and_all_guard_proofs_are_captured (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_continuation_origins_and_all_guard_proofs_are_captured) (caller='ack')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 742, in test_continuation_origins_and_all_guard_proofs_are_captured\n    self.assertEqual(len(captured),1)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\nAssertionError: 0 != 1\n\n======================================================================\nFAIL: test_continuation_origins_and_all_guard_proofs_are_captured (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_continuation_origins_and_all_guard_proofs_are_captured) (caller='startup')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 742, in test_continuation_origins_and_all_guard_proofs_are_captured\n    self.assertEqual(len(captured),1)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\nAssertionError: 0 != 1\n\n======================================================================\nFAIL: test_continuation_origins_and_all_guard_proofs_are_captured (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_continuation_origins_and_all_guard_proofs_are_captured) (caller='unmatched')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 742, in test_continuation_origins_and_all_guard_proofs_are_captured\n    self.assertEqual(len(captured),1)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\nAssertionError: 0 != 1\n\n======================================================================\nFAIL: test_continuation_origins_and_all_guard_proofs_are_captured (tests.test_artifact_diagnostic_phases.ArtifactDiagnosticPhaseTests.test_continuation_origins_and_all_guard_proofs_are_captured) (caller='startup_unmatched')\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\tests\\test_artifact_diagnostic_phases.py\", line 742, in test_continuation_origins_and_all_guard_proofs_are_captured\n    self.assertEqual(len(captured),1)\n    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^\nAssertionError: 0 != 1\n\n----------------------------------------------------------------------\nRan 1 test in 2.260s\n\nFAILED (failures=10)\n"
    }
  ],
  "source_sha256": {
    "C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_service.py": "c444597094e5dc6c4a9bcda40de9f035f70fb9bf6bd44f2215e5ceb596b47f68",
    "C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\artifact_store.py": "6c92e79837400e79444353d1a10c6679ac6761db07bb8a2f48062fd75a212f1d",
    "C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\mcp_bridge.py": "265dd38d36be915b8df6040222cac4de878ef9f8d498127cf99c1b0c253141b8"
  },
  "source_unchanged": true,
  "pass": true
}
```

## Post-Q source hashes

|File|SHA256|
|---|---|
|artifact_store.py|6c92e79837400e79444353d1a10c6679ac6761db07bb8a2f48062fd75a212f1d|
|artifact_service.py|c444597094e5dc6c4a9bcda40de9f035f70fb9bf6bd44f2215e5ceb596b47f68|
|api_seats.py|a638aa9711b3b25e522654cee68fb91000e1349040cc2bd62fef034ed665c13d|
|mcp_bridge.py|265dd38d36be915b8df6040222cac4de878ef9f8d498127cf99c1b0c253141b8|

## Final functional receipt

Q1-Q4 work is implemented/documented and builder verified. Final independent review remains pending. The unit starts at closed A1 tip2c34bbfb159a3334ad4ba66eb7a8fbd4175594ca; no push or activation is authorized. R2 earlier missed gates and all D4 attempt history remain in the final gate document. Capability stays empty. The reviewer may inspect the Q1-only product diff against40b269a3 and reuse its preceding static audit for unchanged product regions.

The following is the retained sequential runner output, including the corrected mutation result,437 artifact tests and ONE1817-test discovery. Injected storage/launch refusal messages are expected fixture output, with overall OK as printed.

```text
2026-10-26T17:29:36.401Z === started (pid 2848, agent 6c2a7241-eb44-423f-8d53-eb4cc5425ad8, shell: C:\Program Files\PowerShell\7\pwsh.exe)
2026-10-26T17:29:36.969Z | {"label": "startup cancel-winner storage containment", "test": "test_startup_cancel_winner_storage_fault_is_held_per_item", "killed": true, "failures": 1, "errors": 0, "evidence": "assertion"}
2026-10-26T17:29:37.398Z | {"label": "startup fresh warning mapping", "test": "test_startup_storage_mapping_reads_fresh_state_and_falls_back_on_read_failure", "killed": true, "failures": 1, "errors": 0, "evidence": "assertion"}
2026-10-26T17:29:37.672Z | {"label": "receipt intent identity", "test": "test_foreign_receipt_and_second_settlement_are_refused_without_effect", "killed": true, "failures": 1, "errors": 0, "evidence": "assertion"}
2026-10-26T17:29:37.934Z | {"label": "receipt token", "test": "test_foreign_receipt_and_second_settlement_are_refused_without_effect", "killed": true, "failures": 1, "errors": 0, "evidence": "assertion"}
2026-10-26T17:29:38.591Z | {"label": "authority audit comparison", "test": "test_corrupt_guard_proof_pairs_cannot_become_terminal_winner_results", "killed": true, "failures": 1, "errors": 0, "evidence": "assertion"}
2026-10-26T17:29:39.231Z | {"label": "record digest pair", "test": "test_corrupt_guard_proof_pairs_cannot_become_terminal_winner_results", "killed": true, "failures": 1, "errors": 0, "evidence": "assertion"}
2026-10-26T17:29:40.104Z | {"label": "queue projection", "test": "test_reservation_resume_queue_changes_and_existing_fence_precedence", "killed": true, "failures": 3, "errors": 0, "evidence": "assertion"}
2026-10-26T17:29:40.994Z | {"label": "saved result digest", "test": "test_saved_proof_ack_and_disposition_changes_refuse_c", "killed": true, "failures": 1, "errors": 0, "evidence": "assertion"}
2026-10-26T17:29:41.872Z | {"label": "ACK observation", "test": "test_saved_proof_ack_and_disposition_changes_refuse_c", "killed": true, "failures": 1, "errors": 0, "evidence": "assertion"}
2026-10-26T17:29:42.824Z | {"label": "disposition observation", "test": "test_saved_proof_ack_and_disposition_changes_refuse_c", "killed": true, "failures": 1, "errors": 0, "evidence": "assertion"}
2026-10-26T17:29:43.234Z | {"label": "C active channel", "test": "test_resume_inactive_at_c_is_409_for_reservation_and_retained_modes", "killed": true, "failures": 2, "errors": 0, "evidence": "assertion"}
2026-10-26T17:29:43.490Z | {"label": "pre-B ownership check", "test": "test_pre_b_guard_rechecks_current_thread_ownership", "killed": true, "failures": 1, "errors": 0, "evidence": "assertion"}
2026-10-26T17:29:43.973Z | {"label": "pre-A ownership check", "test": "test_diagnostic_driver_refuses_caller_held_boundary", "killed": true, "failures": 3, "errors": 0, "evidence": "assertion"}
2026-10-26T17:29:46.390Z | {"label": "B failure must not fabricate receipt", "test": "test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry", "killed": true, "failures": 12, "errors": 0, "evidence": "assertion"}
2026-10-26T17:29:46.701Z | {"label": "summary receipt id", "test": "test_overflow_summary_id_is_the_receipt_id", "killed": true, "failures": 1, "errors": 0, "evidence": "assertion"}
2026-10-26T17:29:47.223Z | {"label": "pre-C guard", "test": "test_second_writer_during_diagnostic_io_refuses_stale_settlement", "killed": true, "failures": 1, "errors": 0, "evidence": "assertion"}
2026-10-26T17:29:49.485Z | {"label": "origin capture", "test": "test_continuation_origins_and_all_guard_proofs_are_captured", "killed": true, "failures": 10, "errors": 0, "evidence": "assertion"}
2026-10-26T17:29:49.486Z | {"receipt": "C:\\Users\\SJG\\.traycer\\worktrees\\sjgold__agentchattr\\codex-ticket-20-r2-on-a1\\.audit-tmp\\d4-mutation-receipt.json", "pass": true}
2026-10-26T17:29:50.580Z err| C:\Users\SJG\Documents\CodePlayground\agentchattr\.venv-windows\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
2026-10-26T17:29:50.580Z err|   from starlette.testclient import TestClient as TestClient  # noqa
2026-10-26T17:29:50.599Z | {'kind': 'builder artifact-module selection, NOT full discovery', 'interpreter': 'C:\\Users\\SJG\\Documents\\CodePlayground\\agentchattr\\.venv-windows\\Scripts\\python.exe', 'modules': 50, 'tests': 437}
2026-10-26T17:33:41.640Z err| .....................................................................................................................................................................................................................................................................................................................................................................................................................................................
2026-10-26T17:33:41.640Z err| ----------------------------------------------------------------------
2026-10-26T17:33:41.640Z err| Ran 437 tests in 231.042s
2026-10-26T17:33:41.640Z err| 
2026-10-26T17:33:41.640Z | {"method": "store/catalog real-files Windows default atomic_json", "portable_envelope_bytes": 4194304, "existing_lineages": 100, "existing_versions": 100, "requests": 128, "versions": 128, "packet_objects": 128, "zip_member_count": 262, "baseline_seconds": [0.000381799996830523, 0.0003939000889658928, 0.0005513000069186091, 0.00043429993093013763, 0.0005794999888166785, 0.00040250003803521395, 0.000503100105561316, 0.0003928000805899501, 0.0003877000417560339, 0.00047740002628415823], "samples_seconds": [0.16329199995379895, 0.16110359993763268, 0.15733109996654093, 0.19657820009160787, 0.19241270003840327, 0.17862929997500032, 0.1655423000920564, 0.1633239999646321, 0.15996309998445213, 0.1606358999852091], "maximum_seconds": 0.19657820009160787, "limit_seconds": 0.3, "includes_metadata_parse": true, "includes_whole_index_validation": true, "fsync_mocked": false}
2026-10-26T17:33:41.641Z err| OK
2026-10-26T17:33:42.834Z err| C:\Users\SJG\Documents\CodePlayground\agentchattr\.venv-windows\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
2026-10-26T17:33:42.834Z err|   from starlette.testclient import TestClient as TestClient  # noqa
2026-10-26T17:33:43.147Z | {'kind': 'D4 builder full root test-module discovery, namespace-safe', 'interpreter': 'C:\\Users\\SJG\\Documents\\CodePlayground\\agentchattr\\.venv-windows\\Scripts\\python.exe', 'modules': 221, 'tests': 1817}
2026-10-26T17:37:39.055Z err| .........................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................Channel state is unavailable; publication and new claims are held.
2026-10-26T17:37:42.701Z err| .............................................................................................................Session 2: failed to persist dispatch for claude (OSError)
2026-10-26T17:37:50.176Z err| ................................................................................................................................Scheduled attempt could not be saved; nothing was published.
2026-10-26T17:37:50.275Z err| ...Scheduled publication was not confirmed (OSError).
2026-10-26T17:37:50.309Z err| .Scheduled delivery bookkeeping could not be saved; the attempt remains reserved.
2026-10-26T17:37:50.336Z err| .Scheduled delivery bookkeeping could not be saved; the attempt remains reserved.
2026-10-26T17:37:50.585Z err| ..........Scheduled publication was not confirmed (OSError).
2026-10-26T17:37:50.637Z err| .Scheduled publication was not confirmed (OSError).
2026-10-26T17:37:52.746Z err| .............................................................Session 2: failed to persist dispatch for cli-4d8efa15-60e1fdc03ce9 (OSError)
2026-10-26T17:37:54.405Z err| ..................................Session 1: failed to persist dispatch for cli-4d8efa15-8dfea48abfad (OSError)
2026-10-26T17:37:54.498Z err| .Session 1: failed to persist dispatch for cli-4d8efa15-33438c440c71 (OSError)
2026-10-26T17:37:54.594Z err| .Session 1: failed to persist dispatch for cli-4d8efa15-381170f1230f (OSError)
2026-10-26T17:38:04.068Z err| ........................................................................................................................Session 1: failed to persist dispatch for codex (OSError)
2026-10-26T17:38:07.963Z | {"method": "store/catalog real-files Windows default atomic_json", "portable_envelope_bytes": 4194304, "existing_lineages": 100, "existing_versions": 100, "requests": 128, "versions": 128, "packet_objects": 128, "zip_member_count": 262, "baseline_seconds": [0.0005506000015884638, 0.00038849993143230677, 0.000404000049456954, 0.000394199974834919, 0.0005321999778971076, 0.00046440004371106625, 0.0004616000223904848, 0.0004991000751033425, 0.0004797999281436205, 0.0005629999795928597], "samples_seconds": [0.17327379994094372, 0.1693572000367567, 0.1685451999073848, 0.1635821999516338, 0.1626836999785155, 0.1604201999725774, 0.15750959992874414, 0.1603894999716431, 0.1594540000660345, 0.17254179995507002], "maximum_seconds": 0.17327379994094372, "limit_seconds": 0.3, "includes_metadata_parse": true, "includes_whole_index_validation": true, "fsync_mocked": false}
2026-10-26T17:38:07.963Z |   Using tmux session: owned
2026-10-26T17:38:07.963Z |   Reattach: tmux attach -t owned
2026-10-26T17:38:07.963Z |   Session already exists; preserved. Choose another seat or stop its owner first.
2026-10-26T17:38:07.963Z |   Warning: AGENTCHATTR_PORT='not-a-number' is not a valid integer, ignoring
2026-10-26T17:38:07.963Z |   MCP proxy: port 63819
2026-10-26T17:38:07.963Z |   MCP proxy: port 53756
2026-10-26T17:38:07.963Z |   Using tmux session: agentchattr-claude-1
2026-10-26T17:38:07.963Z |   Reattach: tmux attach -t agentchattr-claude-1
2026-10-26T17:38:07.964Z |   Child exit receipt unavailable; attach success does not prove child success.
2026-10-26T17:38:07.964Z |   [wrapper] VT enable (stdout): 0x0003 -> 0x0007 [ok]
2026-10-26T17:38:14.817Z err| .........................................................................sss.................Launch could not complete: Agent template is not configured. Add it to config.local.toml before launching.
2026-10-26T17:38:36.461Z err| .........................................................................................................................................................................Session 2: failed to persist dispatch for cli-4d8efa15-12b945f60f08 (OSError)
2026-10-26T17:38:36.902Z err| ....Session 2: failed to persist dispatch for cli-4d8efa15-2b14ae4a8d74 (OSError)
2026-10-26T17:38:46.991Z err| ...................................................................................................................................................................................Artifact ownership binding is unavailable; artifact work is held.
2026-10-26T17:38:47.007Z err| .Artifact ownership binding is unavailable; artifact work is held.
2026-10-26T17:39:20.742Z err| .....................................................................................................................................................................................................................................................................................................................................................................................s......
2026-10-26T17:39:20.742Z | {
2026-10-26T17:39:20.742Z |   "server": "absent",
2026-10-26T17:39:20.742Z |   "environment_ready": false,
2026-10-26T17:39:20.742Z |   "checked_at": "2026-10-26T17:38:15.129669+00:00",
2026-10-26T17:39:20.742Z |   "agents": []
2026-10-26T17:39:20.742Z | }
2026-10-26T17:39:20.742Z |   MCP proxy: port 56567
2026-10-26T17:39:20.742Z |   MCP proxy: port 51235
2026-10-26T17:39:20.742Z |   MCP proxy: port 56161
2026-10-26T17:39:20.742Z |   MCP proxy: port 54463
2026-10-26T17:39:20.742Z |   MCP proxy: port 63526
2026-10-26T17:39:20.742Z err| ----------------------------------------------------------------------
2026-10-26T17:39:20.742Z err| Ran 1817 tests in 337.595s
2026-10-26T17:39:20.742Z err| 
2026-10-26T17:39:20.742Z err| OK (skipped=4)
2026-10-26T17:39:21.298Z === exited (code 0)

```
