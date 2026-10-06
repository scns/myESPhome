# Project maintenance

## Configuration and releases

`static/devices.json` is the shared device catalogue for the website, CI and release
matrix. `supported` devices are published; `experimental` devices are validated
but require personal installation; `concept` devices have no implementation and
are never built or offered for installation.

Main YAML files use local packages, so validation and publication use the exact
checkout. Website builds pin `dashboard_import.package_import_url` to the build's
full commit SHA. When imported by ESPHome, the configuration and its relative
packages are taken from that same revision. The repository is not modified by CI.

`requirements-dev.txt` pins ESPHome. Use the same version in the stable Docker
compose file and the YAML `min_version` values when upgrading. The common firmware
version is `project_version` in `esphome/package/basis_settings.yaml`; bump it for
new releases. Beta settings inherit the common settings.

## Automation

* Every push and pull request runs catalogue checks, regression tests and
  `esphome config` for supported/experimental devices and their secured variants.
  These operations generate no firmware binaries.
* Manual runs of **Validate** also validate beta/dev ESPHome compatibility. Those
  exploratory checks do not block the pinned-version checks.
* Publishing a GitHub release or manually running **Publish website and firmware**
  validates, builds all supported devices, verifies complete manifests and local
  binaries, stages the site and deploys it to GitHub Pages.
* No PR workflow builds or comments on firmware artifacts. A missing firmware,
  wrong chip, invalid path or OTA checksum mismatch prevents website deployment.
  Root `<device>-manifest.json` aliases remain for older installations.

Set repository **Settings > Pages > Source** to **GitHub Actions** and configure
the `github-pages` environment if approvals are desired. A manual publication run
publishes its selected ref; select the intended release commit. Normal pushes do
not update the live website.

## Website preview

The website source is in `static/`. Run a local static server from the repository
root and open `http://localhost:8000`:

```sh
python -m http.server 8000 --directory static
```

The home, parts and contact pages are standalone HTML documents. Project cards,
filters and installer choices all use `static/devices.json`; the JavaScript marks
concepts and experimental configurations separately and never offers them for web
installation. The initial preview has no firmware artifacts, so the install button
remains unavailable until the matching release manifests are served.

Fonts load from Google Fonts with local system-font fallbacks. ESP Web Tools loads
only on the installation page. Bootstrap, jQuery, fetched page fragments and the
previous analytics script are no longer used by the website. All other artwork,
icons and photographs are local. `.nojekyll` keeps the static site independent of
Jekyll when served by GitHub Pages.

## Local checks

With Python 3.12 and Node.js installed:

```sh
python -m pip install -r requirements-dev.txt
python scripts/project.py check
python -m unittest discover -s tests
node --test tests/installer.test.cjs
python scripts/project.py validate
```

Validation never prints generated private keys. Test artifacts contain fixture
bytes and are not real firmware. Actual device behavior and flash capacity still
need hardware testing; publication compiles the real firmware before deployment.

## Garage door commissioning

The garage door configuration is experimental and excluded from web installation.
Create a secured personal configuration first. The relay is D5, the closed
endstop is D3 and the open endstop is D2, with active-low pull-up inputs. D3/GPIO0
is a boot strap pin: verify that the connected endstop circuit permits normal boot
on your board before use. The relay must match the configured active-high output.

The relay starts off and produces a 250 ms pulse. The virtual lock starts enabled
on every boot. Endstops are filtered for 50 ms. A restartable 25 s travel timer is
cancelled at an endstop or an explicit stop, so previous travel cannot create a
late timeout alarm. Contradictory endstops flag a problem and prohibit commands.
The boot state is reconciled after both inputs become available. Between endstops,
the exact position and direction cannot be inferred after a reboot.

Open and close commands require their respective starting endstop. After stopping
halfway, use the physical control to move to a known endstop before issuing another
open/close command. A travel timeout reports a fault; it does not automatically
send a potentially ambiguous toggle pulse. Verify that the door controller's own
obstruction detection and physical stop work independently of this firmware.

Commission on hardware: test both endpoints, reboot at either endpoint and halfway,
stop halfway, contact bounce, contradictory inputs, failure to reach an endstop,
relay behavior during reboot, and physical controller interaction. Adjust the 25 s
timeout to the actual travel time before use.

## Unfinished devices

DS18B20, its beta variant, DHT22, FORNUFTIG, UPPATVIND and KEMO M152 remain concepts.
The repository does not specify their sensor pins, wiring or actuator interfaces.
Add the actual hardware mapping and device component, validate and test it on
hardware, then change its catalogue status. Do not publish a base-only firmware
as a working device.

## IKEA FORNUFTIG

The experimental fan package follows Ed Voncken's D5/D6/D7 wiring modification.
`static/ikea-fornuftig.html` documents the schematic, personal setup and optional
BME680 package. Keep the displayed YAML in this guide in sync with the two source
packages when changing them. CI validates the optional sensor with the secured fan
configuration. The fan is excluded from browser installation and firmware builds
until its wiring and operation have been verified on physical hardware.
