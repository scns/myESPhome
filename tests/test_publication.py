import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import project
import secure_setup


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(project.ROOT / 'static', self.root / 'static')
        shutil.copytree(project.ROOT / 'esphome', self.root / 'esphome', ignore=shutil.ignore_patterns('.esphome', 'private'))
        self.artifacts = self.root / 'artifacts'
        self.output = self.root / 'output'
        for device in project.supported(self.root):
            folder = self.artifacts / f"firmware-{device['id']}"
            folder.mkdir(parents=True)
            (folder / 'factory.bin').write_bytes(b'factory fixture')
            (folder / 'ota.bin').write_bytes(b'ota fixture')
            manifest = {'name': device['id'], 'version': 'fixture', 'builds': [{
                'chipFamily': device['chipFamily'],
                'parts': [{'path': 'factory.bin', 'offset': 0, 'sha256': hashlib.sha256(b'factory fixture').hexdigest()}],
                'ota': {'path': 'ota.bin', 'md5': hashlib.md5(b'ota fixture').hexdigest()},
            }]}
            (folder / 'manifest.json').write_text(json.dumps(manifest))

    def mutate_manifest(self, mutate):
        folder = self.artifacts / 'firmware-luxmeter'
        manifest = json.loads((folder / 'manifest.json').read_text())
        mutate(manifest)
        (folder / 'manifest.json').write_text(json.dumps(manifest))

    def test_complete_publication_and_legacy_paths(self):
        project.assemble(self.artifacts, self.output, self.root)
        for device in project.supported(self.root):
            name = device['id']
            project.validate_manifest(self.output / name, device)
            legacy = json.loads((self.output / f'{name}-manifest.json').read_text())
            self.assertEqual(legacy['builds'][0]['parts'][0]['path'], f'{name}/factory.bin')
            self.assertEqual(legacy['builds'][0]['ota']['path'], f'{name}/ota.bin')
        self.assertFalse((self.output / 'garagedoor').exists())
        self.assertFalse((self.output / 'dth22').exists())

    def test_missing_artifact_does_not_stage_partial_site(self):
        shutil.rmtree(self.artifacts / 'firmware-bluetoothproxy')
        with self.assertRaises(FileNotFoundError):
            project.assemble(self.artifacts, self.output, self.root)
        self.assertFalse(self.output.exists())

    def test_artifact_embeds_device_folder_even_for_single_device(self):
        staged = self.root / 'staged'
        project.stage('luxmeter', self.artifacts / 'firmware-luxmeter', staged, self.root)
        self.assertTrue((staged / 'firmware-luxmeter/manifest.json').is_file())
        project.validate_manifest(staged / 'firmware-luxmeter', project.supported(self.root)[0])

    def test_push_and_pr_workflows_never_build_firmware(self):
        import yaml
        workflow = yaml.load((project.ROOT / '.github/workflows/build.yml').read_text(encoding='utf-8-sig'), Loader=yaml.BaseLoader)
        self.assertEqual(set(workflow['on']), {'release', 'workflow_dispatch'})
        ci = yaml.load((project.ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8-sig'), Loader=yaml.BaseLoader)
        self.assertIn('push', ci['on'])
        self.assertIn('pull_request', ci['on'])
        self.assertNotIn('esphome/build-action', json.dumps(ci))
        self.assertFalse((project.ROOT / '.github/workflows/pr.yml').exists())

    def test_wrong_chip_path_traversal_and_corrupt_binary_fail(self):
        original = (self.artifacts / 'firmware-luxmeter/manifest.json').read_text()
        mutations = [
            lambda m: m['builds'][0].update(chipFamily='ESP32-C3'),
            lambda m: m['builds'][0]['parts'][0].update(path='../outside.bin'),
            lambda m: m['builds'][0]['parts'][0].update(path='https://example.com/firmware.bin'),
            lambda m: m['builds'][0]['ota'].update(md5='0' * 32),
            lambda m: m['builds'][0]['parts'][0].update(sha256='0' * 64),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                (self.artifacts / 'firmware-luxmeter/manifest.json').write_text(original)
                self.mutate_manifest(mutate)
                with self.assertRaises(AssertionError):
                    project.assemble(self.artifacts, self.output, self.root)
                self.assertFalse(self.output.exists())

    def test_catalogue_detects_wrong_update_target(self):
        path = self.root / 'esphome/package/dth22_update.yaml'
        path.write_text(path.read_text().replace('/dth22/', '/kemo_m152/'))
        with self.assertRaisesRegex(AssertionError, 'Wrong update source'):
            project.check(self.root)

    def test_import_is_pinned_and_concepts_cannot_be_published(self):
        revision = 'a' * 40
        project.pin_import('luxmeter', revision, self.root)
        config = (self.root / 'esphome/luxmeter.yaml').read_text()
        self.assertIn(f'luxmeter.yaml@{revision}', config)
        with self.assertRaises(AssertionError):
            project.pin_import('dth22', revision, self.root)

    def test_secure_setup_uses_unique_keys_and_never_overwrites(self):
        first = secure_setup.create('luxmeter', 'sensor-one', self.root)
        second = secure_setup.create('luxmeter', 'sensor-two', self.root)
        import yaml
        first_keys = yaml.safe_load((first / 'secrets.yaml').read_text())
        second_keys = yaml.safe_load((second / 'secrets.yaml').read_text())
        for key in ('api_encryption_key', 'fallback_ap_password'):
            self.assertNotEqual(first_keys[key], second_keys[key])
        with self.assertRaises(FileExistsError):
            secure_setup.create('luxmeter', 'sensor-one', self.root)
        with self.assertRaises(ValueError):
            secure_setup.create('dth22', 'unfinished', self.root)


if __name__ == '__main__':
    unittest.main()
