"""Pre-driver legacy discriminator guards; large manifests stay on the old path."""
import io
import json
from pathlib import Path
import unittest
import zipfile

import archive
from tests import test_channel_import as fixture


class ArtifactArchiveDiscriminationTests(unittest.TestCase):
    setUp=fixture.ChannelImportTests.setUp

    @staticmethod
    def large_manifest(schema):
        manifest={'schema_version':schema,'archive_id':'large-manifest-fixture',
                  'created_at':'2026-10-25T00:00:00Z','padding':'x'*65536}
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w',zipfile.ZIP_STORED) as zf:
            zf.writestr('manifest.json',json.dumps(manifest));zf.writestr('messages.jsonl','')
        return buffer.getvalue()

    def run_legacy(self,data):
        return archive.import_archive(data,self.messages,self.jobs,None,self.summaries,
            list(self.settings['channels']),channel_policy=self.service)

    def test_large_manifest_legacy_reports_match_pre_driver_capture_without_writes(self):
        expected=json.loads((Path(__file__).parent/'fixtures'/'artifact_legacy_large_manifest.json').read_text(encoding='utf-8'))
        for schema in (1,2):
            with self.subTest(schema=schema):
                before={p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
                self.assertEqual(self.run_legacy(self.large_manifest(schema)),expected['reports'][str(schema)])
                self.assertEqual({p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*') if p.is_file()},before)

    def test_legacy_schema_comparison_preserves_old_non_strict_primitives(self):
        for schema in (0,-1,1.0,True):
            with self.subTest(schema=schema):
                report=self.run_legacy(self.large_manifest(schema))
                self.assertTrue(report['ok'])
                self.assertEqual(report['archive']['schema_version'],schema)

    @staticmethod
    def small_zip(manifest,*,artifact=False,message=False):
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w',zipfile.ZIP_STORED) as zf:
            zf.writestr('manifest.json',json.dumps(manifest))
            if artifact:zf.writestr('artifacts/index.json','{"version":1,"lineages":[]}')
            zf.writestr('messages.jsonl',json.dumps({'uid':'strict-history','sender':'operator',
                'text':'safe history','channel':'review'})+'\n' if message else '')
        return buffer.getvalue()

    def test_small_valid_schema2_without_artifact_section_accepts_without_owner(self):
        manifest={'schema_version':2,'archive_id':'empty-artifacts','created_at':'2026-10-25T00:00:00Z',
            'product':'agentchattr','app_version':'test','counts':{'messages':1,'jobs':0,'rules':0,'summaries':0},
            'attachments_included':False}
        report=self.run_legacy(self.small_zip(manifest,message=True))
        self.assertTrue(report['ok']);self.assertFalse(report['partial'])
        self.assertEqual(report['sections']['artifacts']['status'],'complete')
        self.assertEqual(report['sections']['artifacts']['created_lineages'],0)
        self.assertEqual(report['sections']['messages']['created'],1)
        self.assertFalse((self.root/'artifacts'/'index.json').exists())

    def test_invalid_small_schema2_and_artifact_bearing_unknown_schema_are_strict(self):
        for schema,artifact in ((2,False),(2,True),(3,True)):
            with self.subTest(schema=schema,artifact=artifact):
                data=self.small_zip({'schema_version':schema,'archive_id':'invalid'},artifact=artifact,message=True)
                before={p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
                report=self.run_legacy(data)
                self.assertFalse(report['ok']);self.assertFalse(report['partial'])
                self.assertEqual(report['sections']['artifacts']['section_error']['code'],'artifact_archive_invalid_section')
                self.assertEqual({p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*') if p.is_file()},before)

    def test_oversized_manifest_with_artifacts_uses_strict_manifest_limit(self):
        data=self.small_zip({'schema_version':2,'padding':'x'*65536},artifact=True,message=True)
        report=self.run_legacy(data)
        self.assertFalse(report['ok']);self.assertFalse(report['partial'])
        self.assertEqual(report['sections']['artifacts']['section_error']['code'],'artifact_archive_limit')
        self.assertEqual(self.messages.get_recent(100),[])

    def test_unknown_schemas_without_artifact_names_keep_exact_legacy_refusal(self):
        for schema in (3,7):
            with self.subTest(schema=schema):
                report=self.run_legacy(self.small_zip({'schema_version':schema},message=True))
                self.assertEqual(report,{'ok':False,'error':
                    'unsupported archive schema_version: '+str(schema)+'. Update agentchattr to import this archive.'})
                self.assertEqual(self.messages.get_recent(100),[])


if __name__=='__main__':unittest.main()
