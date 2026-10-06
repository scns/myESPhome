const {test} = require('node:test');
const assert = require('node:assert/strict');
const {createSelector} = require('../static/scripts/installer.js');
const luxmeter = {id: 'luxmeter', name: 'Luxmeter', board: 'D1 Mini', status: 'supported', chipFamily: 'ESP8266'};
const bluetooth = {id: 'bluetoothproxy', name: 'Bluetooth', board: 'C3', status: 'supported', chipFamily: 'ESP32-C3'};
const manifest = device => ({name: device.name, version: '1', builds: [{chipFamily: device.chipFamily, parts: [{path: 'factory.bin', offset: 0}]}]});
function ui(fetchManifest) {
    const button = {hidden: true, attrs: {}, setAttribute(k, v) {this.attrs[k] = v;}, removeAttribute(k) {delete this.attrs[k];}};
    const status = {}, board = {};
    return {button, status, board, select: createSelector({button, status, board, fetchManifest})};
}
test('initial selection and changes set the matching manifest', async () => {
    const view = ui(async path => manifest(path.startsWith('luxmeter/') ? luxmeter : bluetooth));
    await view.select(luxmeter);
    assert.equal(view.button.attrs.manifest, 'luxmeter/manifest.json');
    await view.select(bluetooth);
    assert.equal(view.button.attrs.manifest, 'bluetoothproxy/manifest.json');
    assert.equal(view.button.hidden, false);
    assert.equal(view.board.textContent, 'C3');
});
test('slow previous request cannot overwrite a newer selection', async () => {
    let resolveOld;
    const view = ui(path => path.startsWith('luxmeter/') ? new Promise(resolve => {resolveOld = resolve;}) : Promise.resolve(manifest(bluetooth)));
    const old = view.select(luxmeter);
    await view.select(bluetooth);
    resolveOld(manifest(luxmeter));
    await old;
    assert.equal(view.button.attrs.manifest, 'bluetoothproxy/manifest.json');
});
test('missing firmware, wrong chip and concepts never enable installation', async () => {
    const oldError = console.error;
    console.error = () => {};
    try {
        for (const loader of [async () => {throw new Error('404');}, async () => manifest(bluetooth)]) {
            const view = ui(loader);
            await view.select(luxmeter);
            assert.equal(view.button.hidden, true);
            assert.equal(view.button.attrs.manifest, undefined);
        }
        const view = ui(async () => {throw new Error('must not fetch');});
        await view.select({...luxmeter, status: 'concept'});
        assert.equal(view.button.hidden, true);
    } finally { console.error = oldError; }
});
