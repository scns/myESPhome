// Load Navbar
fetch('navbar.html')
    .then(response => response.text())
    .then(data => {
        document.getElementById('navbar').innerHTML = data;
    })
    .catch(error => console.error('Error loading navbar:', error));

// Load Sidebar
fetch('sidebar.html')
    .then(response => response.text())
    .then(data => {
        document.getElementById('sidebar').innerHTML = data;
    })
    .catch(error => console.error('Error loading sidebar:', error));

// Load Footer
fetch('footer.html')
    .then(response => response.text())
    .then(data => {
        document.getElementById('footer').innerHTML = data;
    })
    .catch(error => console.error('Error loading footer:', error));

// Only the installation page has these elements.
const installationButton = document.querySelector('esp-web-install-button');
if (installationButton) {
    const status = document.getElementById('install-status');
    const board = document.getElementById('install-board');
    const choices = document.getElementById('device-choices');
    const getJson = async path => {
        const response = await fetch(path, {cache: 'no-store'});
        if (!response.ok) throw new Error(`Could not load ${path}: ${response.status}`);
        return response.json();
    };
    const select = MyESPHomeInstaller.createSelector({
        button: installationButton, status, board, fetchManifest: getJson
    });
    getJson('devices.json').then(devices => {
        const available = devices.filter(device => device.status === 'supported');
        if (!available.length) throw new Error('No supported devices');
        for (const [index, device] of available.entries()) {
            const label = document.createElement('label');
            label.className = 'device-choice';
            const input = document.createElement('input');
            input.type = 'radio';
            input.name = 'type';
            input.value = device.id;
            input.checked = index === 0;
            input.addEventListener('change', () => select(device));
            label.append(input, document.createTextNode(` ${device.name}`));
            choices.append(label);
        }
        select(available[0]);
    }).catch(error => {
        installationButton.hidden = true;
        status.textContent = 'Unable to load the device list. Please reload the page.';
        console.error(error);
    });
}
