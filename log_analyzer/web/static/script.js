document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Element Selectors ---
    // General
    const statusBanner = document.getElementById('status-banner');
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    // Configuration Tab
    const configForm = document.getElementById('config-form');
    const presidioEnabledCheckbox = document.getElementById('presidio-enabled');
    const presidioConfidenceInput = document.getElementById('presidio-confidence');
    const presidioLanguageSelect = document.getElementById('presidio-language');
    const entitiesTableBody = document.getElementById('entities-table').querySelector('tbody');
    const regexTableBody = document.getElementById('regex-table').querySelector('tbody');
    const addRegexBtn = document.getElementById('add-regex-btn');
    const sampleFileSelect = document.getElementById('sample-file-select');
    const sampleLineNumberInput = document.getElementById('sample-line-number');
    const previewInput = document.getElementById('preview-input').querySelector('code');
    const previewOutput = document.getElementById('preview-output').querySelector('code');

    // Analysis Tab
    const analysisFileSelect = document.getElementById('analysis-file-select');
    const analysisButtons = document.querySelectorAll('.analysis-btn');
    const analysisResultsDiv = document.getElementById('analysis-results');
    const analysisStatusMessage = document.getElementById('analysis-status-message');
    const downloadLink = document.getElementById('download-link');

    // --- State ---
    let initialConfig = {};
    const debounceTimers = {};

    // --- Utility Functions ---
    const showStatus = (message, isError = false, duration = 3000) => {
        statusBanner.textContent = message;
        statusBanner.className = isError ? 'status-banner error' : 'status-banner success';
        statusBanner.style.display = 'block';
        if (duration > 0) {
            setTimeout(() => { statusBanner.style.display = 'none'; }, duration);
        }
    };

    const debounce = (key, func, delay) => {
        clearTimeout(debounceTimers[key]);
        debounceTimers[key] = setTimeout(func, delay);
    };

    // --- Tab Switching Logic ---
    const switchTab = (targetTabId) => {
        tabContents.forEach(content => {
            content.classList.toggle('active', content.id === targetTabId);
        });
        tabButtons.forEach(button => {
            button.classList.toggle('active', button.dataset.tab === targetTabId);
        });
    };

    // --- Configuration Tab Logic ---
    const loadConfig = async () => {
        try {
            const response = await fetch('/api/config');
            if (!response.ok) throw new Error('Failed to load configuration.');
            const config = await response.json();
            initialConfig = config;

            presidioEnabledCheckbox.checked = config.enabled || false;
            presidioConfidenceInput.value = config.analyzer?.analysis?.confidence_threshold || 0.7;
            presidioLanguageSelect.value = config.analyzer?.language || 'en';
            populateEntitiesTable(config.analyzer?.entities || {}, config.anonymizer?.strategies || {});
            populateRegexTable(config.analyzer?.ad_hoc_recognizers || []);
        } catch (error) {
            showStatus(error.message, true);
        }
    };

    const populateEntitiesTable = (entities, strategies) => {
        entitiesTableBody.innerHTML = '';
        Object.keys(entities).sort().forEach(name => {
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

    const populateRegexTable = (recognizers) => {
        // This function will be updated later
        regexTableBody.innerHTML = '';
    };

    const buildConfigFromUI = () => {
        const newConfig = { ...initialConfig };
        newConfig.enabled = presidioEnabledCheckbox.checked;

        if (!newConfig.analyzer) newConfig.analyzer = {};
        newConfig.analyzer.language = presidioLanguageSelect.value;
        if (!newConfig.analyzer.analysis) newConfig.analyzer.analysis = {};
        newConfig.analyzer.analysis.confidence_threshold = parseFloat(presidioConfidenceInput.value);

        const newEntities = {};
        const newStrategies = {};
        entitiesTableBody.querySelectorAll('tr').forEach(row => {
            const name = row.cells[0].textContent;
            const enabled = row.querySelector('input[type="checkbox"]').checked;
            const strategy = row.querySelector('select').value;
            newEntities[name] = enabled;
            newStrategies[name] = strategy;
        });
        newConfig.analyzer.entities = newEntities;

        if (!newConfig.anonymizer) newConfig.anonymizer = {};
        newConfig.anonymizer.strategies = newStrategies;

        const newAdHocRecognizers = [];
        // Logic for reading regex table will be added later
        newConfig.analyzer.ad_hoc_recognizers = newAdHocRecognizers;

        return { presidio: newConfig };
    };

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
            initialConfig = configToSave.presidio;
        } catch (error) {
            showStatus(error.message, true);
        }
    };

    const triggerPreview = async (sampleText) => {
        previewInput.textContent = sampleText;
        if (!sampleText) {
            previewOutput.textContent = '';
            return;
        }
        const uiConfig = buildConfigFromUI();
        try {
            const response = await fetch('/api/preview', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sample_text: sampleText, presidio_config: uiConfig.presidio })
            });
            if (!response.ok) throw new Error((await response.json()).error || 'Preview request failed.');
            const result = await response.json();
            previewOutput.textContent = result.anonymized_text;
        } catch (error) {
            previewOutput.textContent = `Error: ${error.message}`;
        }
    };

    const updatePreviewFromLine = async () => {
        const filepath = sampleFileSelect.value;
        const lineNumber = sampleLineNumberInput.value;
        if (!filepath || lineNumber < 1) {
            previewInput.textContent = 'Please select a file and a valid line number.';
            triggerPreview('');
            return;
        }
        try {
            const response = await fetch(`/api/sample-line?filepath=${encodeURIComponent(filepath)}&line_number=${lineNumber}`);
            if (!response.ok) throw new Error((await response.json()).error || 'Failed to fetch line.');
            const data = await response.json();
            await triggerPreview(data.line_content);
        } catch (error) {
            previewInput.textContent = `Error: ${error.message}`;
            triggerPreview('');
        }
    };

    const addRegexRow = (data = {}) => {
        const row = regexTableBody.insertRow();
        const name = data.name || '';
        const regex = data.regex || '';
        const score = data.score || 0.85;
        const strategy = data.strategy || 'replace';

        row.innerHTML = `
            <td><input type="text" value="${name}" placeholder="Recognizer Name"></td>
            <td><input type="text" value="${regex}" placeholder="Regex Pattern"></td>
            <td><input type="number" value="${score}" step="0.05" min="0" max="1"></td>
            <td>
                <select>
                    <option value="replace" ${strategy === 'replace' ? 'selected' : ''}>Replace</option>
                    <option value="mask" ${strategy === 'mask' ? 'selected' : ''}>Mask</option>
                    <option value="hash" ${strategy === 'hash' ? 'selected' : ''}>Hash</option>
                    <option value="keep" ${strategy === 'keep' ? 'selected' : ''}>Keep</option>
                </select>
            </td>
            <td><button type="button" class="delete-regex-btn">Delete</button></td>
        `;
    };

    // --- Analysis Tab Logic ---
    const runAnalysis = async (analysisType) => {
        const inputFile = analysisFileSelect.value;
        if (!inputFile) {
            showStatus('Please select an input file for analysis.', true);
            return;
        }

        showStatus(`Starting ${analysisType} analysis... This may take a moment.`, false, 0);
        analysisResultsDiv.style.display = 'none';
        analysisButtons.forEach(b => b.disabled = true);

        try {
            const response = await fetch(`/api/analysis/${analysisType}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ input_file: inputFile })
            });

            if (!response.ok) throw new Error((await response.json()).error || 'Analysis failed.');

            const result = await response.json();
            analysisStatusMessage.textContent = `Successfully generated report for ${inputFile}.`;
            downloadLink.href = result.download_url;
            downloadLink.textContent = `Download ${result.download_url.split('/').pop()}`;
            analysisResultsDiv.style.display = 'block';
            showStatus('Analysis complete!', false);

        } catch (error) {
            showStatus(`Error during analysis: ${error.message}`, true);
        } finally {
            analysisButtons.forEach(b => b.disabled = false);
        }
    };

    // --- General Setup ---
    const loadSampleFiles = async () => {
        try {
            const response = await fetch('/api/sample-files');
            if (!response.ok) throw new Error('Could not load sample files.');
            const data = await response.json();
            const options = data.files.map(file => `<option value="${file}">${file}</option>`).join('');
            sampleFileSelect.innerHTML = `<option value="">Select for preview...</option>${options}`;
            analysisFileSelect.innerHTML = `<option value="">Select for analysis...</option>${options}`;
        } catch (error) {
            showStatus(error.message, true);
        }
    };

    // --- Event Listener Registration ---
    tabButtons.forEach(button => {
        button.addEventListener('click', () => switchTab(button.dataset.tab));
    });

    configForm.addEventListener('input', (e) => {
        if (e.target.id === 'sample-file-select' || e.target.id === 'sample-line-number') return;
        debounce('save', saveConfig, 750);
        debounce('preview', updatePreviewFromLine, 750);
    });

    sampleFileSelect.addEventListener('change', updatePreviewFromLine);
    sampleLineNumberInput.addEventListener('input', () => debounce('line_preview', updatePreviewFromLine, 500));

    entitiesTableBody.addEventListener('click', (e) => {
        if (e.target.classList.contains('copy-to-custom-btn')) {
            const row = e.target.closest('tr');
            const entityData = {
                name: row.dataset.entityName,
                regex: row.dataset.entityRegex,
                score: parseFloat(row.dataset.entityScore),
                strategy: row.querySelector('select').value
            };
            addRegexRow(entityData);
            showStatus(`Copied '${entityData.name}' to Custom Recognizers. You can now edit it below.`, false, 4000);
        }
    });

    regexTableBody.addEventListener('click', (e) => {
        if (e.target.classList.contains('delete-regex-btn')) {
            e.target.closest('tr').remove();
            saveConfig();
            updatePreviewFromLine();
        }
    });

    analysisButtons.forEach(button => {
        button.addEventListener('click', () => runAnalysis(button.dataset.analysisType));
    });

    addRegexBtn.addEventListener('click', addRegexRow);

    // --- Debug Tab Logic ---
    const refreshDebugBtn = document.getElementById('refresh-debug-info');
    const debugOutput = document.getElementById('debug-output').querySelector('code');

    const loadDebugInfo = async () => {
        debugOutput.textContent = 'Loading...';
        try {
            const response = await fetch('/api/debug-info');
            if (!response.ok) {
                const errText = await response.text();
                throw new Error(`Failed to load debug info: ${errText}`);
            }
            const data = await response.json();
            debugOutput.textContent = JSON.stringify(data, null, 2); // Pretty print the JSON
        } catch (error) {
            debugOutput.textContent = `Error: ${error.message}`;
        }
    };

    refreshDebugBtn.addEventListener('click', loadDebugInfo);


    // --- Initial Load ---
    loadConfig();
    loadSampleFiles();
    updatePreviewFromLine();
});
