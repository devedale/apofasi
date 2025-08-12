document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Element Selectors ---
    const form = document.getElementById('config-form');
    const presidioEnabledCheckbox = document.getElementById('presidio-enabled');
    const presidioConfidenceInput = document.getElementById('presidio-confidence');
    const entitiesTableBody = document.getElementById('entities-table').querySelector('tbody');
    const regexTableBody = document.getElementById('regex-table').querySelector('tbody');
    const addRegexBtn = document.getElementById('add-regex-btn');
    const sampleTextInput = document.getElementById('sample-text');
    const previewOutput = document.getElementById('preview-output').querySelector('code');
    const statusBanner = document.getElementById('status-banner');

    let initialConfig = {};
    const debounceTimers = {};

    // --- Utility Functions ---

    /**
     * Shows a status message (e.g., "Saved!", "Error!") that fades out.
     * @param {string} message The message to display.
     * @param {boolean} isError If true, shows a red error banner.
     */
    const showStatus = (message, isError = false) => {
        statusBanner.textContent = message;
        statusBanner.className = isError ? 'status-banner error' : 'status-banner success';
        statusBanner.style.display = 'block';
        setTimeout(() => {
            statusBanner.style.display = 'none';
        }, 3000);
    };

    /**
     * Debounce function to delay execution of a function.
     * Used to prevent firing save/preview on every single keystroke.
     * @param {string} key A unique key for the timer (e.g., 'save', 'preview').
     * @param {function} func The function to execute after the delay.
     * @param {number} delay The delay in milliseconds.
     */
    const debounce = (key, func, delay) => {
        clearTimeout(debounceTimers[key]);
        debounceTimers[key] = setTimeout(func, delay);
    };


    // --- Data Loading and UI Population ---

    /**
     * Fetches the configuration from the server and populates the UI.
     */
    const loadConfig = async () => {
        try {
            const response = await fetch('/api/config');
            if (!response.ok) throw new Error('Failed to load configuration.');

            const config = await response.json();
            initialConfig = config; // Store for later reference

            // Populate Core Settings
            presidioEnabledCheckbox.checked = config.enabled || false;
            presidioConfidenceInput.value = config.analyzer?.analysis?.confidence_threshold || 0.7;

            // Populate Entities Table
            populateEntitiesTable(config.analyzer?.entities || {}, config.anonymizer?.strategies || {});

            // Populate Regex Recognizers Table
            populateRegexTable(config.analyzer?.ad_hoc_recognizers || []);

        } catch (error) {
            showStatus(error.message, true);
        }
    };

    /**
     * Renders the entities table.
     * @param {object} entities - The entities object from the config.
     * @param {object} strategies - The strategies object from the config.
     */
    const populateEntitiesTable = (entities, strategies) => {
        entitiesTableBody.innerHTML = ''; // Clear existing rows
        const allEntityNames = Object.keys(entities);

        allEntityNames.sort().forEach(name => {
            const row = entitiesTableBody.insertRow();
            row.innerHTML = `
                <td>${name}</td>
                <td><input type="checkbox" data-entity-name="${name}" ${entities[name] ? 'checked' : ''}></td>
                <td>
                    <select data-entity-name="${name}">
                        <option value="replace" ${strategies[name] === 'replace' ? 'selected' : ''}>Replace</option>
                        <option value="mask" ${strategies[name] === 'mask' ? 'selected' : ''}>Mask</option>
                        <option value="hash" ${strategies[name] === 'hash' ? 'selected' : ''}>Hash</option>
                        <option value="keep" ${strategies[name] === 'keep' ? 'selected' : ''}>Keep</option>
                    </select>
                </td>
            `;
        });
    };

    /**
     * Renders the custom regex recognizers table.
     * @param {Array} recognizers - The list of ad-hoc recognizers.
     */
    const populateRegexTable = (recognizers) => {
        regexTableBody.innerHTML = ''; // Clear existing rows
        recognizers.forEach((rec, index) => {
            const row = regexTableBody.insertRow();
            row.dataset.index = index;
            row.innerHTML = `
                <td><input type="text" value="${rec.name}" placeholder="Recognizer Name"></td>
                <td><input type="text" value="${rec.regex}" placeholder="Regex Pattern"></td>
                <td><input type="number" value="${rec.score}" step="0.1" min="0" max="1"></td>
                <td><button type="button" class="delete-regex-btn">Delete</button></td>
            `;
        });
    };


    // --- UI Event Handlers and Data Persistence ---

    /**
     * Gathers all settings from the UI and builds a config object.
     * @returns {object} The complete Presidio configuration object.
     */
    const buildConfigFromUI = () => {
        const newConfig = {
            ...initialConfig, // Start with the initial config to preserve fields not in the UI
            enabled: presidioEnabledCheckbox.checked,
            analyzer: {
                ...initialConfig.analyzer, // Preserve other analyzer settings
                analysis: {
                    ...(initialConfig.analyzer?.analysis || {}),
                    confidence_threshold: parseFloat(presidioConfidenceInput.value)
                },
                entities: {},
                ad_hoc_recognizers: []
            },
            anonymizer: {
                ...initialConfig.anonymizer, // Preserve other anonymizer settings
                strategies: {}
            }
        };

        // Gather entities and strategies
        entitiesTableBody.querySelectorAll('tr').forEach(row => {
            const name = row.cells[0].textContent;
            const enabled = row.querySelector('input[type="checkbox"]').checked;
            const strategy = row.querySelector('select').value;
            newConfig.analyzer.entities[name] = enabled;
            newConfig.anonymizer.strategies[name] = strategy;
        });

        // Gather regex recognizers
        regexTableBody.querySelectorAll('tr').forEach(row => {
            newConfig.analyzer.ad_hoc_recognizers.push({
                name: row.cells[0].querySelector('input').value,
                regex: row.cells[1].querySelector('input').value,
                score: parseFloat(row.cells[2].querySelector('input').value) || 0.85
            });
        });

        return { presidio: newConfig };
    };

    /**
     * Saves the current UI configuration to the server.
     */
    const saveConfig = async () => {
        const configToSave = buildConfigFromUI();
        try {
            const response = await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(configToSave)
            });
            if (!response.ok) throw new Error('Failed to save configuration.');
            const result = await response.json();
            showStatus(result.message || 'Configuration saved!');
            // After a successful save, update the initialConfig to match the new state
            initialConfig = configToSave.presidio;
        } catch (error) {
            showStatus(error.message, true);
        }
    };

    /**
     * Triggers a live preview of the anonymization.
     */
    const triggerPreview = async () => {
        const sampleText = sampleTextInput.value;
        if (!sampleText) {
            previewOutput.textContent = '';
            return;
        }

        const recognizers = buildConfigFromUI().presidio.analyzer.ad_hoc_recognizers;

        try {
            const response = await fetch('/api/preview', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    sample_text: sampleText,
                    recognizers: recognizers
                })
            });
            if (!response.ok) {
                 const errData = await response.json();
                 throw new Error(errData.error || 'Preview request failed.');
            }
            const result = await response.json();
            previewOutput.textContent = result.anonymized_text;
        } catch (error) {
            previewOutput.textContent = `Error: ${error.message}`;
        }
    };

    /**
     * Adds a new, empty row to the regex recognizers table.
     */
    const addRegexRow = () => {
        const row = regexTableBody.insertRow();
        row.innerHTML = `
            <td><input type="text" placeholder="Recognizer Name"></td>
            <td><input type="text" placeholder="Regex Pattern"></td>
            <td><input type="number" value="0.85" step="0.05" min="0" max="1"></td>
            <td><button type="button" class="delete-regex-btn">Delete</button></td>
        `;
    };

    // --- Event Listener Registration ---

    // Listen for any change or input on the form to save and update preview
    form.addEventListener('input', (e) => {
        // We debounce to avoid hammering the server on every keystroke/change
        debounce('save', saveConfig, 750);
        debounce('preview', triggerPreview, 750);
    });

    // Specific handler for deleting regex rows
    regexTableBody.addEventListener('click', (e) => {
        if (e.target.classList.contains('delete-regex-btn')) {
            e.target.closest('tr').remove();
            // Trigger a save and preview immediately after deletion
            saveConfig();
            triggerPreview();
        }
    });

    addRegexBtn.addEventListener('click', addRegexRow);

    // --- Initial Load ---
    loadConfig();
});
