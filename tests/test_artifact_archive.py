"""Pre-change real writer ZIP golden with controlled input/ZIP metadata only."""
import base64
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
import uuid
import zipfile
import archive
from artifact_store import ArtifactStore

ROOT=Path(__file__).resolve().parents[1]
GOLDEN=json.loads((ROOT/'tests/fixtures/artifact_legacy_export.json').read_text(encoding='utf-8'))

class ArtifactArchiveTests(unittest.TestCase):
    def export(self,**kwargs):
        history=GOLDEN['history']
        stores=(SimpleNamespace(get_recent=lambda count:deepcopy(history['messages'])),
            SimpleNamespace(list_all=lambda:deepcopy(history['jobs'])),
            SimpleNamespace(list_all=lambda:deepcopy(history['rules'])),
            SimpleNamespace(get_all=lambda:deepcopy(history['summaries'])))
        original=zipfile.ZipInfo.__init__
        def fixed_zip(self,*args,**options):
            original(self,*args,**options)
            self.create_system=GOLDEN['zip_create_system']
        with patch('archive.uuid.uuid4',return_value=uuid.UUID(GOLDEN['fixed_uuid'])), \
                patch('archive.time.strftime',return_value=GOLDEN['fixed_time']), \
                patch('zipfile.time.localtime',return_value=(2020,1,2,3,4,6,3,2,-1)), \
                patch.object(zipfile.ZipInfo,'__init__',fixed_zip):
            return archive.build_export(*stores,app_version=GOLDEN['app_version'],**kwargs)

    def test_legacy_omitted_owner_matches_actual_prechange_zip_bytes(self):
        self.assertEqual(self.export(),base64.b64decode(GOLDEN['zip_base64']))

    def test_empty_artifact_owner_export_matches_prechange_bytes(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.audit-tmp') as directory:
            store=ArtifactStore(directory)
            self.assertEqual(self.export(artifact_store=store),base64.b64decode(GOLDEN['zip_base64']))
            self.assertFalse(store.path.exists())

if __name__=='__main__':unittest.main()
