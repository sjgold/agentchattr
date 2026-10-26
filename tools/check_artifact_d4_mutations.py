"""In-process D4 mutation checks, real fixtures, no source edits or timings.

Run with project root on PYTHONPATH. A killed mutant has an observed assertion
failure or error; errors are explicitly labeled weaker evidence in the receipt.
"""
from contextlib import ExitStack
import hashlib
import inspect
import io
import json
from pathlib import Path
import sys
import textwrap
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import artifact_service as service
import artifact_store as storage
from tests.test_artifact_diagnostic_phases import ArtifactDiagnosticPhaseTests as Tests


def rewritten(cls,name,old,new):
    source=textwrap.dedent(inspect.getsource(getattr(cls,name)))
    if old not in source:raise AssertionError((name,'mutation anchor absent'))
    source=source.replace(old,new,1)
    namespace=dict(vars(sys.modules[cls.__module__]))
    exec(compile(source,'<D4-in-process-mutant>','exec'),namespace)
    return patch.object(cls,name,namespace[name])


def main():
    S=service.ArtifactService
    checks=[
        ('startup cancel-winner storage containment',S,'recover_startup',"                except (OSError, ValueError, RuntimeError):\n                    held(request, dispatch, 'storage_unavailable')", "                except KeyError:\n                    held(request, dispatch, 'storage_unavailable')",'test_startup_cancel_winner_storage_fault_is_held_per_item'),
        ('startup fresh warning mapping',S,'recover_startup',"mode = current['state'] if current is not None else None", "mode = snapshot['state'] if snapshot is not None else None",'test_startup_storage_mapping_reads_fresh_state_and_falls_back_on_read_failure'),
        ('receipt intent identity',S,'_settle_diagnostic_intent','receipt.intent is not intent','False','test_foreign_receipt_and_second_settlement_are_refused_without_effect'),
        ('receipt token',S,'_settle_diagnostic_intent','receipt.token is not invocation_key','False','test_foreign_receipt_and_second_settlement_are_refused_without_effect'),
        ('authority audit comparison',S,'_verify_diagnostic_guard','guard.audit_bytes):',"_frozen(row['audit'])):",'test_corrupt_guard_proof_pairs_cannot_become_terminal_winner_results'),
        ('record digest pair',S,'_verify_diagnostic_guard','if guard.record_bytes is not None and hashlib.sha256(guard.record_bytes).hexdigest() != guard.record_digest:', 'if False:', 'test_corrupt_guard_proof_pairs_cannot_become_terminal_winner_results'),
        ('queue projection',S,'_verify_diagnostic_guard',"if guard.mode not in ('fulfilled_ack', 'terminal_saved'):",'if False:','test_reservation_resume_queue_changes_and_existing_fence_precedence'),
        ('saved result digest',S,'_verify_diagnostic_guard','_digest(saved) != guard.saved_digest','False','test_saved_proof_ack_and_disposition_changes_refuse_c'),
        ('ACK observation',S,'_verify_diagnostic_guard','(_frozen(ack) if ack is not None else None) != guard.ack','False','test_saved_proof_ack_and_disposition_changes_refuse_c'),
        ('disposition observation',S,'_verify_diagnostic_guard','(_frozen(disposition) if disposition is not None else None) != guard.disposition','False','test_saved_proof_ack_and_disposition_changes_refuse_c'),
        ('C active channel',S,'_verify_diagnostic_guard',"self.channels.require_active(row['channel'])",'pass','test_resume_inactive_at_c_is_409_for_reservation_and_retained_modes'),
        ('pre-B ownership check',S,'_run_diagnostic_operation','    self._assert_independent_boundary()\n    payload = self._persist_diagnostic_intent(intent)','    payload = self._persist_diagnostic_intent(intent)','test_pre_b_guard_rechecks_current_thread_ownership'),
        ('pre-A ownership check',S,'_assert_independent_boundary','if type(owned) is not bool or owned:','if False:','test_diagnostic_driver_refuses_caller_held_boundary'),
        ('B failure must not fabricate receipt',S,'_run_diagnostic_operation','payload = self._persist_diagnostic_intent(intent)',"try:\n        payload = self._persist_diagnostic_intent(intent)\n    except ArtifactUnavailable:\n        payload = _frozen({'id': 'f'*32})",'test_b_failure_has_no_c_effect_or_fabricated_receipt_per_entry'),
        ('summary receipt id',S,'_settle_diagnostic_intent',"diagnostic.get('id') or diagnostic['latest_diagnostic_id']","diagnostic.get('latest_diagnostic_id') or diagnostic['id']",'test_overflow_summary_id_is_the_receipt_id'),
        ('pre-C guard',S,'_settle_diagnostic_intent','if not unchanged:','if False:','test_second_writer_during_diagnostic_io_refuses_stale_settlement'),
        ('origin capture',S,'_capture_diagnostic','_DiagnosticContinuation(kind, origin, error_text)',"_DiagnosticContinuation(kind, 'agent', error_text)",'test_continuation_origins_and_all_guard_proofs_are_captured'),
    ]
    paths=[ROOT/name for name in ('artifact_service.py','artifact_store.py','mcp_bridge.py')]
    before={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    report={'kind':'D4 in-process mutation proof, no product edits, not a timing gate','mutations':[],'source_sha256':before}
    out=ROOT/'.audit-tmp/d4-mutation-receipt.json'
    for label,cls,name,old,new,test in checks:
        stream=io.StringIO()
        try:
            with rewritten(cls,name,old,new):result=unittest.TextTestRunner(stream=stream,verbosity=0).run(unittest.TestSuite([Tests(test)]))
            row={'label':label,'test':test,'killed':not result.wasSuccessful(),'failures':len(result.failures),'errors':len(result.errors),'evidence':'assertion' if result.failures else 'ERROR-based, weaker','output':stream.getvalue()}
        except Exception as error:
            row={'label':label,'test':test,'killed':False,'harness_error':repr(error)}
        report['mutations'].append(row);out.write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps({k:v for k,v in row.items() if k!='output'}),flush=True)
    after={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    report['source_unchanged']=after==before
    report['pass']=report['source_unchanged'] and all(row['killed'] for row in report['mutations'])
    out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'receipt':str(out),'pass':report['pass']}),flush=True)
    return 0 if report['pass'] else 1


if __name__=='__main__':raise SystemExit(main())
