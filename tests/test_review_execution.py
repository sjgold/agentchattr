from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from agents import AgentTrigger
from registry import RuntimeRegistry
from session_engine import SessionEngine
from session_store import SessionStore
from store import MessageStore


class CoordinatorDesignExecutionTests(unittest.TestCase):
    def test_distinct_designs_execute_their_own_frozen_role_phase_order(self):
        designs = [
            {'id': 'review', 'name': 'Review', 'roles': ['reviewer', 'editor'], 'phases': [
                {'name': 'Read', 'participants': ['reviewer'], 'prompt': 'Inspect.'},
                {'name': 'Decide', 'participants': ['editor'], 'prompt': 'Decide.', 'is_output': True}]},
            {'id': 'debate', 'name': 'Debate', 'roles': ['for', 'against', 'judge'], 'phases': [
                {'name': 'Arguments', 'participants': ['for', 'against'], 'prompt': 'Argue.'},
                {'name': 'Verdict', 'participants': ['judge'], 'prompt': 'Judge.', 'is_output': True}]},
        ]
        for design in designs:
            with self.subTest(design=design['id']), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                sessions = SessionStore(str(root / 'session_runs.json'))
                sessions.save_custom_template(deepcopy(design))
                messages = MessageStore(str(root / 'messages.jsonl'))
                registry = RuntimeRegistry(directory)
                names = ['alpha', 'beta', 'gamma'][:len(design['roles'])]
                registry.seed({name: {} for name in names})
                for name in names:
                    registry.register(name)
                engine = SessionEngine(sessions, messages, AgentTrigger(registry, directory), registry)
                pending = []
                def timer(delay, callback, args):
                    result = Mock()
                    result.start.side_effect = lambda: pending.append((callback, args))
                    return result
                expected = [(phase['name'], role) for phase in design['phases'] for role in phase['participants']]
                observed = []
                with patch('session_engine.threading.Timer', timer):
                    session = engine.start_session(design['id'], 'general', dict(zip(design['roles'], names)),
                                                   'operator', 'Compare the evidence', input_text='Exact original source')
                    sessions._templates[design['id']]['phases'] = []
                    for phase_name, role in expected:
                        current = sessions.get(session['id'])
                        agent = engine._get_expected_agent(current)
                        queue = root / (agent + '_queue.jsonl')
                        entry = json.loads(queue.read_text(encoding='utf-8').splitlines()[-1])
                        brief = sessions.briefs.get(entry['review_brief_id'], registry.get_instance(agent))
                        observed.append((brief['phase']['name'], brief['role']))
                        self.assertEqual(brief['source'], 'Exact original source')
                        messages.add(agent, f'Fake result for {role}', channel='general')
                        callback, args = pending.pop(0)
                        callback(*args)
                self.assertEqual(observed, expected)
                self.assertEqual(sessions.get(session['id'])['state'], 'complete')
