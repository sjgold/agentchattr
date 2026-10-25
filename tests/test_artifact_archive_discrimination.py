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


if __name__=='__main__':unittest.main()
