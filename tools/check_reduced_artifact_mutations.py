"""Targeted in-process reduced backend mutants; product source is never edited."""
from contextlib import contextmanager
import hashlib,inspect,io,json,sys,textwrap,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import artifact_operator as operator
import artifact_routes as routes
import artifact_sources as sources
import artifact_service as service
import queue_coordinator as queue
import store
from tests.test_artifact_operator_core import ArtifactOperatorCoreTests as Core
from tests.test_artifact_operator_routes import ArtifactOperatorRouteTests as Routes
from tests.test_artifact_source_builder import ArtifactSourceBuilderTests as Sources
from tests.test_artifact_source_stop_wiring import ArtifactSourceStopWiringTests as Stop
from tests.test_artifact_recovery import ArtifactRecoveryTests as Recovery

@contextmanager
def rewrite(owner,name,old,new):
    original=getattr(owner,name)
    source=textwrap.dedent(inspect.getsource(original))
    if old not in source:raise AssertionError((name,'mutation anchor absent'))
    namespace=dict(vars(sys.modules[original.__module__]))
    exec(compile(source.replace(old,new,1),'<reduced20-mutant>','exec'),namespace)
    with patch.object(owner,name,namespace[name]):yield

def main():
    checks=[
      ('author mappings',operator,'resolve_default_artifact_author',"cause = reasons.get(current['reason'], 'not_supported')","cause = 'no_live_instance'",Core,'test_reason_mapping_order_family_skip_and_inactive_duplicate'),
      ('global capability first',operator,'resolve_default_artifact_author',"if 'artifact-v1' not in runtime_protocol.SUPPORTED_CAPABILITIES:",'if False:',Core,'test_capability_off_refuses_before_any_manager_lookup'),
      ('concurrent packet winner replay',operator.ArtifactOperator,'create','if isinstance(error, storage.ArtifactConflict):','if False:',Core,'test_concurrent_saved_same_intent_wins_before_packet_staging'),
      ('replay before relaunch lookup',operator.ArtifactOperator,'create','if saved is not None:','if False:',Core,'test_replay_uses_stored_intent_before_prepare_or_resolver'),
      ('create caller boundary',operator.ArtifactOperator,'create','authority._assert_independent_boundary()','pass',Core,'test_status_and_cancel_reads_are_serialized_and_create_guard_is_no_effect'),
      ('public status serialized',service.ArtifactService,'request_status','with self.channels._boundary():',"with __import__('contextlib').nullcontext():",Core,'test_status_and_cancel_reads_are_serialized_and_create_guard_is_no_effect'),
      ('create202',operator.ArtifactOperator,'create','created=True)','created=False)',Core,'test_successful_create_replay_conflict_and_capture_stop_guard'),
      ('capture current Stop guard',operator.ArtifactOperator,'create',"or current.get('stop_id')",'or False',Core,'test_successful_create_replay_conflict_and_capture_stop_guard'),
      ('error durable state',operator.ArtifactOperator,'_failure',"durability = 'recorded' if row is not None else 'not_recorded'","durability = 'not_recorded'",Core,'test_summary_all_states_and_post_durable_cancel_failure'),
      ('Host guard',routes,'operator_prefix',"host[0].lower() not in hosts",'False',Routes,'test_bad_host_and_duplicate_security_headers_refuse'),
      ('bearer excluded',routes,'operator_prefix',"or values(b'authorization')",'or False',Routes,'test_security_raw_header_matrix_envelopes_and_legacy_namespace'),
      ('POST Origin',routes,'operator_prefix',"(request.method == 'POST' and len(origin) != 1)",'False',Routes,'test_post_requires_origin_but_get_allows_absent_origin'),
      ('query token excluded',routes,'operator_prefix',"or 'token' in request.query_params",'or False',Routes,'test_query_token_and_authorization_are_never_operator_fallback'),
      ('chunked cap',routes,'operator_prefix','if size > MAX_BODY:','if False:',Routes,'test_json_boundaries_chunked_body_and_scoped_errors'),
      ('duplicate JSON',routes,'_unique','if key in value:','if False:',Routes,'test_post_media_body_limit_and_duplicate_json_refuse_before_endpoint'),
      ('503 envelope preserved',routes,'operator_prefix',"elif response.status_code >= 500 and not getattr(request.state, 'artifact_error_envelope', False):",'elif response.status_code >= 500:',Routes,'test_fixed_error_codes_do_not_become_generic_500'),
      ('404 domain code preserved',routes,'operator_prefix',"if response.status_code in (404, 405, 422) and not getattr(request.state, 'artifact_error_envelope', False):",'if response.status_code in (404, 405, 422):',Routes,'test_create_202_replay_200_validation_and_detail_errors'),
      ('source UID proof',sources,'capture_artifact_session_source','if not valid:','if False:',Sources,'test_capture_single_read_identity_attribution_and_deep_detachment'),
      ('source caps',sources,'check_packet_bounds','if total > storage.MAX_PACKET_BYTES:','if False:',Sources,'test_cap_precheck_exact_bytes_unicode_escaping_and_count'),
      ('metadata allowlist',sources,'project_artifact_message','if key in PROVENANCE and _primitive(value)','if _primitive(value)',Sources,'test_projection_allowlist_preserves_literal_text_not_server_metadata'),
      ('source full walk seam',sources,'capture_artifact_session_source',"storage._packet_scope('0'*32, packet)",'pass',Sources,'test_capture_single_read_identity_attribution_and_deep_detachment'),
      ('snapshot deep detach',store.MessageStore,'snapshot_selected','return deepcopy([rows[identifier] for identifier in message_ids])','return [dict(rows[identifier]) for identifier in message_ids]',Sources,'test_snapshot_selected_is_detached_and_channel_exact'),
      ('snapshot typed refusal',store.MessageStore,'snapshot_selected',"raise MessageSnapshotUnavailable('Selected messages are unavailable.')","raise ValueError('Selected messages are unavailable.')",Sources,'test_snapshot_missing_and_duplicate_ids_never_return_partial'),
      ('Stop policy wired',queue.CoordinatedQueue,'cancel_run','if not fence_artifacts or self._artifact_policy is None:','if True:',Stop,'test_engine_stop_cancels_mid_run_artifact_and_fences_claim'),
      ('Stop fence effect',queue.CoordinatedQueue,'cancel_run','for start in range(0, len(ids), 100):','for start in range(0):',Stop,'test_engine_stop_cancels_mid_run_artifact_and_fences_claim'),
      ('retained Stop repair',queue.CoordinatedQueue,'_reconcile','self._repair_retained_artifact_stops()','pass',Stop,'test_reconcile_repairs_retained_artifacts_without_review_receipts'),
      ('historical index scans',queue.CoordinatedQueue,'_reconcile',"self._queue.cancel_run(run['run_id'], run['stop_id'])","self.cancel_run(run['run_id'], run['stop_id'], fence_artifacts=True)",Stop,'test_historical_stops_never_scan_artifact_index_per_claim'),
      ('held owner Stop containment',queue.CoordinatedQueue,'cancel_run',"except (ArtifactUnavailable, OSError):","except FileNotFoundError:",Stop,'test_held_artifact_owner_does_not_abort_stop_or_other_sessions'),
      ('retained held owner containment',queue.CoordinatedQueue,'_repair_retained_artifact_stops',"except (ArtifactUnavailable, OSError):","except FileNotFoundError:",Stop,'test_held_owner_allows_ordinary_claim_after_historical_stop'),
      ('Stop reports separate',queue.CoordinatedQueue,'cancel_run',"records = self._queue.cancel_run(run_id, stop_id)","records = self._queue.cancel_run(run_id, stop_id) + [row for row in self._queue.records() if row['envelope'].get('purpose') == 'artifact-v1']",Stop,'test_artifact_fences_are_separate_from_review_stop_outcome'),
      ('retained repair bounded rotation',queue.CoordinatedQueue,'_repair_retained_artifact_stops','ids = ordered[:100]','ids = ids[:100]',Stop,'test_retained_repair_budget_rotates_without_starving_later_requests'),
      ('ASCII content length',routes,'operator_prefix',"not re.fullmatch(r'[0-9]{1,20}', lengths[0])","not lengths[0].isdigit()",Routes,'test_content_length_requires_ascii_decimal_and_head_errors_are_empty'),
      ('HEAD refusal body',routes,'operator_prefix',"if request.method == 'HEAD':","if False:",Routes,'test_content_length_requires_ascii_decimal_and_head_errors_are_empty'),
      ('duplicate query',routes,'create_router',"or any(len(request.query_params.getlist(key)) != 1 for key in request.query_params)",'or False',Routes,'test_duplicate_session_query_fields_refuse_before_listing'),
      ('orphan conflict cause',operator.ArtifactOperator,'_failure',"getattr(error, 'packet_exists', False)",'False',Core,'test_orphan_packet_conflict_has_distinct_recoverable_cause'),
      ('producer drift cause',operator.ArtifactOperator,'_failure',"isinstance(error, (_ArtifactProducerUnavailable, ArtifactAccessError))",'False',Core,'test_producer_drift_and_access_loss_are_author_refusals'),
      ('postrun independent',service.ArtifactService,'fence_source_requests',"('complete', 'stopping', 'stopped', 'unresolved')",'()',Recovery,'test_source_fence_partial_stop_failure_is_explicit_and_later_request_is_independent')]
    paths=[ROOT/name for name in ('artifact_operator.py','artifact_routes.py','artifact_sources.py','store.py','artifact_service.py','queue_coordinator.py','session_engine.py','app.py')]
    hashes=lambda:{str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    before=hashes();report={'kind':'reduced20 in-process mutations, no source edits','source_hashes':before,'checks':[]}
    receipt=ROOT/'.audit-tmp/reduced20-mutations.json';receipt.parent.mkdir(exist_ok=True)
    for label,owner,name,old,new,case,test in checks:
        stream=io.StringIO()
        try:
            with rewrite(owner,name,old,new):result=unittest.TextTestRunner(stream=stream,verbosity=0).run(unittest.TestSuite([case(test)]))
            row={'label':label,'test':test,'killed':not result.wasSuccessful(),'failures':len(result.failures),'errors':len(result.errors),'evidence':'assertion' if result.failures else 'ERROR-only, weaker typed-contract evidence','output':stream.getvalue()}
        except Exception as error:row={'label':label,'killed':False,'harness_error':repr(error)}
        report['checks'].append(row);receipt.write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps({key:value for key,value in row.items() if key!='output'}),flush=True)
    report['source_unchanged']=hashes()==before;report['pass']=report['source_unchanged'] and all(row['killed'] for row in report['checks'])
    receipt.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'receipt':str(receipt),'pass':report['pass']}))
    return 0 if report['pass'] else 1
if __name__=='__main__':raise SystemExit(main())
