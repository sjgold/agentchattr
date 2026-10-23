"""Managed replacement profile clones; readiness seams are explicitly nonnative."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time
import unittest
from unittest.mock import patch
import uuid

from api_seats import SeatError, atomic_json
from api_seat_runtime import SeatManager
from runtime_ownership import new_launch_identity, record_spawn_outcome
from tests import test_restart_launch as fixture


class PrepareReplacementContextTests(unittest.TestCase):
    def setUp(self):
        fixture.RestartLaunchTests.setUp(self)
        self.source, self.source_launch=self.ready('api')
        self.provenance=self.manager.launch_provenance(self.source)
        self.binding={'child_run_id':uuid.uuid4().hex,'role':'reviewer'}
        self.context_key='replacement-'+uuid.uuid4().hex
        seam=patch.object(self.manager,'restart_readiness',return_value={'state':'ready','process_verified':True})
        self.readiness=seam.start()
        self.addCleanup(seam.stop)

    def ready(self, seat_id):
        return fixture.RestartLaunchTests.ready(self,seat_id)

    def prepare(self, **kwargs):
        return self.manager.prepare_replacement_context(self.provenance,self.context_key,
            binding=self.binding,**kwargs)

    def context(self, view):
        return next(value for value in self.manager.attempts.values() if value['id']==view['launch_attempt'])

    def register_ready(self, view):
        attempt=self.context(view)
        owner=self.registry.register(attempt['base'])
        atomic_json(attempt['receipt'],{'attempt':attempt['id'],'state':'ready','name':owner['name'],
            'identity_id':owner['identity_id'],'adapter_connected':True,'authentication':'unknown',
            'confirmed_model':None,'updated_at':time.time()})
        return owner

    def cli_source(self, *, verified=False, fixed_settings=False):
        if verified:
            self.store.providers['fake-cli'].update(cli_fresh_context_args=['--context-id','{context_id}'],
                                                    cli_fresh_context_verified=True)
        if fixed_settings:
            self.store.providers['fake-cli'].update(mcp_inject='settings_file',
                mcp_settings_path=str(self.root/'fixed-client-settings.json'))
        self.source,self.source_launch=self.ready('cli')
        self.provenance=self.manager.launch_provenance(self.source)

    def no_spawn_or_source_control(self, callback):
        calls=self.spawn.call_count
        try:
            result=callback()
        except SeatError:
            result=None
        else:
            self.assertIn(result['state'],('blocked','failed','action_required'))
        self.assertEqual(self.spawn.call_count,calls)
        for process in self.processes:
            process.terminate.assert_not_called()
            process.wait.assert_not_called()
        return result

    def test_api_clone_is_distinct_and_leaves_profile_source_running_and_unchanged(self):
        source=self.manager.attempts['team/api']
        files={path:path.read_bytes() for path in source['snapshot'].parent.iterdir() if path.is_file()}
        process=source['process']
        with patch.object(self.manager,'prepare_retry_context',side_effect=AssertionError('must not retry source')), \
             patch.object(self.manager,'terminate_owned',side_effect=AssertionError('must not terminate source')):
            clone=self.prepare()
        self.assertEqual(clone['state'],'starting')
        self.assertNotEqual(clone['launch_attempt'],self.source_launch['attempt'])
        self.assertEqual(len(self.processes),2)
        self.assertIs(self.manager.attempts['team/api']['process'],process)
        self.assertIsNone(process.poll())
        process.terminate.assert_not_called()
        process.wait.assert_not_called()
        self.assertEqual(files,{path:path.read_bytes() for path in source['snapshot'].parent.iterdir() if path.is_file()})
        self.assertEqual(self.prepare()['launch_attempt'],clone['launch_attempt'])
        self.assertEqual(len(self.processes),2)

    def test_invalid_binding_or_context_key_is_rejected_before_spawn_and_source_control(self):
        for binding in (None,{},dict(self.binding,extra='injected'),{'child_run_id':True,'role':'reviewer'},
                        {'child_run_id':uuid.uuid4().hex,'role':''}):
            with self.subTest(binding=binding),self.assertRaises(SeatError):
                self.manager.prepare_replacement_context(self.provenance,self.context_key,binding=binding)
        for key in ('',True,'../escape','a'*129):
            with self.subTest(key=key),self.assertRaises(SeatError):
                self.manager.prepare_replacement_context(self.provenance,key,binding=self.binding)
        self.assertEqual(len(self.processes),1)
        self.processes[0].terminate.assert_not_called()
        self.processes[0].wait.assert_not_called()

    def test_saved_provider_template_and_package_drift_cannot_change_frozen_api_clone(self):
        frozen=deepcopy(self.manager.attempts['team/api']['effective'])
        self.package['seats'][0]['model']='SAVED_EDIT_MUST_NOT_LAUNCH'
        self.store.save(self.package)
        self.store.providers['fake-api'].update(base_url='http://127.0.0.1:29999/wrong',
                                                system_prompt='WRONG_SAVED_SYSTEM')
        inspect=self.manager._inspect
        def no_source_inspect(key):
            self.assertNotEqual(key,'team/api','cloning must not inspect/release the profile source')
            return inspect(key)
        with patch.object(self.manager,'_inspect',side_effect=no_source_inspect):
            view=self.prepare()
        attempt=self.context(view)
        for field in ('seat','provider','server','mcp'):
            self.assertEqual(attempt['effective'][field],frozen[field])
        snapshot=json.loads(attempt['snapshot'].read_text('utf-8'))
        self.assertEqual(snapshot['replacement_source'],{key:self.provenance[key]
            for key in ('key','launch_attempt','identity_id','fingerprint')})
        self.assertEqual(snapshot['child_run_id'],self.binding['child_run_id'])
        self.assertEqual(snapshot['role'],self.binding['role'])

    def test_forged_recomputed_profile_and_changed_disk_ownership_or_server_refs_deny(self):
        for field,value in (('model','INJECTED_MODEL'),('provider','unknown-provider')):
            forged=deepcopy(self.provenance)
            forged['effective']['seat'][field]=value
            forged['fingerprint']=hashlib.sha256(json.dumps(forged['effective'],sort_keys=True).encode()).hexdigest()
            with self.subTest(field=field),self.assertRaises(SeatError):
                self.manager.prepare_replacement_context(forged,self.context_key,binding=self.binding)
        source=self.manager.attempts['team/api']
        disk=source['snapshot'].read_bytes()
        snapshot=json.loads(disk)
        snapshot['ownership']['launch_nonce']=uuid.uuid4().hex
        atomic_json(source['snapshot'],snapshot)
        changed=source['snapshot'].read_bytes()
        with self.assertRaises(SeatError):self.prepare()
        self.assertEqual(source['snapshot'].read_bytes(),changed)
        source['snapshot'].write_bytes(disk)
        port=self.manager.config['server']['port']
        self.manager.config['server']['port']=port+1
        with self.assertRaises(SeatError):self.prepare()
        self.manager.config['server']['port']=port
        self.assertEqual(len(self.processes),1)

    def test_source_and_clone_have_separate_current_boot_verified_readiness(self):
        for proof in ({'state':'ready','process_verified':False},
                      {'state':'unverified','process_verified':False},
                      {'state':'disconnected','process_verified':True}):
            self.readiness.return_value=proof
            self.no_spawn_or_source_control(self.prepare)
        self.readiness.return_value={'state':'ready','process_verified':True}
        starting=self.prepare()
        self.assertFalse(starting['clean_context'])
        clone_owner=self.register_ready(starting)
        def source_only(identity,boot,**kwargs):
            self.assertEqual(boot,self.manager.boot_id)
            return {'state':'ready','process_verified':True} if identity==self.source['identity_id'] else {
                'state':'unverified','process_verified':False}
        self.readiness.side_effect=source_only
        not_proven=self.prepare()
        self.assertFalse(not_proven['clean_context'])
        self.assertNotEqual(not_proven['state'],'ready')
        self.readiness.side_effect=None
        self.readiness.return_value={'state':'ready','process_verified':True}
        ready=self.prepare()
        self.assertEqual(ready['state'],'ready')
        self.assertTrue(ready['clean_context'])
        self.assertEqual(ready['identity_id'],clone_owner['identity_id'])
        self.assertNotEqual(ready['identity_id'],self.source['identity_id'])
        self.assertEqual(len(self.processes),2)

    def test_stable_context_key_conflicts_on_binding_or_source_change_instead_of_adding_worker(self):
        original=self.prepare()
        for binding in (dict(self.binding,role='editor'),dict(self.binding,child_run_id=uuid.uuid4().hex)):
            with self.subTest(binding=binding),self.assertRaises(SeatError):
                self.manager.prepare_replacement_context(self.provenance,self.context_key,binding=binding)
        cli,_=self.ready('cli')
        other=self.manager.launch_provenance(cli)
        before=self.spawn.call_count
        with self.assertRaises(SeatError):
            self.manager.prepare_replacement_context(other,self.context_key,binding=self.binding)
        self.assertEqual(self.spawn.call_count,before)
        self.assertEqual(self.prepare()['launch_attempt'],original['launch_attempt'])

    def test_pending_manifest_and_exact_scope_exist_before_popen_spawned_only_after_return(self):
        spawn=self.spawn.side_effect
        observations=[]
        def observe(argv,**kwargs):
            config=Path(argv[argv.index('--seat-file')+1])
            snapshot=json.loads(config.read_text('utf-8'))
            manifest=json.loads(config.with_name('launch.json').read_text('utf-8'))
            self.assertEqual(manifest['spawn_outcome'],'pending')
            self.assertEqual(snapshot['child_run_id'],self.binding['child_run_id'])
            self.assertEqual(snapshot['role'],self.binding['role'])
            self.assertEqual(snapshot['context_key'],self.context_key)
            self.assertEqual(snapshot['replacement_source']['identity_id'],self.source['identity_id'])
            observations.append(config)
            return spawn(argv,**kwargs)
        self.spawn.side_effect=observe
        prepared=self.prepare()
        self.assertEqual(len(observations),1)
        config=observations[0]
        manifest=json.loads(config.with_name('launch.json').read_text('utf-8'))
        self.assertEqual(manifest['spawn_outcome'],'spawned')
        self.assertEqual(manifest['attempt'],prepared['launch_attempt'])
        self.assertNotIn('credential-value-test-only',json.dumps(manifest))
        self.assertNotIn(self.source['token'],json.dumps(manifest))

    def test_pre_spawn_snapshot_write_fault_leaves_source_and_process_count_unchanged(self):
        source=self.manager.attempts['team/api']
        before={path:path.read_bytes() for path in source['snapshot'].parent.iterdir() if path.is_file()}
        with patch('api_seat_runtime.atomic_json',side_effect=OSError('Injected clone snapshot failure')):
            try:
                result=self.prepare()
            except (SeatError,OSError):
                pass
            else:
                self.assertIn(result['state'],('failed','blocked','action_required'))
                self.assertFalse(result['clean_context'])
        self.assertEqual(len(self.processes),1)
        self.assertEqual(before,{path:path.read_bytes() for path in source['snapshot'].parent.iterdir() if path.is_file()})
        self.processes[0].terminate.assert_not_called()
        self.processes[0].wait.assert_not_called()

    def test_sync_failed_clone_warm_and_cold_replay_never_respawns_and_ambiguous_history_denies(self):
        spawn=self.spawn.side_effect
        self.spawn.side_effect=OSError('Fixture synchronous Popen failure')
        failed=self.prepare()
        self.assertIn(failed['state'],('failed','action_required','blocked'))
        self.spawn.side_effect=spawn
        calls=self.spawn.call_count
        self.assertEqual(self.prepare()['launch_attempt'],failed['launch_attempt'])
        cold=SeatManager(fixture.ROOT,self.manager.config,self.store,self.registry,monitor=False)
        self.addCleanup(cold.shutdown)
        replay=cold.prepare_replacement_context(self.provenance,self.context_key,binding=self.binding)
        self.assertEqual(replay['launch_attempt'],failed['launch_attempt'])
        self.assertEqual(self.spawn.call_count,calls)
        attempt=self.context(failed)
        snapshot=json.loads(attempt['snapshot'].read_text('utf-8'))
        duplicate=deepcopy(snapshot)
        duplicate['attempt']=uuid.uuid4().hex
        prefix='api-' + hashlib.sha256(failed['key'].encode()).hexdigest()[:8]+'-'
        duplicate['base']=prefix+duplicate['attempt'][:12]
        duplicate['ownership']=new_launch_identity(fixture.ROOT,attempt['effective'],failed['key'],duplicate['attempt'],self.manager.boot_id)
        target=self.root/'api_seat_runtime'/duplicate['attempt']/'config.json'
        atomic_json(target,duplicate)
        record_spawn_outcome(target,duplicate,'pending')
        ambiguous=SeatManager(fixture.ROOT,self.manager.config,self.store,self.registry,monitor=False)
        self.addCleanup(ambiguous.shutdown)
        with self.assertRaises(SeatError):
            ambiguous.prepare_replacement_context(self.provenance,self.context_key,binding=self.binding)
        self.assertEqual(self.spawn.call_count,calls)
        # A separate valid spawned intent with no native birth remains unknown
        # on cold replay; missing RAM never authorizes another Popen.
        pending_key='pending-'+uuid.uuid4().hex
        pending=self.manager.prepare_replacement_context(self.provenance,pending_key,binding=self.binding)
        self.assertEqual(pending['state'],'starting')
        pending_cold=SeatManager(fixture.ROOT,self.manager.config,self.store,self.registry,monitor=False)
        self.addCleanup(pending_cold.shutdown)
        calls=self.spawn.call_count
        try:
            unknown=pending_cold.prepare_replacement_context(self.provenance,pending_key,binding=self.binding)
        except SeatError:
            pass
        else:
            self.assertIn(unknown['state'],('blocked','starting','failed','action_required'))
            self.assertFalse(unknown['clean_context'])
            self.assertEqual(unknown['launch_attempt'],pending['launch_attempt'])
        self.assertEqual(self.spawn.call_count,calls)

    def test_generic_cli_without_verified_fresh_contract_never_clones_or_controls_source(self):
        self.cli_source()
        before=self.spawn.call_count
        result=self.no_spawn_or_source_control(self.prepare)
        if result is not None:self.assertIn('unsupported_clean_context',json.dumps(result))
        self.assertEqual(self.spawn.call_count,before)

    def test_verified_cli_uses_one_fresh_selector_and_cloning_fresh_source_does_not_accumulate_it(self):
        self.cli_source(verified=True)
        source=self.manager.attempts['team/cli']
        original_process=source['process']
        first=self.prepare()
        clone=self.context(first)
        args=clone['effective']['provider']['cli_args']
        self.assertEqual(args,['fixture-original','--context-id',first['context_id']])
        self.assertNotEqual(first['launch_attempt'],self.source_launch['attempt'])
        owner=self.register_ready(first)
        ready=self.prepare()
        self.assertTrue(ready['clean_context'])
        provenance=self.manager.launch_provenance(owner)
        second=self.manager.prepare_replacement_context(provenance,'another-'+uuid.uuid4().hex,binding=self.binding)
        second_args=self.context(second)['effective']['provider']['cli_args']
        self.assertEqual(second_args,['fixture-original','--context-id',second['context_id']])
        self.assertNotEqual(second['context_id'],first['context_id'])
        self.assertEqual(second_args.count('--context-id'),1)
        original_process.terminate.assert_not_called()
        original_process.wait.assert_not_called()
        self.assertIsNone(original_process.poll())

    def test_active_fixed_cli_settings_resource_blocks_clone_before_spawn_without_source_mutation(self):
        self.cli_source(verified=True,fixed_settings=True)
        source=self.manager.attempts['team/cli']
        before={path:path.read_bytes() for path in source['snapshot'].parent.iterdir() if path.is_file()}
        self.no_spawn_or_source_control(self.prepare)
        self.assertEqual(before,{path:path.read_bytes() for path in source['snapshot'].parent.iterdir() if path.is_file()})
