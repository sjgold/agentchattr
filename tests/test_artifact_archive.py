"""Pre-change real writer ZIP golden with controlled input/ZIP metadata only."""
import base64
import asyncio
import io
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

    def test_configured_export_call_passes_real_owner(self):
        import app
        from tests.test_artifact_imported_store import ArtifactImportedStoreTests
        case=ArtifactImportedStoreTests();self.addCleanup(case.doCleanups);case.setUp()
        with patch.object(app,'artifacts',case.source),patch.object(app,'config',{'server':{'version':'fixture'}}), \
                patch('archive.build_export',return_value=b'CONTROLLED_ZIP') as call:
            response=asyncio.run(app.export_history())
        self.assertEqual(response.status_code,200)
        self.assertIs(call.call_args.kwargs.get('artifact_store'),case.source)

    def test_configured_import_call_passes_real_owner(self):
        import app
        from fastapi import UploadFile
        from tests.test_artifact_imported_store import ArtifactImportedStoreTests
        case=ArtifactImportedStoreTests();self.addCleanup(case.doCleanups);case.setUp()
        with patch.object(app,'artifacts',case.target),patch.object(app,'_channels',return_value=case.service), \
                patch.object(app,'room_settings',case.settings),patch.object(app,'ws_clients',set()), \
                patch('archive.import_archive',return_value={'ok':True,'channels':{'created':[]}}) as call:
            response=asyncio.run(app.import_history(UploadFile(filename='fixture.zip',file=io.BytesIO(b'CONTROLLED_ZIP'))))
        self.assertEqual(response.status_code,200)
        self.assertIs(call.call_args.kwargs.get('artifact_store'),case.target)

if __name__=='__main__':unittest.main()
