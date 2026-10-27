# Reduced Ticket20 backend ROOT reds

Status: BACKEND RED SCOPE CLEARED by reviewer at2279329b; production HELD for independent execution and body audit of this pin. UI/transcript/screen/activation/push remain held. R3 remains deferred;23 next.

## Frozen interfaces and contract corrections

C1-C11 are folded into TICKET-20-22-REDUCED-RELEASE.md: identity-only ordered resolver/shared active identity lookup; mapped causes/global capability first; boundary status/replay with Needs recovery/imported; POST-only Origin with GET/HEAD compatibility, scoped prefix/header/constant-time/method/envelope rules; actual threading.Lock snapshot; packet/provenance/attachment/document allowlists and typed cap precheck; capture/manager I/O outside boundary and accepted packet-orphan seam; wall versus hold screen; corrected errors/cancel pre-read; NEW shared source-Stop wiring; descending completed-session discovery; closed version DTO; transcript admission/skip ordering later. No separate docs approval round is requested before red review.

## Observed result

27 methods, 16 FAIL entries and 20 ERROR entries, zero skips. Ran 27 tests in 1.530s. FAIL/ERROR entries include subtests and after-loop no-effect assertions, so they are not counts of distinct methods. Seven distinct behavioral methods fail,18 distinct infrastructure methods error, one replay fixture-defect method errors, and one guard method passes. Reviewer independently identified ERR-F: replay reused an immutable packet id; raw counts remain unchanged. All four files ran together against unchanged accepted product220f3400.

The first27-method corrected-fixture run before final route-table alignment had17 failures/20 errors; the final POST-only create + real GET status stub removes an extra no-effect failure without weakening authentication. The earliest25-method attempt had17 failures/19 errors, including one genuine fixture error calling QueueStore.inspect (which does not exist). It is retained in .audit-tmp/reduced20-first-red.txt; corrected tests read actual queue.records. No old receipt is represented as a clean red pin. This is functional red evolution, not performance sampling.

## Per-area reachability

|File / methods|Area|Observed / unobserved boundary|
|---|---|---|
|tests/test_artifact_operator_core.py (9)|resolver/status/replay|Missing artifact_operator and ArtifactService.request_status; owner setup before the missing seam ran. Remaining assertions require those real APIs.|
|tests/test_artifact_operator_routes.py (9)|middleware/routes|Five behavioral middleware methods reach current app middleware. Router/status/cancel/download/completed-list bodies require the missing artifact_operator/artifact_routes modules; post-import assertions are unobserved.|
|tests/test_artifact_source_builder.py (6)|source/snapshot|snapshot_selected and artifact_sources do not exist. Detachment/lock/cap/allowlist/legacy assertions after those missing seams are unobserved.|
|tests/test_artifact_source_stop_wiring.py (3)|Stop production wiring|Engine Stop and coordinated cancel_run reach actual stored state, which stays queued/queued. Fence assertions after that first failure are unobserved. Unrelated source guard passes.|

No production module is stubbed into existence. Missing-module/method exceptions are explicitly infrastructure reds, not a claim that their future bodies already discriminate. Existing FastAPI middleware is exercised with minimal real handlers matching the reduced route/method table. Filesystem/process/provider observations use existing real-temp-owner fixtures with controlled mock processes; no listener/model/provider/native acceptance. Imported setup reaches the missing status seam. The original replay fixture does NOT reach its missing operator seam: it collides with the first packet bytes. F1 corrects this with a fresh request/derived ids and an actual relaunch, as recorded in the production ledger.

Meaningful green preconditions: run all follow-on assertions, inspect typed outcomes and actual file/no-effect assertions; any body fixture mismatch is corrected and disclosed before claiming green. Recheck real source-Stop fence fields and correct replay after relaunch, not only missing APIs. No new full discovery or timing campaign is run while the known root reds remain red.

## Final retained runner output

```text
test_capability_off_refuses_before_any_manager_lookup (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_capability_off_refuses_before_any_manager_lookup) ... ERROR
test_default_author_uses_binding_identity_and_returns_only_identity (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_default_author_uses_binding_identity_and_returns_only_identity) ... ERROR
test_duplicate_active_identity_refuses_as_ambiguous (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_duplicate_active_identity_refuses_as_ambiguous) ... ERROR
test_first_candidate_cause_and_examined_count_are_deterministic (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_first_candidate_cause_and_examined_count_are_deterministic) ... ERROR
test_imported_status_is_read_only_without_needs_resume (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_imported_status_is_read_only_without_needs_resume) ... ERROR
test_public_status_prepared_without_queue_is_needs_recovery (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_public_status_prepared_without_queue_is_needs_recovery) ... ERROR
test_replay_uses_stored_intent_before_prepare_or_resolver (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_replay_uses_stored_intent_before_prepare_or_resolver) ... ERROR
test_resolver_manager_io_does_not_own_engine_catalog_boundary (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_resolver_manager_io_does_not_own_engine_catalog_boundary) ... ERROR
test_terminal_status_is_not_needs_resume_and_does_not_repair (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_terminal_status_is_not_needs_resume_and_does_not_repair) ... ERROR
test_bad_host_and_duplicate_security_headers_refuse (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_bad_host_and_duplicate_security_headers_refuse) ... 
  test_bad_host_and_duplicate_security_headers_refuse (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_bad_host_and_duplicate_security_headers_refuse) (headers={'x-session-token': 'OPERATOR_ONLY', 'origin': 'http://127.0.0.1:18300', 'host': 'attacker.invalid:18300'}) ... FAIL
  test_bad_host_and_duplicate_security_headers_refuse (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_bad_host_and_duplicate_security_headers_refuse) (headers=[('x-session-token', 'OPERATOR_ONLY'), ('x-session-token', 'OPERATOR_ONLY'), ('origin', 'http://127.0.0.1:18300')]) ... FAIL
  test_bad_host_and_duplicate_security_headers_refuse (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_bad_host_and_duplicate_security_headers_refuse) (headers=[('x-session-token', 'OPERATOR_ONLY'), ('host', '127.0.0.1:18300'), ('host', 'localhost:18300')]) ... FAIL
test_bad_host_and_duplicate_security_headers_refuse (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_bad_host_and_duplicate_security_headers_refuse) ... FAIL
test_completed_sessions_list_is_available_sorted_and_channel_checked (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_completed_sessions_list_is_available_sorted_and_channel_checked) ... ERROR
test_new_router_has_only_reduced_routes_and_fixed_download_policy (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_new_router_has_only_reduced_routes_and_fixed_download_policy) ... ERROR
test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint) ... 
  test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint) (media='text/plain', size=2) ... FAIL
  test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint) (media='application/json', size=31) ... FAIL
  test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint) (media='application/json', size=262145) ... FAIL
test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint) ... FAIL
test_post_requires_origin_but_get_allows_absent_origin (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_post_requires_origin_but_get_allows_absent_origin) ... FAIL
test_prefix_404_405_and_headers_are_scoped (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_prefix_404_405_and_headers_are_scoped) ... 
  test_prefix_404_405_and_headers_are_scoped (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_prefix_404_405_and_headers_are_scoped) (method='GET') ... FAIL
  test_prefix_404_405_and_headers_are_scoped (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_prefix_404_405_and_headers_are_scoped) (method='DELETE') ... FAIL
test_query_token_and_authorization_are_never_operator_fallback (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_query_token_and_authorization_are_never_operator_fallback) ... 
  test_query_token_and_authorization_are_never_operator_fallback (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_query_token_and_authorization_are_never_operator_fallback) (headers=()) ... FAIL
  test_query_token_and_authorization_are_never_operator_fallback (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_query_token_and_authorization_are_never_operator_fallback) (headers=('authorization',)) ... FAIL
  test_query_token_and_authorization_are_never_operator_fallback (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_query_token_and_authorization_are_never_operator_fallback) (headers=('x-session-token', 'origin')) ... FAIL
test_status_and_cancel_real_request_with_no_secret_projection (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_status_and_cancel_real_request_with_no_secret_projection) ... ERROR
test_version_download_is_exact_and_has_fixed_safe_headers (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_version_download_is_exact_and_has_fixed_safe_headers) ... ERROR
test_legacy_uid_collision_is_refused_not_renamed (tests.test_artifact_source_builder.ArtifactSourceBuilderTests.test_legacy_uid_collision_is_refused_not_renamed) ... ERROR
test_projection_allowlist_preserves_literal_text_not_server_metadata (tests.test_artifact_source_builder.ArtifactSourceBuilderTests.test_projection_allowlist_preserves_literal_text_not_server_metadata) ... ERROR
test_snapshot_missing_and_duplicate_ids_never_return_partial (tests.test_artifact_source_builder.ArtifactSourceBuilderTests.test_snapshot_missing_and_duplicate_ids_never_return_partial) ... 
  test_snapshot_missing_and_duplicate_ids_never_return_partial (tests.test_artifact_source_builder.ArtifactSourceBuilderTests.test_snapshot_missing_and_duplicate_ids_never_return_partial) (ids=[0, 999999]) ... ERROR
  test_snapshot_missing_and_duplicate_ids_never_return_partial (tests.test_artifact_source_builder.ArtifactSourceBuilderTests.test_snapshot_missing_and_duplicate_ids_never_return_partial) (ids=[0, 0]) ... ERROR
test_snapshot_selected_is_detached_and_channel_exact (tests.test_artifact_source_builder.ArtifactSourceBuilderTests.test_snapshot_selected_is_detached_and_channel_exact) ... ERROR
test_snapshot_selected_locks_once_without_recursive_lock_calls (tests.test_artifact_source_builder.ArtifactSourceBuilderTests.test_snapshot_selected_locks_once_without_recursive_lock_calls) ... ERROR
test_typed_packet_precheck_runs_before_full_content_walk (tests.test_artifact_source_builder.ArtifactSourceBuilderTests.test_typed_packet_precheck_runs_before_full_content_walk) ... ERROR
test_engine_stop_cancels_mid_run_artifact_and_fences_claim (tests.test_artifact_source_stop_wiring.ArtifactSourceStopWiringTests.test_engine_stop_cancels_mid_run_artifact_and_fences_claim) ... FAIL
test_shared_cancel_run_path_also_covers_reconciliation (tests.test_artifact_source_stop_wiring.ArtifactSourceStopWiringTests.test_shared_cancel_run_path_also_covers_reconciliation) ... FAIL
test_stop_does_not_cancel_unrelated_artifact_source (tests.test_artifact_source_stop_wiring.ArtifactSourceStopWiringTests.test_stop_does_not_cancel_unrelated_artifact_source) ... ok

======================================================================
ERROR: test_capability_off_refuses_before_any_manager_lookup (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_capability_off_refuses_before_any_manager_lookup)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_operator_core.py", line 35, in test_capability_off_refuses_before_any_manager_lookup
    case=self.context();resolve=self.resolver()
                                ~~~~~~~~~~~~~^^
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_operator_core.py", line 21, in resolver
    return importlib.import_module('artifact_operator').resolve_default_artifact_author
           ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\SJG\miniconda3\Lib\importlib\__init__.py", line 88, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1406, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1371, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1335, in _find_and_load_unlocked
ModuleNotFoundError: No module named 'artifact_operator'

======================================================================
ERROR: test_default_author_uses_binding_identity_and_returns_only_identity (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_default_author_uses_binding_identity_and_returns_only_identity)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_operator_core.py", line 32, in test_default_author_uses_binding_identity_and_returns_only_identity
    self.assertEqual(self.resolver()(session,case.authority),case.instance['identity_id'])
                     ~~~~~~~~~~~~~^^
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_operator_core.py", line 21, in resolver
    return importlib.import_module('artifact_operator').resolve_default_artifact_author
           ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\SJG\miniconda3\Lib\importlib\__init__.py", line 88, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1406, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1371, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1335, in _find_and_load_unlocked
ModuleNotFoundError: No module named 'artifact_operator'

======================================================================
ERROR: test_duplicate_active_identity_refuses_as_ambiguous (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_duplicate_active_identity_refuses_as_ambiguous)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_operator_core.py", line 61, in test_duplicate_active_identity_refuses_as_ambiguous
    case=self.context();resolve=self.resolver();row=deepcopy(case.instance);row['state']='active'
                                ~~~~~~~~~~~~~^^
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_operator_core.py", line 21, in resolver
    return importlib.import_module('artifact_operator').resolve_default_artifact_author
           ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\SJG\miniconda3\Lib\importlib\__init__.py", line 88, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1406, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1371, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1335, in _find_and_load_unlocked
ModuleNotFoundError: No module named 'artifact_operator'

======================================================================
ERROR: test_first_candidate_cause_and_examined_count_are_deterministic (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_first_candidate_cause_and_examined_count_are_deterministic)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_operator_core.py", line 53, in test_first_candidate_cause_and_examined_count_are_deterministic
    case=self.context();resolve=self.resolver();session=self.session(case)
                                ~~~~~~~~~~~~~^^
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_operator_core.py", line 21, in resolver
    return importlib.import_module('artifact_operator').resolve_default_artifact_author
           ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\SJG\miniconda3\Lib\importlib\__init__.py", line 88, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1406, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1371, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1335, in _find_and_load_unlocked
ModuleNotFoundError: No module named 'artifact_operator'

======================================================================
ERROR: test_imported_status_is_read_only_without_needs_resume (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_imported_status_is_read_only_without_needs_resume)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_operator_core.py", line 88, in test_imported_status_is_read_only_without_needs_resume
    result=case.authority.request_status(request)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'ArtifactService' object has no attribute 'request_status'

======================================================================
ERROR: test_public_status_prepared_without_queue_is_needs_recovery (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_public_status_prepared_without_queue_is_needs_recovery)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_operator_core.py", line 69, in test_public_status_prepared_without_queue_is_needs_recovery
    status=case.authority.request_status(audit['request_id'])
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'ArtifactService' object has no attribute 'request_status'

======================================================================
ERROR: test_replay_uses_stored_intent_before_prepare_or_resolver (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_replay_uses_stored_intent_before_prepare_or_resolver)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_operator_core.py", line 102, in test_replay_uses_stored_intent_before_prepare_or_resolver
    audit.update(source_run=source,scope=case.artifacts.put_packet(audit['request_id'],packet))
                                         ~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\artifact_store.py", line 1080, in put_packet
    return self._put_packet(request_id, packet)
           ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\channel_guards.py", line 21, in guarded
    return method(self, *args, **kwargs)
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\artifact_store.py", line 1088, in _put_packet
    self._put_bytes(self._object_path('packet', ids['packet_id']), _canonical(packet))
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\artifact_store.py", line 512, in _put_bytes
    raise ArtifactConflict('Different bytes already occupy this immutable artifact object.')
artifact_store.ArtifactConflict: Different bytes already occupy this immutable artifact object.

======================================================================
ERROR: test_resolver_manager_io_does_not_own_engine_catalog_boundary (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_resolver_manager_io_does_not_own_engine_catalog_boundary)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_operator_core.py", line 44, in test_resolver_manager_io_does_not_own_engine_catalog_boundary
    case=self.context();resolve=self.resolver();seen=[];original=case.manager.artifact_producer
                                ~~~~~~~~~~~~~^^
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_operator_core.py", line 21, in resolver
    return importlib.import_module('artifact_operator').resolve_default_artifact_author
           ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\SJG\miniconda3\Lib\importlib\__init__.py", line 88, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1406, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1371, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1335, in _find_and_load_unlocked
ModuleNotFoundError: No module named 'artifact_operator'

======================================================================
ERROR: test_terminal_status_is_not_needs_resume_and_does_not_repair (tests.test_artifact_operator_core.ArtifactOperatorCoreTests.test_terminal_status_is_not_needs_resume_and_does_not_repair)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_operator_core.py", line 77, in test_terminal_status_is_not_needs_resume_and_does_not_repair
    result=case.authority.request_status(audit['request_id'])
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'ArtifactService' object has no attribute 'request_status'

======================================================================
ERROR: test_completed_sessions_list_is_available_sorted_and_channel_checked (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_completed_sessions_list_is_available_sorted_and_channel_checked)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_operator_routes.py", line 118, in test_completed_sessions_list_is_available_sorted_and_channel_checked
    case,client=self.real_routes()
                ~~~~~~~~~~~~~~~~^^
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_operator_routes.py", line 80, in real_routes
    module=importlib.import_module('artifact_operator');routes=importlib.import_module('artifact_routes')
  File "C:\Users\SJG\miniconda3\Lib\importlib\__init__.py", line 88, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1406, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1371, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1335, in _find_and_load_unlocked
ModuleNotFoundError: No module named 'artifact_operator'

======================================================================
ERROR: test_new_router_has_only_reduced_routes_and_fixed_download_policy (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_new_router_has_only_reduced_routes_and_fixed_download_policy)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_operator_routes.py", line 68, in test_new_router_has_only_reduced_routes_and_fixed_download_policy
    module=importlib.import_module('artifact_routes')
  File "C:\Users\SJG\miniconda3\Lib\importlib\__init__.py", line 88, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1406, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1371, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1335, in _find_and_load_unlocked
ModuleNotFoundError: No module named 'artifact_routes'

======================================================================
ERROR: test_status_and_cancel_real_request_with_no_secret_projection (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_status_and_cancel_real_request_with_no_secret_projection)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_operator_routes.py", line 89, in test_status_and_cancel_real_request_with_no_secret_projection
    case,client=self.real_routes();audit=case.prepare()
                ~~~~~~~~~~~~~~~~^^
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_operator_routes.py", line 80, in real_routes
    module=importlib.import_module('artifact_operator');routes=importlib.import_module('artifact_routes')
  File "C:\Users\SJG\miniconda3\Lib\importlib\__init__.py", line 88, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1406, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1371, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1335, in _find_and_load_unlocked
ModuleNotFoundError: No module named 'artifact_operator'

======================================================================
ERROR: test_version_download_is_exact_and_has_fixed_safe_headers (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_version_download_is_exact_and_has_fixed_safe_headers)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_operator_routes.py", line 102, in test_version_download_is_exact_and_has_fixed_safe_headers
    case,client=self.real_routes();audit=case.prepare();case.claim(audit)
                ~~~~~~~~~~~~~~~~^^
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_operator_routes.py", line 80, in real_routes
    module=importlib.import_module('artifact_operator');routes=importlib.import_module('artifact_routes')
  File "C:\Users\SJG\miniconda3\Lib\importlib\__init__.py", line 88, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1406, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1371, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1335, in _find_and_load_unlocked
ModuleNotFoundError: No module named 'artifact_operator'

======================================================================
ERROR: test_legacy_uid_collision_is_refused_not_renamed (tests.test_artifact_source_builder.ArtifactSourceBuilderTests.test_legacy_uid_collision_is_refused_not_renamed)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_source_builder.py", line 71, in test_legacy_uid_collision_is_refused_not_renamed
    module=importlib.import_module('artifact_sources')
  File "C:\Users\SJG\miniconda3\Lib\importlib\__init__.py", line 88, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1406, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1371, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1335, in _find_and_load_unlocked
ModuleNotFoundError: No module named 'artifact_sources'

======================================================================
ERROR: test_projection_allowlist_preserves_literal_text_not_server_metadata (tests.test_artifact_source_builder.ArtifactSourceBuilderTests.test_projection_allowlist_preserves_literal_text_not_server_metadata)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_source_builder.py", line 58, in test_projection_allowlist_preserves_literal_text_not_server_metadata
    module=importlib.import_module('artifact_sources')
  File "C:\Users\SJG\miniconda3\Lib\importlib\__init__.py", line 88, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1406, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1371, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1335, in _find_and_load_unlocked
ModuleNotFoundError: No module named 'artifact_sources'

======================================================================
ERROR: test_snapshot_missing_and_duplicate_ids_never_return_partial (tests.test_artifact_source_builder.ArtifactSourceBuilderTests.test_snapshot_missing_and_duplicate_ids_never_return_partial) (ids=[0, 999999])
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_source_builder.py", line 44, in test_snapshot_missing_and_duplicate_ids_never_return_partial
    with self.subTest(ids=ids),self.assertRaises(ValueError):messages.snapshot_selected('review',ids)
                                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'MessageStore' object has no attribute 'snapshot_selected'

======================================================================
ERROR: test_snapshot_missing_and_duplicate_ids_never_return_partial (tests.test_artifact_source_builder.ArtifactSourceBuilderTests.test_snapshot_missing_and_duplicate_ids_never_return_partial) (ids=[0, 0])
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_source_builder.py", line 44, in test_snapshot_missing_and_duplicate_ids_never_return_partial
    with self.subTest(ids=ids),self.assertRaises(ValueError):messages.snapshot_selected('review',ids)
                                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'MessageStore' object has no attribute 'snapshot_selected'

======================================================================
ERROR: test_snapshot_selected_is_detached_and_channel_exact (tests.test_artifact_source_builder.ArtifactSourceBuilderTests.test_snapshot_selected_is_detached_and_channel_exact)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_source_builder.py", line 23, in test_snapshot_selected_is_detached_and_channel_exact
    saved=messages.snapshot_selected('review',[first['id']])
          ^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'MessageStore' object has no attribute 'snapshot_selected'

======================================================================
ERROR: test_snapshot_selected_locks_once_without_recursive_lock_calls (tests.test_artifact_source_builder.ArtifactSourceBuilderTests.test_snapshot_selected_locks_once_without_recursive_lock_calls)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_source_builder.py", line 38, in test_snapshot_selected_locks_once_without_recursive_lock_calls
    result=messages.snapshot_selected('review',[row['id']])
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'MessageStore' object has no attribute 'snapshot_selected'

======================================================================
ERROR: test_typed_packet_precheck_runs_before_full_content_walk (tests.test_artifact_source_builder.ArtifactSourceBuilderTests.test_typed_packet_precheck_runs_before_full_content_walk)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_source_builder.py", line 47, in test_typed_packet_precheck_runs_before_full_content_walk
    module=importlib.import_module('artifact_sources')
  File "C:\Users\SJG\miniconda3\Lib\importlib\__init__.py", line 88, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1406, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1371, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1335, in _find_and_load_unlocked
ModuleNotFoundError: No module named 'artifact_sources'

======================================================================
FAIL: test_bad_host_and_duplicate_security_headers_refuse (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_bad_host_and_duplicate_security_headers_refuse) (headers={'x-session-token': 'OPERATOR_ONLY', 'origin': 'http://127.0.0.1:18300', 'host': 'attacker.invalid:18300'})
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_operator_routes.py", line 45, in test_bad_host_and_duplicate_security_headers_refuse
    self.assertEqual(self.client.get(self.read,headers=headers).status_code,403)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 200 != 403

======================================================================
FAIL: test_bad_host_and_duplicate_security_headers_refuse (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_bad_host_and_duplicate_security_headers_refuse) (headers=[('x-session-token', 'OPERATOR_ONLY'), ('x-session-token', 'OPERATOR_ONLY'), ('origin', 'http://127.0.0.1:18300')])
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_operator_routes.py", line 45, in test_bad_host_and_duplicate_security_headers_refuse
    self.assertEqual(self.client.get(self.read,headers=headers).status_code,403)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 200 != 403

======================================================================
FAIL: test_bad_host_and_duplicate_security_headers_refuse (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_bad_host_and_duplicate_security_headers_refuse) (headers=[('x-session-token', 'OPERATOR_ONLY'), ('host', '127.0.0.1:18300'), ('host', 'localhost:18300')])
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_operator_routes.py", line 45, in test_bad_host_and_duplicate_security_headers_refuse
    self.assertEqual(self.client.get(self.read,headers=headers).status_code,403)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 200 != 403

======================================================================
FAIL: test_bad_host_and_duplicate_security_headers_refuse (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_bad_host_and_duplicate_security_headers_refuse)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_operator_routes.py", line 46, in test_bad_host_and_duplicate_security_headers_refuse
    self.assertEqual(self.calls,[])
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^
AssertionError: Lists differ: [True, True, True] != []

First list contains 3 additional elements.
First extra element 0:
True

- [True, True, True]
+ []

======================================================================
FAIL: test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint) (media='text/plain', size=2)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_operator_routes.py", line 64, in test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint
    self.assertEqual(response.status_code,code)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 200 != 400

======================================================================
FAIL: test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint) (media='application/json', size=31)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_operator_routes.py", line 64, in test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint
    self.assertEqual(response.status_code,code)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 200 != 400

======================================================================
FAIL: test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint) (media='application/json', size=262145)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_operator_routes.py", line 64, in test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint
    self.assertEqual(response.status_code,code)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 200 != 413

======================================================================
FAIL: test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_operator_routes.py", line 65, in test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint
    self.assertEqual(self.calls,[])
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^
AssertionError: Lists differ: [True, True, True] != []

First list contains 3 additional elements.
First extra element 0:
True

- [True, True, True]
+ []

======================================================================
FAIL: test_post_requires_origin_but_get_allows_absent_origin (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_post_requires_origin_but_get_allows_absent_origin)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_operator_routes.py", line 37, in test_post_requires_origin_but_get_allows_absent_origin
    self.assertEqual(response.status_code,403)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 200 != 403

======================================================================
FAIL: test_prefix_404_405_and_headers_are_scoped (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_prefix_404_405_and_headers_are_scoped) (method='GET')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_operator_routes.py", line 53, in test_prefix_404_405_and_headers_are_scoped
    self.assertEqual(response.headers.get('cache-control'),'no-store')
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: None != 'no-store'

======================================================================
FAIL: test_prefix_404_405_and_headers_are_scoped (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_prefix_404_405_and_headers_are_scoped) (method='DELETE')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_operator_routes.py", line 53, in test_prefix_404_405_and_headers_are_scoped
    self.assertEqual(response.headers.get('cache-control'),'no-store')
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: None != 'no-store'

======================================================================
FAIL: test_query_token_and_authorization_are_never_operator_fallback (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_query_token_and_authorization_are_never_operator_fallback) (headers=())
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_operator_routes.py", line 30, in test_query_token_and_authorization_are_never_operator_fallback
    self.assertEqual(response.status_code,403)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 405 != 403

======================================================================
FAIL: test_query_token_and_authorization_are_never_operator_fallback (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_query_token_and_authorization_are_never_operator_fallback) (headers=('authorization',))
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_operator_routes.py", line 30, in test_query_token_and_authorization_are_never_operator_fallback
    self.assertEqual(response.status_code,403)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 405 != 403

======================================================================
FAIL: test_query_token_and_authorization_are_never_operator_fallback (tests.test_artifact_operator_routes.ArtifactOperatorRouteTests.test_query_token_and_authorization_are_never_operator_fallback) (headers=('x-session-token', 'origin'))
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_operator_routes.py", line 30, in test_query_token_and_authorization_are_never_operator_fallback
    self.assertEqual(response.status_code,403)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 405 != 403

======================================================================
FAIL: test_engine_stop_cancels_mid_run_artifact_and_fences_claim (tests.test_artifact_source_stop_wiring.ArtifactSourceStopWiringTests.test_engine_stop_cancels_mid_run_artifact_and_fences_claim)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_source_stop_wiring.py", line 18, in test_engine_stop_cancels_mid_run_artifact_and_fences_claim
    self.assertEqual((row['state'],row['reason']),('cancelled','source_stopped'))
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Tuples differ: ('queued', 'queued') != ('cancelled', 'source_stopped')

First differing element 0:
'queued'
'cancelled'

- ('queued', 'queued')
+ ('cancelled', 'source_stopped')

======================================================================
FAIL: test_shared_cancel_run_path_also_covers_reconciliation (tests.test_artifact_source_stop_wiring.ArtifactSourceStopWiringTests.test_shared_cancel_run_path_also_covers_reconciliation)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\SJG\.traycer\worktrees\sjgold__agentchattr\codex-ticket-20-r2-on-a1\tests\test_artifact_source_stop_wiring.py", line 28, in test_shared_cancel_run_path_also_covers_reconciliation
    self.assertEqual((row['state'],row['reason']),('cancelled','source_stopped'))
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: Tuples differ: ('queued', 'queued') != ('cancelled', 'source_stopped')

First differing element 0:
'queued'
'cancelled'

- ('queued', 'queued')
+ ('cancelled', 'source_stopped')

----------------------------------------------------------------------
Ran 27 tests in 1.530s

FAILED (failures=16, errors=20)

```

## Product hashes, unchanged during red work

|File|SHA256|
|---|---|
|artifact_service.py|c444597094e5dc6c4a9bcda40de9f035f70fb9bf6bd44f2215e5ceb596b47f68|
|artifact_store.py|6c92e79837400e79444353d1a10c6679ac6761db07bb8a2f48062fd75a212f1d|
|api_seats.py|a638aa9711b3b25e522654cee68fb91000e1349040cc2bd62fef034ed665c13d|
|mcp_bridge.py|265dd38d36be915b8df6040222cac4de878ef9f8d498127cf99c1b0c253141b8|
|app.py|0bdef830c6e592b2755c8c5dd837ceac9a7a1eac3f01563271f346c861188576|
|store.py|33d70008efb3ab4207797648ca65de43f2dac0e8ad55985006d846df52b67041|
|session_engine.py|1a98b6529a748f1d002fc81970bd4e25a8e385aa9f35522c94347f3a64e8bd78|
|queue_coordinator.py|4f5dda260dae04eaaa9ce7cd778832ae90771cf04b8720d1beaf8e17d25e15da|
