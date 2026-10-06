/* Shared catalogue drives both the website and publication workflow. */
(function (global) {
  'use strict';

  function validateManifest(manifest, device) {
    if (!manifest.name || !manifest.version || !Array.isArray(manifest.builds)) {
      throw new Error('The firmware manifest is incomplete.');
    }
    const build = manifest.builds.find(item => item.chipFamily === device.chipFamily);
    if (!build || !Array.isArray(build.parts) || !build.parts.length) {
      throw new Error('No firmware is available for this board.');
    }
    for (const part of build.parts) {
      if (typeof part.path !== 'string' || !part.path.endsWith('.bin') ||
          !Number.isInteger(part.offset) || part.offset < 0) {
        throw new Error('The firmware manifest contains an invalid binary.');
      }
    }
    return manifest;
  }

  function createSelector({button, status, board, fetchManifest}) {
    let generation = 0;
    return async function select(device) {
      const current = ++generation;
      button.hidden = true;
      button.removeAttribute('manifest');
      board.textContent = device.board || '';
      if (device.status !== 'supported') {
        status.textContent = 'This project is not available for web installation.';
        return;
      }
      status.textContent = 'Checking firmware availability…';
      const path = `${device.id}/manifest.json`;
      try {
        validateManifest(await fetchManifest(path), device);
        if (current !== generation) return;
        button.setAttribute('manifest', path);
        button.hidden = false;
        status.textContent = `Ready to install ${device.name}. Check that your board matches the model above.`;
      } catch (error) {
        if (current !== generation) return;
        status.textContent = 'Firmware is unavailable. Please try again after the next website release.';
        console.error(error);
      }
    };
  }

  const api = {validateManifest, createSelector};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  global.MyESPHomeInstaller = api;
})(typeof window !== 'undefined' ? window : globalThis);
