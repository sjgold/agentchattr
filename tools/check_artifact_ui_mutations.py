"""Mutate actual UI source in Node vm; never edit production files."""
from pathlib import Path
import hashlib
import json
import sys
import io
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tests.test_artifact_ui import ArtifactUITests


def main():
    paths=['static/artifacts.js','static/sessions.js','static/artifacts.css','static/index.html','tests/test_artifact_ui.py']
    sources={name:(ROOT/name).read_text(encoding='utf-8') for name in paths}
    hashes=lambda:{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in paths}
    before=hashes()
    checks=[
        ('operator auth header','static/artifacts.js',"'X-Session-Token': window.SESSION_TOKEN","'X-Session-Token': ''",'test_completed_session_list_and_more_are_authenticated'),
        ('lazy rotated token','static/artifacts.js',"'X-Session-Token': window.SESSION_TOKEN","'X-Session-Token': 'OPERATOR_ONLY'",'test_unknown_reload_retry_requires_original_instruction_and_lazy_token'),
        ('double submit','static/artifacts.js','s.submitting = true; stopPoll(s);','s.submitting = false; stopPoll(s);','test_double_activation_and_unknown_effect_keep_same_request_id'),
        ('unknown same intent','static/artifacts.js',"if (s.known?.unknown) {",'if (false) {','test_double_activation_and_unknown_effect_keep_same_request_id'),
        ('unknown404 retains id','static/artifacts.js','s.notFound = true; s.error =','s.known = null; s.intent = null; s.notFound = true; s.error =','test_double_activation_and_unknown_effect_keep_same_request_id'),
        ('reentered instruction proof','static/artifacts.js','if (s.known.instruction_sha256 !== instructionHash)', 'if (false)','test_unknown_reload_retry_requires_original_instruction_and_lazy_token'),
        ('twenty second deadline','static/artifacts.js','}, 20000);','}, 200000);','test_deadline_get404_late_save_and_reload_keep_unknown_identity'),
        ('terminal poll stops','static/artifacts.js','s.row && LIVE.has(s.row.state))','s.row)','test_poll_backoff_terminal_and_close_dispose_timers'),
        ('backoff cap','static/artifacts.js','Math.min(30000, 2000 * (2 ** s.failures))','Math.min(60000, 2000 * (2 ** s.failures))','test_poll_backoff_terminal_and_close_dispose_timers'),
        ('close cancels timer','static/artifacts.js','s.closed = true; stopPoll(s);','s.closed = true;','test_poll_backoff_terminal_and_close_dispose_timers'),
        ('cancel warning sticky','static/artifacts.js','if (row.transport_settled === true) s.cancelWarning = null;','s.cancelWarning = null;','test_all_status_texts_and_cancel_warning_survive_manual_refresh'),
        ('literal reader','static/artifacts.js','s.nodes.reader.textContent = value.markdown;','s.nodes.reader.innerHTML = value.markdown;','test_verified_reader_is_literal_and_download_is_exact_blob'),
        ('binary download bytes','static/artifacts.js','return response.blob();',"return new Blob([await response.text()]);",'test_verified_reader_is_literal_and_download_is_exact_blob'),
        ('no body persistence','static/artifacts.js','s.nodes.reader.textContent = value.markdown;',"window.sessionStorage.setItem('artifact-body', value.markdown); s.nodes.reader.textContent = value.markdown;",'test_verified_reader_is_literal_and_download_is_exact_blob'),
        ('download response integrity','static/artifacts.js',"if (!['text/markdown', 'application/octet-stream'].includes(media))",'if (false)','test_download_rejects_proxy_html_without_creating_a_file'),
        ('in-memory draft survives close','static/artifacts.js',"drafts.set(s.channel, s.nodes.instruction.value);",'','test_draft_survives_close_in_memory_without_browser_body_storage'),
        ('channel disposal','static/artifacts.js',"Store.watch('activeChannel', () => close(false));","Store.watch('activeChannel', () => {});",'test_channel_change_and_late_response_do_not_leak_other_channel'),
        ('owner availability','static/artifacts.js',"&& window.ChannelLifecycle?.ownerAvailable('artifacts', s.channel) === true",'','test_archived_held_policy_labels_keyboard_and_latest_only_disclosure'),
        ('Stop warning display','static/sessions.js',"if (artifact?.warning || artifact?.unconfirmed_dispatch_ids?.length)",'if (false)','test_stop_warning_is_literal_and_distinct_from_review_outcome'),
        ('Stop warning render key','static/sessions.js','s.quarantined_events?.length, s.artifact_cancellation]','s.quarantined_events?.length]','test_stop_warning_only_update_invalidates_render_cache')
    ]
    report={'kind':'actual UI source mutated only in Node vm','source_hashes':before,'checks':[]}
    out=ROOT/'.audit-tmp/artifact-ui-mutations.json';out.parent.mkdir(exist_ok=True)
    for label,path,old,new,test in checks:
        if sources[path].count(old)!=1:
            row={'label':label,'killed':False,'harness_error':'anchor count '+str(sources[path].count(old))}
        else:
            stream=io.StringIO()
            with patch.object(ArtifactUITests,'source_overrides',{path:sources[path].replace(old,new,1)}):
                result=unittest.TextTestRunner(stream=stream,verbosity=0).run(unittest.TestSuite([ArtifactUITests(test)]))
            row={'label':label,'test':test,'killed':bool(result.failures) and not result.errors,'failures':len(result.failures),'errors':len(result.errors),'output':stream.getvalue()}
        report['checks'].append(row);out.write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps({k:v for k,v in row.items() if k!='output'}),flush=True)
    report['source_unchanged']=hashes()==before;report['pass']=report['source_unchanged'] and all(row['killed'] for row in report['checks'])
    out.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps({'pass':report['pass'],'receipt':str(out)}))
    return 0 if report['pass'] else 1


if __name__=='__main__':raise SystemExit(main())
