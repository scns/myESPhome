"""Validate the catalogue, stage publication artifacts and pin dashboard imports."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def devices(root=ROOT):
    return json.loads((root / 'static/devices.json').read_text(encoding='utf-8'))


def supported(root=ROOT):
    return [d for d in devices(root) if d['status'] == 'supported']


def check(root=ROOT):
    catalogue = devices(root)
    ids = [d['id'] for d in catalogue]
    assert len(ids) == len(set(ids)), 'Duplicate device IDs'
    assert supported(root), 'No publication devices configured'
    assert set(ids) == {p.stem for p in (root / 'esphome').glob('*.yaml')}, 'Catalogue/config mismatch'
    for device in catalogue:
        name = device['id']
        assert re.fullmatch(r'[a-z0-9_]+', name), f'Invalid device ID: {name}'
        assert device['status'] in ('supported', 'experimental', 'concept'), f'Invalid status: {name}'
        config = (root / f'esphome/{name}.yaml').read_text(encoding='utf-8')
        assert f'device_name: "{name}"' in config, f'Incorrect device name: {name}'
        assert f'package_import_url: github://scns/myESPhome/esphome/{name}.yaml' in config, f'Incorrect import: {name}'
        assert 'remote_package:' not in config, f'CI must use checkout packages: {name}'
        for include in re.findall(r'!include\s+(\S+)', config):
            assert (root / 'esphome' / include).is_file(), f'Missing include: {include}'
        implementation = (root / f'esphome/package/{name}.yaml').read_text(encoding='utf-8')
        if device['status'] == 'concept':
            assert 'CONCEPT:' in implementation, f'Missing concept marker: {name}'
        else:
            assert re.search(r'^\w+:', implementation, re.M), f'Empty implementation: {name}'
        update_file = 'ds18b20_update_beta' if name == 'ds18b20_beta' else f'{name}_update'
        update = (root / f'esphome/package/{update_file}.yaml').read_text(encoding='utf-8')
        assert f'https://myesphome.assistantathome.nl/{name}/manifest.json' in update, f'Wrong update source: {name}'
    print('Catalogue, local packages, import paths and update sources checked.')


def validate(root=ROOT):
    def validate_config(path):
        result = subprocess.run([sys.executable, '-m', 'esphome', 'config', str(path)],
                                cwd=root, text=True, capture_output=True)
        if result.returncode:
            error = result.stdout + result.stderr
            secret_path = path.parent / 'secrets.yaml'
            if secret_path.exists():
                import yaml
                for value in yaml.safe_load(secret_path.read_text(encoding='utf-8')).values():
                    error = error.replace(str(value), '[REDACTED]')
            print(error, file=sys.stderr)
            result.check_returncode()
        print(f'Validated {path.relative_to(root)}')
    # config validates local packages without producing firmware binaries.
    for device in devices(root):
        if device['status'] != 'concept':
            validate_config(root / f"esphome/{device['id']}.yaml")
    # Validate the secure adoption path too, using temporary per-device secrets.
    from secure_setup import create
    private = root / 'esphome/private'
    private.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='v-', dir=private) as temporary:
        validation_root = Path(temporary)
        for device in devices(root):
            if device['status'] == 'concept':
                continue
            # Each generated folder must stay directly below private/ so its
            # relative package include resolves to the real checkout.
            name = device['id'].replace('_', '-')
            destination = private / (validation_root.name + '-' + name)
            assert not destination.exists(), 'Refusing to overwrite an existing private configuration'
            try:
                create(device['id'], destination.name, root)
                validate_config(destination / 'device.yaml')
            finally:
                if destination.exists():
                    shutil.rmtree(destination)
    print('All factory and secured supported/experimental configurations are valid.')


def local_binary(folder, path):
    parsed = urlsplit(path)
    assert not parsed.scheme and not parsed.netloc and not parsed.query and not parsed.fragment, f'Non-local binary: {path}'
    target = (folder / path).resolve()
    assert target.is_relative_to(folder.resolve()), f'Binary outside artifact: {path}'
    assert target.is_file() and target.stat().st_size > 0, f'Missing/empty binary: {path}'
    assert target.suffix == '.bin', f'Unexpected binary extension: {path}'
    return target


def verify_checksums(binary, metadata):
    data = binary.read_bytes()
    for algorithm in ('md5', 'sha256'):
        if algorithm in metadata:
            digest = hashlib.new(algorithm, data).hexdigest()
            assert digest == metadata[algorithm].lower(), f'{algorithm} checksum mismatch: {binary.name}'


def validate_manifest(folder, device):
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    assert manifest.get('name') and manifest.get('version'), f'Incomplete manifest: {device["id"]}'
    builds = manifest.get('builds', [])
    assert len(builds) == 1 and builds[0].get('chipFamily') == device['chipFamily'], f'Wrong chip: {device["id"]}'
    parts = builds[0].get('parts', [])
    assert parts, f'No factory firmware: {device["id"]}'
    for part in parts:
        assert isinstance(part.get('offset'), int) and part['offset'] >= 0, 'Invalid flash offset'
        verify_checksums(local_binary(folder, part['path']), part)
    ota = builds[0].get('ota')
    assert ota and re.fullmatch(r'[a-fA-F0-9]{32}', ota.get('md5', '')), 'Missing OTA checksum'
    binary = local_binary(folder, ota['path'])
    verify_checksums(binary, ota)
    return manifest


def assemble(artifacts, output, root=ROOT):
    # Validate the complete set before staging; never publish a partial set.
    validated = []
    for device in supported(root):
        folder = artifacts / f"firmware-{device['id']}"
        validated.append((device, folder, validate_manifest(folder, device)))
    assert not output.exists(), f'Output already exists: {output}'
    shutil.copytree(root / 'static', output)
    for device, folder, manifest in validated:
        name = device['id']
        shutil.copytree(folder, output / name)
        legacy = copy.deepcopy(manifest)
        for build in legacy['builds']:
            for part in build['parts']:
                part['path'] = f"{name}/{part['path']}"
            build['ota']['path'] = f"{name}/{build['ota']['path']}"
        (output / f'{name}-manifest.json').write_text(json.dumps(legacy, indent=2) + '\n', encoding='utf-8')
    print(f'Website staged with {len(validated)} verified firmware artifacts.')


def stage(device, build_directory, output, root=ROOT):
    catalogue = {d['id']: d for d in supported(root)}
    assert device in catalogue, 'Cannot publish a concept/experimental device'
    build_directory = Path(build_directory)
    validate_manifest(build_directory, catalogue[device])
    # Embed the device folder so download-artifact works for one or many devices.
    shutil.copytree(build_directory, Path(output) / f'firmware-{device}')


def pin_import(device, revision, root=ROOT):
    assert device in [d['id'] for d in supported(root)], 'Cannot publish a concept/experimental device'
    assert re.fullmatch(r'[a-f0-9]{40}', revision), 'Use a full commit SHA'
    path = root / f'esphome/{device}.yaml'
    text = path.read_text(encoding='utf-8')
    text, count = re.subn(r'(package_import_url: github://\S+\.yaml)(?:@\S+)?', rf'\1@{revision}', text)
    assert count == 1, 'Expected exactly one dashboard import'
    path.write_text(text, encoding='utf-8')


def settings():
    version = re.search(r'^esphome==(.+)$', (ROOT / 'requirements-dev.txt').read_text(), re.M).group(1)
    print('devices=' + json.dumps([d['id'] for d in supported()]))
    print('version=' + version)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['check', 'validate', 'settings', 'assemble', 'stage', 'pin-import'])
    parser.add_argument('args', nargs='*')
    options = parser.parse_args()
    if options.command == 'assemble':
        assemble(*map(Path, options.args))
    elif options.command == 'pin-import':
        pin_import(*options.args)
    elif options.command == 'stage':
        stage(*options.args)
    else:
        globals()[options.command]()
