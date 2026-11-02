"""Mutate actual UI source in Node vm; never edit production files."""
from pathlib import Path
import hashlib
import json
import sys
import io
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / 'src'))
from tests.test_artifact_ui import ArtifactUITests


def main():
    paths=['static/artifacts.js','static/sessions.js','static/artifacts.css','static/index.html','tests/test_artifact_ui.py']
    sources={name:(ROOT / 'src' / name if name.endswith('.py') and '/' not in name else ROOT / name).read_text(encoding='utf-8') for name in paths}
    hashes=lambda:{name:hashlib.sha256((ROOT / 'src' / name if name.endswith('.py') and '/' not in name else ROOT / name).read_bytes()).hexdigest() for name in paths}
    before=hashes()
    checks=[
        ('card source after session switch','static/artifacts.js',"const cardLabel = otherSession ? 'Latest request: ' + requestTitle + ' · ' : '';","const cardLabel = '';",'test_switching_selected_session_labels_card_source_without_changing_saved_request'),
        ('selected session prompt','static/artifacts.js',"s.listBusy ? 'Loading sessions...' : s.selected ? '' : 'Choose a session to write from'","s.listBusy ? 'Loading sessions...' : 'Choose a session to write from'",'test_selected_session_has_no_choose_prompt_but_empty_list_keeps_it'),
        ('operator auth header','static/artifacts.js',"'X-Session-Token': window.SESSION_TOKEN","'X-Session-Token': ''",'test_completed_session_list_and_more_are_authenticated'),
        ('lazy rotated token','static/artifacts.js',"'X-Session-Token': window.SESSION_TOKEN","'X-Session-Token': 'OPERATOR_ONLY'",'test_unknown_reload_retry_requires_original_instruction_and_lazy_token'),
        ('double submit','static/artifacts.js','s.submitting = true; stopPoll(s);','s.submitting = false; stopPoll(s);','test_double_activation_and_unknown_effect_keep_same_request_id'),
        ('unknown same intent','static/artifacts.js',"const identifier = wasUnknown ? s.known.request_id : window.crypto.randomUUID().replace(/-/g, '');","const identifier = window.crypto.randomUUID().replace(/-/g, '');",'test_double_activation_and_unknown_effect_keep_same_request_id'),
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
        ('exact create body keys','static/artifacts.js',"run_id: s.selected.run_id, instruction};","run_id: s.selected.run_id, instruction, format: 'Markdown'};",'test_create_exact_intent_and_fresh_id_for_each_new_submit'),
        ('UUID becomes hex','static/artifacts.js',"window.crypto.randomUUID().replace(/-/g, '')","window.crypto.randomUUID()",'test_create_exact_intent_and_fresh_id_for_each_new_submit'),
        ('fresh id for new submit','static/artifacts.js',"window.crypto.randomUUID().replace(/-/g, '')","'a'.repeat(32)",'test_create_exact_intent_and_fresh_id_for_each_new_submit'),
        ('channel query encoding','static/artifacts.js','encodeURIComponent(s.channel)','s.channel','test_encoding_channel_and_ids_never_becomes_url_navigation'),
        ('status id encoding','static/artifacts.js',"request(s, '/api/artifacts/requests/' + encodeURIComponent(id));","request(s, '/api/artifacts/requests/' + id);",'test_digest_is_request_salted_and_every_path_id_is_encoded'),
        ('read id encoding','static/artifacts.js',"'/api/artifacts/requests/' + encodeURIComponent(id) + '/document'","'/api/artifacts/requests/' + id + '/document'",'test_digest_is_request_salted_and_every_path_id_is_encoded'),
        ('cancel id encoding','static/artifacts.js',"'/api/artifacts/requests/' + encodeURIComponent(id) + '/cancel'","'/api/artifacts/requests/' + id + '/cancel'",'test_digest_is_request_salted_and_every_path_id_is_encoded'),
        ('version id encoding','static/artifacts.js',"'/api/artifacts/versions/' + encodeURIComponent(version)","'/api/artifacts/versions/' + version",'test_digest_is_request_salted_and_every_path_id_is_encoded'),
        ('version id validation','static/artifacts.js','if (!hex(s.row.version_id))','if (false)','test_digest_is_request_salted_and_every_path_id_is_encoded'),
        ('salted retry digest','static/artifacts.js',"digest(identifier + ':' + instruction)",'digest(instruction)','test_digest_is_request_salted_and_every_path_id_is_encoded'),
        ('definitive pre-effect reset','static/artifacts.js','PRE_EFFECT.has(error.data?.code)','false','test_pre_effect_null_durability_refusals_clear_new_unknown_and_prechecks_preserve_text'),
        ('packet exists reset','static/artifacts.js',"error.data?.cause === 'packet_exists'","false",'test_definitive_500_and_packet_exists_reset_but_unknown_500_does_not'),
        ('not recorded reset','static/artifacts.js',"error.data?.durability === 'not_recorded' && error.data?.code",'false','test_definitive_500_and_packet_exists_reset_but_unknown_500_does_not'),
        ('unchanged live region text','static/artifacts.js','if (item.textContent !== value) item.textContent = value;','item.textContent = value;','test_live_regions_only_change_for_changed_text_and_focus_is_not_stolen'),
        ('preserve user focus','static/artifacts.js','active(s) && document.activeElement === openingFocus','active(s)','test_live_regions_only_change_for_changed_text_and_focus_is_not_stolen'),
        ('delayed URL revoke','static/artifacts.js','}, 1000);','}, 0);','test_url_revoke_is_delayed_and_close_cleans_it_up'),
        ('URL revoke on close','static/artifacts.js','s.urls.forEach(url => URL.revokeObjectURL(url));','s.urls.forEach(() => {});','test_url_revoke_is_delayed_and_close_cleans_it_up'),
        ('abort inflight on close','static/artifacts.js','s.requests.forEach(abort => abort());','s.requests.forEach(() => {});','test_close_aborts_inflight_and_hidden_completion_does_not_schedule'),
        ('initial poll interval','static/artifacts.js','Math.min(30000, 2000 * (2 ** s.failures))','Math.min(30000, 4000 * (2 ** s.failures))','test_poll_backoff_terminal_and_close_dispose_timers'),
        ('hidden page scheduling','static/artifacts.js','!document.hidden && !s.nodes.panel.hidden','!s.nodes.panel.hidden','test_close_aborts_inflight_and_hidden_completion_does_not_schedule'),
        ('JSON request media','static/artifacts.js',"'Content-Type': 'application/json'","'Content-Type': 'text/plain'",'test_create_exact_intent_and_fresh_id_for_each_new_submit'),
        ('no store policy','static/artifacts.js',"cache: 'no-store'","cache: 'default'",'test_completed_session_list_and_more_are_authenticated'),
        ('errors literal','static/artifacts.js',"text(n.error, s.error || '');","if (s.error) n.error.innerHTML = s.error;",'test_errors_and_author_labels_are_literal_text'),
        ('author literal','static/artifacts.js','text(n.source, detail);','n.source.innerHTML = detail;','test_errors_and_author_labels_are_literal_text'),
        ('Escape closes','static/artifacts.js',"if (event.key === 'Escape')",'if (false)','test_archived_held_policy_labels_keyboard_and_latest_only_disclosure'),
        ('input label association','static/artifacts.js',"label.htmlFor = 'artifact-session-select'","label.htmlFor = ''",'test_archived_held_policy_labels_keyboard_and_latest_only_disclosure'),
        ('polite status','static/artifacts.js',"status.setAttribute('aria-live', 'polite')","status.setAttribute('aria-live', 'assertive')",'test_archived_held_policy_labels_keyboard_and_latest_only_disclosure'),
        ('rename metadata migration','static/artifacts.js','window.sessionStorage.setItem(key(event.new_name), JSON.stringify(previous));','void 0;','test_deduplicated_pages_rename_delete_and_stale_list'),
        ('abandon confirms before reset','static/artifacts.js','s.statusSerial++; s.readSerial++; stopPoll(s); s.known = null;','s.statusSerial++; s.readSerial++; stopPoll(s);','test_unknown_abandon_and_definitive_refusal_are_explicit'),
        ('abandon literal warning','static/artifacts.js',"const ABANDON = 'The earlier request may still finish and could create a second document.';","const ABANDON = '';",'test_unknown_abandon_and_definitive_refusal_are_explicit'),
        ('cancel single-send','static/artifacts.js','s.cancelling = true; s.statusSerial++;','s.cancelling = false; s.statusSerial++;','test_all_status_texts_and_cancel_warning_survive_manual_refresh') ,
        ('stale list serial (reentry fault)','static/artifacts.js','serial !== s.listSerial','false','test_stale_list_serial_is_independent_of_single_flight'),
        ('stale read serial (reentry fault)','static/artifacts.js','serial !== s.readSerial','false','test_stale_read_serial_is_independent_of_single_flight'),
        ('Refresh disabled during cancel','static/artifacts.js','n.refresh.disabled = !s.known || s.refreshing || s.cancelling;','n.refresh.disabled = !s.known || s.refreshing;','test_cancel_not_found_does_not_claim_a_running_worker_and_refresh_serializes'),
        ('Refresh handler during cancel','static/artifacts.js','if (!active(s) || document.hidden || s.nodes.panel.hidden || !s.known || s.refreshing || s.cancelling) return;','if (!active(s) || document.hidden || s.nodes.panel.hidden || !s.known || s.refreshing) return;','test_cancel_not_found_does_not_claim_a_running_worker_and_refresh_serializes'),
        ('reject blank instruction','static/artifacts.js','!instruction.trim()','!instruction','test_pre_effect_null_durability_refusals_clear_new_unknown_and_prechecks_preserve_text'),
        ('reject instruction controls','static/artifacts.js',r'/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(instruction)','false','test_pre_effect_null_durability_refusals_clear_new_unknown_and_prechecks_preserve_text'),
        ('instruction byte cap','static/artifacts.js','new TextEncoder().encode(instruction).length > 32768','false','test_pre_effect_null_durability_refusals_clear_new_unknown_and_prechecks_preserve_text'),
        ('stale download error','static/artifacts.js',"if (active(s) && s.known?.request_id === id) s.error = errorText(error.data);","if (active(s)) s.error = errorText(error.data);",'test_older_download_error_does_not_replace_new_request_status'),
        ('Stop warning display','static/sessions.js',"if (artifact?.warning || artifact?.unconfirmed_dispatch_ids?.length)",'if (false)','test_stop_warning_is_literal_and_distinct_from_review_outcome'),
        ('Stop warning render key','static/sessions.js','s.quarantined_events?.length, s.artifact_cancellation]','s.quarantined_events?.length]','test_stop_warning_only_update_invalidates_render_cache')
    ]
    for label,operation,test in [
        ('stale status after cancel',"const row = await request(s, '/api/artifacts/requests/' + encodeURIComponent(id));",'test_stale_status_after_cancel_cannot_restore_working'),
        ('stale create identity (reentry fault)',"const value = await request(s, '/api/artifacts/requests', {method: 'POST', body: JSON.stringify(intent)});",'test_stale_create_identity_is_independent_of_single_flight')]:
        begin=sources['static/artifacts.js'].index(operation)
        line=sources['static/artifacts.js'][begin:].splitlines()[1]
        old=operation+'\n'+line
        predicate='s.statusSerial !== serial' if label.startswith('stale status') else 's.known?.request_id !== id'
        checks.append((label,'static/artifacts.js',old,old.replace(predicate,'false'),test))
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
