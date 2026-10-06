'use strict';

const icon = name => `<svg class="icon" aria-hidden="true"><use href="./stuff/icons.svg#${name}"></use></svg>`;
const escapeHtml = value => String(value).replace(/[&<>"']/g, char => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[char]));
const projectDetails = {
    luxmeter: {icon: 'sun', tone: 'light', category: 'LIGHT & ENVIRONMENT', label: 'BH1750 / I²C', description: 'Let your home respond to the light. Measure ambient brightness and put your lighting automations in their element.'},
    vindriktning: {icon: 'wind', tone: 'air', category: 'AIR & ENVIRONMENT', label: 'PM1006 / UART', description: 'Give your IKEA air quality sensor a voice. Bring its PM2.5 readings straight into Home Assistant.'},
    bluetoothproxy: {icon: 'bluetooth', tone: 'bluetooth', category: 'CONNECTIVITY', label: 'ESP32-C3 / BLUETOOTH LE', description: 'Bridge the gap. Extend Home Assistant’s Bluetooth coverage and connect devices around your home.'},
    garagedoor: {icon: 'home', tone: 'neutral', category: 'ACCESS & CONTROL', label: 'RELAY / DUAL ENDSTOPS', description: 'An experimental garage door controller with endstop feedback. Personal setup and hardware commissioning are required.'},
    ds18b20: {icon: 'chip', tone: 'neutral', category: 'TEMPERATURE', label: 'DS18B20 / CONCEPT', description: 'A temperature sensor project in planning. The wiring and device implementation are not available yet.'},
    ds18b20_beta: {icon: 'chip', tone: 'neutral', category: 'TEMPERATURE', label: 'DS18B20 / BETA CONCEPT', description: 'A planned test variant of the temperature sensor project. There is no installable firmware yet.'},
    dth22: {icon: 'wind', tone: 'neutral', category: 'TEMPERATURE & HUMIDITY', label: 'DHT22 / CONCEPT', description: 'A temperature and humidity project in planning. Hardware mapping and implementation are still needed.'},
    ikea_fornuftig: {icon: 'wind', tone: 'neutral', category: 'AIR & ENVIRONMENT', label: 'FORNUFTIG / SIX SPEEDS', page: './ikea-fornuftig.html', description: 'Build a connected air purifier with six fan speeds, motor feedback and a filter reminder. Follow the wiring guide and configure your own device.'},
    ikea_uppatvind: {icon: 'wind', tone: 'neutral', category: 'AIR & ENVIRONMENT', label: 'UPPATVIND / CONCEPT', description: 'An IKEA air purifier project in planning. Its control interface and device implementation are still to come.'},
    kemo_m152: {icon: 'chip', tone: 'neutral', category: 'SENSORS', label: 'KEMO M152 / CONCEPT', description: 'A planned KEMO M152 integration. Its hardware mapping and device implementation are not available yet.'}
};

const menuButton = document.querySelector('.menu-toggle');
const navigation = document.getElementById('site-nav');
if (menuButton && navigation) {
    const closeMenu = () => {
        menuButton.setAttribute('aria-expanded', 'false');
        menuButton.setAttribute('aria-label', 'Open navigation');
        navigation.classList.remove('is-open');
    };
    menuButton.addEventListener('click', () => {
        const open = menuButton.getAttribute('aria-expanded') !== 'true';
        menuButton.setAttribute('aria-expanded', String(open));
        menuButton.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
        navigation.classList.toggle('is-open', open);
    });
    navigation.addEventListener('click', event => {
        if (event.target.closest('a')) closeMenu();
    });
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && menuButton.getAttribute('aria-expanded') === 'true') {
            closeMenu();
            menuButton.focus();
        }
    });
    window.matchMedia('(min-width: 801px)').addEventListener('change', closeMenu);
}
document.querySelectorAll('[data-year]').forEach(node => { node.textContent = new Date().getFullYear(); });

const installationButton = document.querySelector('esp-web-install-button');
if (installationButton) {
    const status = document.getElementById('install-status');
    const board = document.getElementById('install-board');
    const choices = document.getElementById('device-choices');
    const grid = document.getElementById('project-grid');
    const getJson = async path => {
        const response = await fetch(path, {cache: 'no-store', signal: AbortSignal.timeout(15000)});
        if (!response.ok) throw new Error(`Could not load ${path}: ${response.status}`);
        return response.json();
    };
    const select = MyESPHomeInstaller.createSelector({
        button: installationButton, status, board, fetchManifest: getJson,
        onStateChange: (state, manifest) => {
            status.dataset.state = state;
            const label = document.querySelector('.panel-number');
            label.textContent = state === 'ready' ? `v${manifest.version}` : 'USB SETUP';
        }
    });
    getJson('devices.json').then(devices => {
        const available = devices.filter(device => device.status === 'supported');
        if (!available.length) throw new Error('No supported devices');
        const byId = new Map(devices.map(device => [device.id, device]));
        const inputs = new Map();
        const choose = device => {
            const input = inputs.get(device.id);
            if (!input) return;
            input.checked = true;
            select(device);
        };
        for (const [index, device] of available.entries()) {
            const label = document.createElement('label');
            label.className = 'device-choice';
            const input = document.createElement('input');
            input.type = 'radio';
            input.name = 'type';
            input.value = device.id;
            input.checked = index === 0;
            input.addEventListener('change', () => choose(device));
            const illustration = document.createElement('span');
            illustration.innerHTML = icon(projectDetails[device.id]?.icon || 'chip');
            label.append(input, illustration, document.createTextNode(device.name));
            choices.append(label);
            inputs.set(device.id, input);
        }
        document.getElementById('supported-count').textContent = available.length;
        const render = filter => {
            const visible = devices.filter(device => filter === 'all' || (filter === 'supported' ? device.status === 'supported' : device.status !== 'supported'));
            document.getElementById('project-count').textContent = `${String(visible.length).padStart(2, '0')} PROJECTS`;
            grid.innerHTML = visible.map(device => {
                const details = projectDetails[device.id] || {icon: 'chip', tone: 'neutral', category: 'PROJECT', label: 'ESPHome', description: 'Explore this device configuration on GitHub.'};
                const ready = device.status === 'supported';
                const badge = ready ? 'Ready to build' : device.status === 'experimental' ? 'Experimental' : 'Concept';
                const source = `https://github.com/scns/myESPhome/blob/main/esphome/${encodeURIComponent(device.id)}.yaml`;
                const ordinal = String(devices.indexOf(device) + 1).padStart(2, '0');
                return `<article class="project-card"><div class="project-art" data-tone="${details.tone}">${icon(details.icon)}<span class="art-number mono">PROJECT / ${ordinal}</span><span class="art-label mono">${details.label}</span></div><div class="project-content"><div class="card-topline"><span class="card-category mono">${details.category}</span><span class="status-badge ${ready ? '' : escapeHtml(device.status)}">${badge}</span></div><h3>${escapeHtml(device.name)}</h3><p>${details.description}</p><div class="card-board">${icon('chip')}<span>${escapeHtml(device.board || 'Hardware mapping in development')}</span></div><div class="card-actions">${ready ? `<button type="button" class="button button-outline" data-install="${escapeHtml(device.id)}">Install project ${icon('arrow')}</button>` : `<a class="button button-outline" href="${details.page || source}">${details.page ? 'Build guide' : 'View'} ${details.page ? '' : device.status === 'experimental' ? 'configuration' : 'concept'} ${icon('external')}</a>`}<a class="text-link" href="${ready ? source : 'https://github.com/scns/myESPhome/blob/main/docs/maintenance.md'}">${ready ? 'YAML' : 'Read notes'} ${icon('external')}</a></div></div></article>`;
            }).join('');
        };
        document.querySelectorAll('[data-filter]').forEach(button => button.addEventListener('click', () => {
            document.querySelectorAll('[data-filter]').forEach(other => {
                const active = other === button;
                other.classList.toggle('active', active);
                other.setAttribute('aria-pressed', String(active));
            });
            render(button.dataset.filter);
        }));
        grid.addEventListener('click', event => {
            const button = event.target.closest('[data-install]');
            if (!button) return;
            const device = byId.get(button.dataset.install);
            if (!device || device.status !== 'supported') return;
            choose(device);
            document.getElementById('install').scrollIntoView({behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'});
            inputs.get(device.id).focus({preventScroll: true});
        });
        render('supported');
        choose(available[0]);
    }).catch(error => {
        installationButton.hidden = true;
        status.textContent = 'The device list could not be loaded. Reload this page or browse the configurations on GitHub.';
        status.dataset.state = 'unavailable';
        grid.replaceChildren();
        const message = document.createElement('p');
        message.className = 'loading-note';
        message.textContent = 'Projects are temporarily unavailable. Please reload the page.';
        grid.append(message);
        document.getElementById('project-count').textContent = 'COLLECTION UNAVAILABLE';
        console.error(error);
    });
}
