document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Element Selectors ---
    const statusBanner = document.getElementById('status-banner');
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');
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
    const analysisFileSelect = document.getElementById('analysis-file-select');
    const analysisButtons = document.querySelectorAll('.analysis-btn');
    const analysisResultsDiv = document.getElementById('analysis-results');
    const analysisStatusMessage = document.getElementById('analysis-status-message');
    let downloadLink = document.getElementById('download-link');
    const modelNameInput = document.getElementById('model-name-input');
    const downloadModelBtn = document.getElementById('download-model-btn');
    const downloadedModelsList = document.getElementById('downloaded-models-list');
    const logpptFileUpload = document.getElementById('logppt-file-upload');
    const logpptShots = document.getElementById('logppt-shots');
    const logpptModelSelect = document.getElementById('logppt-model-select');
    const logpptMaxTrainSteps = document.getElementById('logppt-max-train-steps');
    const runLogpptIntegrationBtn = document.getElementById('run-logppt-integration-btn');
    const logpptResults = document.getElementById('logppt-results');
    const logpptEvaluationResults = document.getElementById('logppt-evaluation-results');
    const logpptDownloadParsedLink = document.getElementById('logppt-download-parsed-link');
    const logpptDownloadTemplatesLink = document.getElementById('logppt-download-templates-link');
    const logpptContentConfig = document.getElementById('logppt-content-config');
    const logpptColumnsOrder = document.getElementById('logppt-columns-order');
    const logModal = document.getElementById('log-modal');
    const logOutput = document.getElementById('log-output');
    const closeModalBtn = document.querySelector('.close-button');

    // --- LogPPT 2 elements ---
    const logppt2FileUpload = document.getElementById('logppt2-file-upload');
    const logppt2Shots = document.getElementById('logppt2-shots');
    const logppt2Evaluate = document.getElementById('logppt2-evaluate');
    const runLogppt2Btn = document.getElementById('run-logppt2-btn');
    const logppt2LogOutput = document.getElementById('logppt2-log-output');
    const logppt2Results = document.getElementById('logppt2-results');
    const logppt2EvaluationResults = document.getElementById('logppt2-evaluation-results');
    const logppt2DownloadStructured = document.getElementById('logppt2-download-structured');
    const logppt2DownloadTemplates = document.getElementById('logppt2-download-templates');
    const logppt2DatasetDir = document.getElementById('logppt2-dataset-dir');
    const logppt2SaveDatasetDir = document.getElementById('logppt2-save-dataset-dir');
    const logppt2DatasetSelect = document.getElementById('logppt2-dataset-select');

    let initialConfig = {};
    const debounceTimers = {};

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

    const switchTab = (targetTabId) => {
        tabContents.forEach(content => content.classList.remove('active'));
        tabButtons.forEach(button => button.classList.remove('active'));
        document.getElementById(targetTabId).classList.add('active');
        document.querySelector(`[data-tab='${targetTabId}']`).classList.add('active');
    };

    const loadConfig = async () => {
        try {
            const response = await fetch('/api/config');
            if (!response.ok) throw new Error('Failed to load configuration.');
            const config = await response.json();
            initialConfig = config;
            presidioEnabledCheckbox.checked = config.enabled || false;
            presidioConfidenceInput.value = config.analyzer?.analysis?.confidence_threshold || 0.7;
            presidioLanguageSelect.value = config.analyzer?.language || 'en';
            populateEntitiesTable(config.analyzer?.entities || {});
            populateRegexTable(config.analyzer?.ad_hoc_recognizers || []);
        } catch (error) {
            showStatus(error.message, true);
        }
    };

    const populateEntitiesTable = (entities) => {
        entitiesTableBody.innerHTML = '';
        Object.keys(entities).sort().forEach(name => {
            const entity = entities[name];
            const row = entitiesTableBody.insertRow();
            row.dataset.entityName = name;
            row.dataset.entityRegex = entity.regex;
            row.dataset.entityScore = entity.score;
            const scoreValue = (typeof entity.score === 'number' ? entity.score.toFixed(2) : '0.00');
            row.innerHTML = `
                <td>${name}</td>
                <td><input type="checkbox" data-entity-name="${name}" ${entity.enabled ? 'checked' : ''}></td>
                <td>
                    <select data-entity-name="${name}">
                        <option value="replace" ${entity.strategy === 'replace' ? 'selected' : ''}>Replace</option>
                        <option value="mask" ${entity.strategy === 'mask' ? 'selected' : ''}>Mask</option>
                        <option value="hash" ${entity.strategy === 'hash' ? 'selected' : ''}>Hash</option>
                        <option value="keep" ${entity.strategy === 'keep' ? 'selected' : ''}>Keep</option>
                    </select>
                </td>
                <td><pre class="regex-display">${entity.regex || 'undefined'}</pre></td>
                <td><input type="number" class="score-input" value="${scoreValue}" readonly></td>
                <td><button type="button" class="copy-to-custom-btn" ${!entity.is_regex_based ? 'disabled' : ''}>Copy to Custom</button></td>
            `;
        });
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

    const populateRegexTable = (recognizers) => {
        regexTableBody.innerHTML = '';
        recognizers.forEach((rec) => addRegexRow(rec));
    };

    const buildConfigFromUI = () => {
        const newConfig = JSON.parse(JSON.stringify(initialConfig));
        newConfig.enabled = presidioEnabledCheckbox.checked;
        newConfig.analyzer.language = presidioLanguageSelect.value;
        newConfig.analyzer.analysis.confidence_threshold = parseFloat(presidioConfidenceInput.value);
        const newEntities = {};
        const newStrategies = {};
        entitiesTableBody.querySelectorAll('tr').forEach(row => {
            const name = row.dataset.entityName;
            const enabled = row.querySelector('input[type="checkbox"]').checked;
            const strategy = row.querySelector('select').value;
            newEntities[name] = enabled;
            newStrategies[name] = strategy;
        });
        newConfig.analyzer.entities = newEntities;
        newConfig.anonymizer.strategies = newStrategies;
        newConfig.analyzer.ad_hoc_recognizers = [];
        regexTableBody.querySelectorAll('tr').forEach(row => {
            newConfig.analyzer.ad_hoc_recognizers.push({
                name: row.cells[0].querySelector('input').value,
                regex: row.cells[1].querySelector('input').value,
                score: parseFloat(row.cells[2].querySelector('input').value) || 0.85,
                strategy: row.cells[3].querySelector('select').value
            });
        });
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
            
            // Handle different response formats based on analysis type
            if (analysisType === 'logppt' || analysisType === 'csv_export') {
                // Both LogPPT and CSV Export return both original and anonymized URLs
                if (result.original_download_url && result.anonymized_download_url) {
                    // Ensure a primary download link exists
                    if (!downloadLink) {
                        downloadLink = document.createElement('a');
                        downloadLink.id = 'download-link';
                        downloadLink.target = '_blank';
                        downloadLink.className = 'download-link';
                        analysisResultsDiv.appendChild(downloadLink);
                    }

                    // Update the original report link
                    downloadLink.href = result.original_download_url;
                    downloadLink.textContent = analysisType === 'csv_export' ? 'Download Original CSV' : 'Download Original Report';

                    // Find or create the anonymized report link placed after the original
                    let anonymizedLink = document.getElementById('anonymized-download-link');
                    if (!anonymizedLink) {
                        anonymizedLink = document.createElement('a');
                        anonymizedLink.id = 'anonymized-download-link';
                        anonymizedLink.target = '_blank';
                        anonymizedLink.className = 'download-link';
                        // Insert the new link after the original, then place a separator before it
                        downloadLink.insertAdjacentElement('afterend', anonymizedLink);
                        anonymizedLink.insertAdjacentText('beforebegin', ' | ');
                    }
                    anonymizedLink.href = result.anonymized_download_url;
                    anonymizedLink.textContent = analysisType === 'csv_export' ? 'Download Anonymized CSV' : 'Download Anonymized Report';
                }
            } else {
                // Other analysis types return single download_url
                downloadLink.href = result.download_url;
                downloadLink.textContent = `Download ${result.download_url.split('/').pop()}`;
            }
            
            analysisResultsDiv.style.display = 'block';
            showStatus('Analysis complete!', false);
        } catch (error) {
            showStatus(`Error during analysis: ${error.message}`, true);
        } finally {
            analysisButtons.forEach(b => b.disabled = false);
        }
    };

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
    tabButtons.forEach(button => button.addEventListener('click', () => switchTab(button.dataset.tab)));
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
            addRegexRow({
                name: row.dataset.entityName,
                regex: row.dataset.entityRegex,
                score: parseFloat(row.dataset.entityScore),
                strategy: row.querySelector('select').value
            });
            showStatus(`Copied '${row.dataset.entityName}' to Custom Recognizers.`, false, 4000);
        }
    });
    regexTableBody.addEventListener('click', (e) => {
        if (e.target.classList.contains('delete-regex-btn')) {
            e.target.closest('tr').remove();
            saveConfig();
            updatePreviewFromLine();
        }
    });
    analysisButtons.forEach(button => button.addEventListener('click', () => runAnalysis(button.dataset.analysisType)));
    addRegexBtn.addEventListener('click', () => addRegexRow());

    // Ollama Health Check
    const checkOllamaHealth = async () => {
        const statusElement = document.getElementById('ollama-status');
        const statusText = document.getElementById('status-text');
        const statusIcon = document.getElementById('status-icon');
        
        try {
            const response = await fetch('/api/ollama/health');
            const data = await response.json();
            
            if (data.available) {
                statusElement.className = 'status-indicator healthy';
                statusText.textContent = 'Ollama è online e funzionante';
                statusIcon.textContent = '✅';
            } else {
                statusElement.className = 'status-indicator unhealthy';
                statusText.textContent = 'Ollama non è disponibile';
                statusIcon.textContent = '❌';
            }
        } catch (error) {
            statusElement.className = 'status-indicator error';
            statusText.textContent = 'Errore nella verifica di Ollama';
            statusIcon.textContent = '⚠️';
        }
    };

    // Load Available Models for Download
    const loadAvailableModels = (availableModels) => {
        const gridElement = document.getElementById('available-models-grid');
        if (!gridElement) return;
        
        const modelsHtml = Object.entries(availableModels).map(([name, info]) => `
            <div class="model-card">
                <h4>${name}</h4>
                <p class="model-description">${info.description}</p>
                <p class="model-base">Basato su: ${info.base_model}</p>
                <button class="download-predefined-btn" data-model-name="${name}">
                    Scarica ${name}
                </button>
            </div>
        `).join('');
        
        gridElement.innerHTML = modelsHtml;
        
        // Add event listeners for predefined model downloads
        gridElement.addEventListener('click', (e) => {
            if (e.target.classList.contains('download-predefined-btn')) {
                const modelName = e.target.dataset.modelName;
                downloadPredefinedModel(modelName);
            }
        });
    };

    // Download Predefined Model
    const downloadPredefinedModel = async (modelName) => {
        try {
            const button = document.querySelector(`[data-model-name="${modelName}"]`);
            button.disabled = true;
            button.textContent = 'Scaricando...';
            
            const response = await fetch('/api/models/download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model_name: modelName })
            });
            
            if (!response.ok) throw new Error('Download failed');
            const result = await response.json();
            
            showStatus(`Download di ${modelName} iniziato. Controlla i log per il progresso.`);
            streamLogs(result.task_id);
            loadDownloadedModels();
        } catch (error) {
            showStatus(`Errore nel download di ${modelName}: ${error.message}`, true);
        } finally {
            // Reset button after a delay
            setTimeout(() => {
                const button = document.querySelector(`[data-model-name="${modelName}"]`);
                if (button) {
                    button.disabled = false;
                    button.textContent = `Scarica ${modelName}`;
                }
            }, 3000);
        }
    };

    const loadDownloadedModels = async () => {
        try {
            // Check Ollama health first
            await checkOllamaHealth();
            
            const response = await fetch('/api/models');
            if (!response.ok) throw new Error('Could not load Ollama models.');
            const data = await response.json();
            
            // Load available models for download
            loadAvailableModels(data.available_models || {});
            
            if (data.models.length === 0) {
                // No models installed
                downloadedModelsList.innerHTML = `
                    <tr>
                        <td colspan="5" style="text-align: center; color: #666; padding: 20px;">
                            Nessun modello installato. Scarica un modello dalla sezione sopra per usare LogPPT.
                        </td>
                    </tr>
                `;
                
                logpptModelSelect.innerHTML = `
                    <option value="">-- Nessun modello disponibile --</option>
                    <option value="" disabled>Scarica prima un modello</option>
                `;
            } else {
                // Models available
                const modelOptions = data.models.map(model => `<option value="${model.name}">${model.name}</option>`).join('');

                downloadedModelsList.innerHTML = data.models.map(model => {
                    const modelType = model.is_predefined ? 'Predefinito' : 'Personalizzato';
                    const modifiedDate = model.modified_at ? 
                        new Date(model.modified_at).toLocaleDateString('it-IT') : 'N/A';
                    
                    return `
                        <tr>
                            <td>${model.name}</td>
                            <td>${model.size_mb}</td>
                            <td>${modelType}</td>
                            <td>${modifiedDate}</td>
                            <td><button class="delete-model-btn" data-model-name="${model.name}">Elimina</button></td>
                        </tr>
                    `;
                }).join('');

                logpptModelSelect.innerHTML = `
                    <option value="">-- Seleziona un modello installato --</option>
                    ${modelOptions}
                `;
            }
        } catch (error) {
            showStatus(`Errore nel caricamento dei modelli: ${error.message}`, true);
            // Set default state on error
            downloadedModelsList.innerHTML = `
                <tr>
                    <td colspan="5" style="text-align: center; color: #666; padding: 20px;">
                        Errore nel caricamento dei modelli. Verifica che Ollama sia in esecuzione.
                    </td>
                </tr>
            `;
            logpptModelSelect.innerHTML = `
                <option value="">-- Errore nel caricamento --</option>
            `;
        }
    };

    const deleteModel = async (modelName) => {
        if (!confirm(`Are you sure you want to delete the model '${modelName}'?`)) {
            return;
        }
        showStatus(`Deleting model '${modelName}'...`, false, 0);
        try {
            const response = await fetch(`/api/models/${modelName}`, {
                method: 'DELETE'
            });
            if (!response.ok) throw new Error((await response.json()).error || 'Model deletion failed.');
            const result = await response.json();
            showStatus(result.message || 'Model deleted successfully!');
            loadDownloadedModels();
        } catch (error) {
            showStatus(`Error deleting model: ${error.message}`, true);
        }
    };

    const openLogModal = () => {
        logOutput.textContent = '';
        logModal.style.display = 'block';
    };

    const closeLogModal = () => {
        logModal.style.display = 'none';
    };

    const streamLogs = (taskId) => {
        // Clear previous output and show progress bar
        document.getElementById('log-output').textContent = 'Starting LogPPT pipeline...\n';
        document.getElementById('logppt-progress').style.display = 'block';
        
        // Reset progress
        updateProgress(0, 'Starting pipeline...');
        resetSteps();
        
        const eventSource = new EventSource(`/api/stream-logs/${taskId}`);

        eventSource.onmessage = (event) => {
            if (event.data.startsWith("PIPELINE_COMPLETE::")) {
                const results = JSON.parse(event.data.substring("PIPELINE_COMPLETE::".length));
                document.getElementById('log-output').textContent += "\n\nPipeline complete!\n";
                logpptEvaluationResults.innerHTML = `<pre>${JSON.stringify(results.evaluation, null, 2)}</pre>`;
                logpptDownloadParsedLink.href = results.parsed_log_url;
                logpptDownloadTemplatesLink.href = results.templates_url;
                logpptResults.style.display = 'block';
                
                // Complete progress
                updateProgress(100, 'Pipeline completed successfully!');
                completeAllSteps();
                
                eventSource.close();
            } else if (event.data.startsWith("ERROR::")) {
                const errorMsg = event.data.substring("ERROR::".length);
                document.getElementById('log-output').textContent += `\n\nERROR: ${errorMsg}\n`;
                showStatus(`Error during LogPPT process: ${errorMsg}`, true);
                
                // Show error in progress
                updateProgress(0, `Error: ${errorMsg}`);
                showStepError();
                
                eventSource.close();
            } else {
                document.getElementById('log-output').textContent += event.data + '\n';
                
                // Auto-scroll to bottom
                const container = document.getElementById('log-output-container');
                container.scrollTop = container.scrollHeight;
                
                // Update progress based on log messages
                updateProgressFromLog(event.data);
            }
        };

        eventSource.onerror = () => {
            document.getElementById('log-output').textContent += '\n\nConnection to log stream lost.';
            eventSource.close();
        };
    };

    const streamLogs2 = (taskId) => {
        if (!document.getElementById('logppt2-log-output')) return;
        document.getElementById('logppt2-log-output').textContent = 'Starting LogPPT 2 pipeline...\n';
        const eventSource = new EventSource(`/api/stream-logs/${taskId}`);
        eventSource.onmessage = (event) => {
            if (event.data.startsWith('PIPELINE_COMPLETE::')) {
                const results = JSON.parse(event.data.substring('PIPELINE_COMPLETE::'.length));
                document.getElementById('logppt2-log-output').textContent += "\n\nPipeline complete!\n";
                if (document.getElementById('logppt2-evaluation-results')) {
                    document.getElementById('logppt2-evaluation-results').innerHTML = `<pre>${JSON.stringify(results.evaluation, null, 2)}</pre>`;
                }
                if (document.getElementById('logppt2-download-structured')) {
                    document.getElementById('logppt2-download-structured').href = results.parsed_log_url;
                }
                if (document.getElementById('logppt2-download-templates')) {
                    document.getElementById('logppt2-download-templates').href = results.templates_url;
                }
                if (document.getElementById('logppt2-results')) {
                    document.getElementById('logppt2-results').style.display = 'block';
                }
                eventSource.close();
            } else if (event.data.startsWith('ERROR::')) {
                const errorMsg = event.data.substring('ERROR::'.length);
                document.getElementById('logppt2-log-output').textContent += `\n\nERROR: ${errorMsg}\n`;
                showStatus(`Error during LogPPT 2 process: ${errorMsg}`, true);
                eventSource.close();
            } else {
                document.getElementById('logppt2-log-output').textContent += event.data + '\n';
                const container = document.getElementById('logppt2-log-output-container');
                if (container) container.scrollTop = container.scrollHeight;
            }
        };
        eventSource.onerror = () => {
            document.getElementById('logppt2-log-output').textContent += '\n\nConnection to log stream lost.';
            eventSource.close();
        };
    };

    const runLogppt2 = async () => {
        const file = logppt2FileUpload?.files?.[0];
        const formData = new FormData();
        if (file) {
            formData.append('file', file);
        } else if (logppt2DatasetSelect && logppt2DatasetSelect.value) {
            formData.append('dataset_filename', logppt2DatasetSelect.value);
        } else {
            showStatus('Please choose a dataset from the folder or upload a CSV.', true);
            return;
        }
        formData.append('shots', logppt2Shots?.value || '8,16');
        formData.append('evaluate', logppt2Evaluate?.checked ? 'true' : 'false');
        if (runLogppt2Btn) runLogppt2Btn.disabled = true;
        if (logppt2Results) logppt2Results.style.display = 'none';
        try {
            const response = await fetch('/api/logppt2/run', { method: 'POST', body: formData });
            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.error || 'LogPPT 2 process failed.');
            }
            const result = await response.json();
            streamLogs2(result.task_id);
        } catch (error) {
            showStatus(`Error during LogPPT 2 process: ${error.message}`, true);
        } finally {
            if (runLogppt2Btn) runLogppt2Btn.disabled = false;
        }
    };

    const loadLogppt2Datasets = async () => {
        try {
            const resp = await fetch('/api/logppt2/datasets');
            if (!resp.ok) throw new Error('Failed to load LogPPT 2 datasets.');
            const data = await resp.json();
            if (logppt2DatasetDir) logppt2DatasetDir.value = data.dataset_dir || '';
            if (logppt2DatasetSelect) {
                const opts = (data.files || []).map(f => `<option value="${f}">${f}</option>`).join('');
                logppt2DatasetSelect.innerHTML = `<option value="">-- Select dataset from folder --</option>${opts}`;
            }
        } catch (e) {
            // no-op UI fallback
        }
    };

    const saveLogppt2DatasetDir = async () => {
        const dir = logppt2DatasetDir?.value?.trim();
        if (!dir) { showStatus('Please enter a dataset directory.', true); return; }
        try {
            const resp = await fetch('/api/logppt2/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ dataset_dir: dir })
            });
            if (!resp.ok) throw new Error((await resp.json()).error || 'Failed to save dataset directory.');
            showStatus('Dataset directory saved.');
            loadLogppt2Datasets();
        } catch (e) {
            showStatus(e.message, true);
        }
    };
    
    const updateProgress = (percentage, text) => {
        document.getElementById('progress-fill').style.width = percentage + '%';
        document.getElementById('progress-text').textContent = text;
    };
    
    const resetSteps = () => {
        document.querySelectorAll('.step').forEach(step => {
            step.className = 'step';
        });
    };
    
    const completeAllSteps = () => {
        document.querySelectorAll('.step').forEach(step => {
            step.classList.add('completed');
        });
    };
    
    const showStepError = () => {
        document.querySelectorAll('.step').forEach(step => {
            step.classList.add('error');
        });
    };
    
    const updateProgressFromLog = (logMessage) => {
        // Update progress based on log messages
        if (logMessage.includes('Preprocessing complete')) {
            updateProgress(25, 'Preprocessing completed');
            document.getElementById('step-preprocessing').classList.add('completed');
            document.getElementById('step-sampling').classList.add('active');
        } else if (logMessage.includes('Starting sampling')) {
            updateProgress(30, 'Starting sampling...');
            document.getElementById('step-sampling').classList.add('active');
        } else if (logMessage.includes('Sampling completed successfully')) {
            updateProgress(60, 'Sampling completed');
            document.getElementById('step-sampling').classList.add('completed');
            document.getElementById('step-training').classList.add('active');
        } else if (logMessage.includes('Model training complete')) {
            updateProgress(80, 'Training completed');
            document.getElementById('step-training').classList.add('completed');
            document.getElementById('step-parsing').classList.add('active');
        } else if (logMessage.includes('Log parsing complete')) {
            updateProgress(90, 'Parsing completed');
            document.getElementById('step-parsing').classList.add('completed');
        } else if (logMessage.includes('Starting hierarchical clustering')) {
            updateProgress(35, 'Building clusters...');
        } else if (logMessage.includes('Hierarchical clustering completed')) {
            updateProgress(45, 'Clustering completed');
        } else if (logMessage.includes('Starting 8-shot sampling')) {
            updateProgress(50, 'Processing 8-shot sampling...');
        } else if (logMessage.includes('Starting 16-shot sampling')) {
            updateProgress(55, 'Processing 16-shot sampling...');
        }
    };

    const downloadModel = async () => {
        const modelName = modelNameInput.value.trim();
        if (!modelName) {
            showStatus('Please enter a model name.', true);
            return;
        }

        downloadModelBtn.disabled = true;
        try {
            const response = await fetch('/api/models/download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model_name: modelName })
            });
            if (!response.ok) throw new Error((await response.json()).error || 'Model download failed.');
            const result = await response.json();
            streamLogs(result.task_id);
            modelNameInput.value = '';
            loadDownloadedModels();
        } catch (error) {
            showStatus(`Error downloading model: ${error.message}`, true);
        } finally {
            downloadModelBtn.disabled = false;
        }
    };

    const runLogpptIntegration = async () => {
        const file = logpptFileUpload.files[0];
        if (!file) {
            showStatus('Please select a file to upload.', true);
            return;
        }

        const selectedModel = logpptModelSelect.value;
        if (!selectedModel) {
            showStatus('Please select a model from the dropdown. Download a model from the Model Management tab if none are available.', true);
            return;
        }

        const formData = new FormData();
        formData.append('file', file);
        formData.append('model_name', selectedModel);
        formData.append('shots', logpptShots.value);
        formData.append('max_train_steps', logpptMaxTrainSteps.value);
        formData.append('content_config', logpptContentConfig.value);
        formData.append('columns_order', logpptColumnsOrder.value);

        runLogpptIntegrationBtn.disabled = true;
        logpptResults.style.display = 'none';
        
        // Hide progress bar for new run
        document.getElementById('logppt-progress').style.display = 'none';

        try {
            const response = await fetch('/api/logppt/run', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'LogPPT process failed.');
            }

            const result = await response.json();
            streamLogs(result.task_id);

        } catch (error) {
            showStatus(`Error during LogPPT process: ${error.message}`, true);
            
            // Show helpful suggestions for common errors
            if (error.message.includes('Data size') && error.message.includes('smaller than requested shots')) {
                const suggestions = error.message.match(/Suggested shot sizes: ([^.]*)/);
                if (suggestions) {
                    showStatus(`Try using smaller shot sizes: ${suggestions[1]}`, false, 5000);
                }
            }
        } finally {
            runLogpptIntegrationBtn.disabled = false;
        }
    };

    downloadModelBtn.addEventListener('click', downloadModel);
    runLogpptIntegrationBtn.addEventListener('click', runLogpptIntegration);
    if (runLogppt2Btn) runLogppt2Btn.addEventListener('click', runLogppt2);
    if (logppt2SaveDatasetDir) logppt2SaveDatasetDir.addEventListener('click', saveLogppt2DatasetDir);
    closeModalBtn.addEventListener('click', closeLogModal);
    downloadedModelsList.addEventListener('click', (e) => {
        if (e.target.classList.contains('delete-model-btn')) {
            const modelName = e.target.dataset.modelName;
            deleteModel(modelName);
        }
    });

    // === FINE-TUNING FUNCTIONALITY ===
    
    // Variables for fine-tuning
    let selectedBaseModel = null;
    let selectedTemplate = null;
    let uploadedDataset = null;
    let currentTrainingTask = null;
    
    // Elements for fine-tuning
    const baseModelSelect = document.getElementById('base-model-select');
    const modelInfo = document.getElementById('model-info');
    const templateGrid = document.getElementById('template-grid');
    const templatePreview = document.getElementById('template-preview-content');
    const datasetUploadArea = document.getElementById('dataset-upload-area');
    const datasetFileInput = document.getElementById('dataset-file-input');
    const datasetValidation = document.getElementById('dataset-validation');
    const validationResults = document.getElementById('validation-results');
    const datasetPreview = document.getElementById('dataset-preview');
    const ftModelNameInput = document.getElementById('ft-model-name-input');
    const temperatureInput = document.getElementById('temperature-input');
    const topPInput = document.getElementById('top-p-input');
    const topKInput = document.getElementById('top-k-input');
    const startFineTuningBtn = document.getElementById('start-finetuning-btn');
    const trainingProgress = document.getElementById('training-progress');
    const progressText = document.getElementById('progress-text');
    const trainingStats = document.getElementById('training-stats');
    const elapsedTime = document.getElementById('elapsed-time');
    const trainingStatus = document.getElementById('training-status');
    const fineTuningLogOutput = document.getElementById('finetuning-log-output');
    const testModelSelect = document.getElementById('test-model-select');
    const testPrompt = document.getElementById('test-prompt');
    const testModelBtn = document.getElementById('test-model-btn');
    const testResults = document.getElementById('test-results');
    const testOutput = document.getElementById('test-output');
    const refreshModelsBtn = document.getElementById('refresh-models-btn');
    const exportModelBtn = document.getElementById('export-model-btn');
    const exportStatus = document.getElementById('export-status');

    // Load Base Models
    const loadBaseModels = async () => {
        try {
            const response = await fetch('/api/finetuning/base-models');
            if (!response.ok) throw new Error('Failed to load base models');
            
            const data = await response.json();
            baseModelSelect.innerHTML = '<option value="">-- Seleziona un modello base --</option>';
            
            data.base_models.forEach(model => {
                const option = document.createElement('option');
                option.value = model.name;
                option.textContent = `${model.name} (${model.size_mb}MB)`;
                if (model.needs_download) {
                    option.textContent += ' - Da scaricare';
                }
                baseModelSelect.appendChild(option);
            });
            
            updateStepStatus('step1-status', '✅');
            
        } catch (error) {
            console.error('Error loading base models:', error);
            updateStepStatus('step1-status', '❌');
            logToFineTuning(`❌ Errore nel caricamento modelli base: ${error.message}`);
        }
    };

    // Load Training Templates
    const loadTrainingTemplates = async () => {
        try {
            const response = await fetch('/api/finetuning/templates');
            if (!response.ok) throw new Error('Failed to load templates');
            
            const data = await response.json();
            templateGrid.innerHTML = '';
            
            Object.entries(data.templates).forEach(([key, template]) => {
                const card = document.createElement('div');
                card.className = 'template-card';
                card.dataset.template = key;
                
                card.innerHTML = `
                    <h4>${template.name}</h4>
                    <p>${template.description}</p>
                `;
                
                card.addEventListener('click', () => selectTemplate(key, template));
                templateGrid.appendChild(card);
            });
            
            updateStepStatus('step2-status', '✅');
            
        } catch (error) {
            console.error('Error loading templates:', error);
            updateStepStatus('step2-status', '❌');
            logToFineTuning(`❌ Errore nel caricamento template: ${error.message}`);
        }
    };

    // Select Template
    const selectTemplate = (key, template) => {
        // Remove previous selection
        document.querySelectorAll('.template-card').forEach(card => card.classList.remove('selected'));
        
        // Select current
        document.querySelector(`[data-template="${key}"]`).classList.add('selected');
        selectedTemplate = key;
        
        // Show preview
        const preview = `Sistema: ${template.system_prompt}\n\nTemplate:\n${template.prompt_template}`;
        templatePreview.textContent = preview;
        
        checkReadyToStart();
        logToFineTuning(`✅ Template selezionato: ${template.name}`);
    };

    // Base Model Selection
    baseModelSelect?.addEventListener('change', (e) => {
        selectedBaseModel = e.target.value;
        
        if (selectedBaseModel) {
            const option = e.target.selectedOptions[0];
            modelInfo.innerHTML = `
                <p><strong>Modello selezionato:</strong> ${selectedBaseModel}</p>
                <p><strong>Informazioni:</strong> ${option.textContent}</p>
            `;
            logToFineTuning(`✅ Modello base selezionato: ${selectedBaseModel}`);
        } else {
            modelInfo.innerHTML = '<p>Seleziona un modello base per vedere le informazioni</p>';
        }
        
        checkReadyToStart();
    });

    // Dataset Upload
    datasetUploadArea?.addEventListener('click', () => {
        datasetFileInput?.click();
    });

    datasetUploadArea?.addEventListener('dragover', (e) => {
        e.preventDefault();
        datasetUploadArea.classList.add('dragover');
    });

    datasetUploadArea?.addEventListener('dragleave', () => {
        datasetUploadArea.classList.remove('dragover');
    });

    datasetUploadArea?.addEventListener('drop', (e) => {
        e.preventDefault();
        datasetUploadArea.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleDatasetFile(files[0]);
        }
    });

    datasetFileInput?.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleDatasetFile(e.target.files[0]);
        }
    });

    // Handle Dataset File
    const handleDatasetFile = async (file) => {
        logToFineTuning(`📄 Caricamento dataset: ${file.name}`);
        
        // Detect format
        const format = detectDatasetFormat(file.name);
        
        // Create FormData and upload
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            // First upload the file
            const uploadResponse = await fetch('/api/upload-dataset', {
                method: 'POST',
                body: formData
            });
            
            if (!uploadResponse.ok) {
                // Fallback: use file name for validation (assuming it's in examples folder)
                const filePath = `examples/${file.name}`;
                await validateDataset(filePath, format);
                return;
            }
            
            const uploadData = await uploadResponse.json();
            await validateDataset(uploadData.file_path, format);
            
        } catch (error) {
            logToFineTuning(`❌ Errore nel caricamento dataset: ${error.message}`);
            updateStepStatus('step3-status', '❌');
        }
    };

    // Validate Dataset
    const validateDataset = async (filePath, format) => {
        try {
            logToFineTuning(`🔍 Validazione dataset: ${filePath} (${format})`);
            
            const response = await fetch('/api/finetuning/validate-dataset', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    dataset_path: filePath,
                    format_type: format
                })
            });
            
            if (!response.ok) throw new Error('Validation failed');
            
            const validation = await response.json();
            displayValidationResults(validation);
            
            if (validation.valid) {
                uploadedDataset = { path: filePath, format: format };
                updateStepStatus('step3-status', '✅');
                logToFineTuning(`✅ Dataset valido: ${validation.statistics.total_entries} entries`);
            } else {
                updateStepStatus('step3-status', '❌');
                logToFineTuning(`❌ Dataset non valido: ${validation.errors.join(', ')}`);
            }
            
            checkReadyToStart();
            
        } catch (error) {
            console.error('Validation error:', error);
            updateStepStatus('step3-status', '❌');
            logToFineTuning(`❌ Errore nella validazione: ${error.message}`);
        }
    };

    // Display Validation Results
    const displayValidationResults = (validation) => {
        let html = '';
        
        if (validation.valid) {
            html += '<div class="validation-success">✅ Dataset valido</div>';
        }
        
        if (validation.errors.length > 0) {
            html += '<div class="validation-error">';
            html += '<strong>Errori:</strong><ul>';
            validation.errors.forEach(error => {
                html += `<li>${error}</li>`;
            });
            html += '</ul></div>';
        }
        
        if (validation.warnings.length > 0) {
            html += '<div class="validation-warning">';
            html += '<strong>Avvisi:</strong><ul>';
            validation.warnings.forEach(warning => {
                html += `<li>${warning}</li>`;
            });
            html += '</ul></div>';
        }
        
        if (validation.recommendations.length > 0) {
            html += '<div class="validation-info">';
            html += '<strong>Raccomandazioni:</strong><ul>';
            validation.recommendations.forEach(rec => {
                html += `<li>${rec}</li>`;
            });
            html += '</ul></div>';
        }
        
        // Statistics
        if (validation.statistics) {
            html += '<div class="dataset-stats">';
            html += '<strong>Statistiche:</strong><br>';
            html += `Entries totali: ${validation.statistics.total_entries}<br>`;
            html += `Formato: ${validation.statistics.format}<br>`;
            html += `Dimensione: ${validation.statistics.file_size_mb?.toFixed(2)} MB`;
            html += '</div>';
        }
        
        // Sample entries
        if (validation.sample_entries?.length > 0) {
            html += '<div class="dataset-samples">';
            html += '<strong>Anteprima dati:</strong>';
            html += '<pre>' + JSON.stringify(validation.sample_entries, null, 2) + '</pre>';
            html += '</div>';
        }
        
        validationResults.innerHTML = html;
        datasetValidation.style.display = 'block';
    };

    // Detect Dataset Format
    const detectDatasetFormat = (filename) => {
        const ext = filename.toLowerCase().split('.').pop();
        const formatMap = {
            'json': 'json',
            'csv': 'csv',
            'yaml': 'yaml',
            'yml': 'yaml',
            'txt': 'txt'
        };
        return formatMap[ext] || 'txt';
    };

    // Check if Ready to Start
    const checkReadyToStart = () => {
        const modelName = ftModelNameInput?.value?.trim();
        const ready = selectedBaseModel && selectedTemplate && uploadedDataset && modelName;
        
        if (startFineTuningBtn) {
            startFineTuningBtn.disabled = !ready;
        }
        
        if (ready) {
            updateStepStatus('step4-status', '✅');
            logToFineTuning(`🟢 Pronto per il fine-tuning!`);
        } else {
            updateStepStatus('step4-status', '⏳');
        }
    };

    // Model Name Input
    ftModelNameInput?.addEventListener('input', checkReadyToStart);

    // Start Fine-Tuning
    startFineTuningBtn?.addEventListener('click', async () => {
        if (!selectedBaseModel || !selectedTemplate || !uploadedDataset) {
            showStatus('Completa tutti i passaggi prima di iniziare', true);
            return;
        }
        
        const modelName = ftModelNameInput.value.trim();
        if (!modelName) {
            showStatus('Inserisci un nome per il modello', true);
            return;
        }
        
        try {
            startFineTuningBtn.disabled = true;
            logToFineTuning(`🚀 Avvio fine-tuning: ${modelName}`);
            
            const config = {
                temperature: parseFloat(temperatureInput.value),
                top_p: parseFloat(topPInput.value),
                top_k: parseInt(topKInput.value)
            };
            
            const response = await fetch('/api/finetuning/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    base_model: selectedBaseModel,
                    dataset_path: uploadedDataset.path,
                    model_name: modelName,
                    training_template: selectedTemplate,
                    custom_config: config
                })
            });
            
            if (!response.ok) throw new Error('Failed to start fine-tuning');
            
            const result = await response.json();
            currentTrainingTask = result.task_id;
            
            // Start monitoring
            startTrainingMonitoring();
            logToFineTuning(`✅ Fine-tuning avviato (Task ID: ${result.task_id})`);
            
        } catch (error) {
            console.error('Fine-tuning error:', error);
            showStatus(`Errore nel fine-tuning: ${error.message}`, true);
            logToFineTuning(`❌ Errore: ${error.message}`);
            startFineTuningBtn.disabled = false;
        }
    });

    // Start Training Monitoring
    const startTrainingMonitoring = () => {
        if (!currentTrainingTask) return;
        
        trainingStats.style.display = 'block';
        trainingStatus.textContent = 'Training in corso...';
        
        const startTime = Date.now();
        
        // Update elapsed time
        const timeInterval = setInterval(() => {
            const elapsed = Math.floor((Date.now() - startTime) / 1000);
            const minutes = Math.floor(elapsed / 60);
            const seconds = elapsed % 60;
            elapsedTime.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        }, 1000);
        
        // Stream logs
        streamLogs(currentTrainingTask, (log) => {
            logToFineTuning(log);
            
            // Update progress based on log content
            if (log.includes('completato')) {
                updateTrainingProgress(100, 'Completato');
                clearInterval(timeInterval);
                trainingStatus.textContent = 'Completato';
                startFineTuningBtn.disabled = false;
                refreshFineTunedModels();
            } else if (log.includes('download')) {
                updateTrainingProgress(25, 'Download modello base...');
            } else if (log.includes('creazione')) {
                updateTrainingProgress(75, 'Creazione modello...');
            }
        });
    };

    // Update Training Progress
    const updateTrainingProgress = (percent, text) => {
        trainingProgress.style.width = `${percent}%`;
        progressText.textContent = text;
    };

    // Log to Fine-Tuning Console
    const logToFineTuning = (message) => {
        const timestamp = new Date().toLocaleTimeString();
        const logLine = `[${timestamp}] ${message}\n`;
        fineTuningLogOutput.textContent += logLine;
        fineTuningLogOutput.scrollTop = fineTuningLogOutput.scrollHeight;
    };

    // Update Step Status
    const updateStepStatus = (elementId, status) => {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = status;
        }
    };

    // Refresh All Available Models for Testing
    const refreshFineTunedModels = async () => {
        try {
            // Load both fine-tuned models and all Ollama models
            const [fineTunedResponse, ollamaResponse] = await Promise.all([
                fetch('/api/finetuning/models'),
                fetch('/api/models')
            ]);
            
            // Update test model select
            testModelSelect.innerHTML = '<option value="">Seleziona un modello</option>';
            
            let totalModels = 0;
            
            let fineTunedData = null;
            
            // Add fine-tuned models
            if (fineTunedResponse.ok) {
                fineTunedData = await fineTunedResponse.json();
                fineTunedData.models.forEach(model => {
                    const option = document.createElement('option');
                    option.value = model.name;
                    option.textContent = `${model.name} (Fine-tuned)`;
                    testModelSelect.appendChild(option);
                    totalModels++;
                });
            }
            
            // Add all Ollama models
            if (ollamaResponse.ok) {
                const ollamaData = await ollamaResponse.json();
                ollamaData.models.forEach(model => {
                    const option = document.createElement('option');
                    option.value = model.name;
                    option.textContent = `${model.name} (${model.size})`;
                    testModelSelect.appendChild(option);
                    totalModels++;
                });
            }
            
            // Enable export button if fine-tuned models exist
            if (fineTunedData && fineTunedData.models) {
                exportModelBtn.disabled = fineTunedData.models.length === 0;
            } else {
                exportModelBtn.disabled = true;
            }
            
        } catch (error) {
            console.error('Error loading models for testing:', error);
        }
    };

    // Test Model
    testModelSelect?.addEventListener('change', () => {
        testModelBtn.disabled = !testModelSelect.value || !testPrompt.value.trim();
    });

    testPrompt?.addEventListener('input', () => {
        testModelBtn.disabled = !testModelSelect.value || !testPrompt.value.trim();
    });

    testModelBtn?.addEventListener('click', async () => {
        const modelName = testModelSelect.value;
        const prompt = testPrompt.value.trim();
        
        if (!modelName || !prompt) return;
        
        try {
            testModelBtn.disabled = true;
            testModelBtn.textContent = 'Testando...';
            testOutput.textContent = 'Generando risposta...';
            testResults.style.display = 'block';
            
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 240000); // 4 minuti timeout (più del backend)
            
            const response = await fetch('/api/finetuning/test', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model_name: modelName,
                    test_prompt: prompt
                }),
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            
            const result = await response.json();
            
            if (result.success) {
                // Mostra la risposta generata in modo leggibile
                testOutput.textContent = result.response || 'Nessuna risposta generata';
                testResults.style.display = 'block';
                showStatus(`✅ Test completato per ${modelName}`, false);
            } else {
                testOutput.textContent = `Errore: ${result.error}`;
                showStatus(`Test fallito: ${result.error}`, true);
            }
            
        } catch (error) {
            console.error('Test error:', error);
            showStatus(`Errore nel test: ${error.message}`, true);
        } finally {
            testModelBtn.disabled = false;
            testModelBtn.textContent = 'Testa Modello';
        }
    });

    // Refresh Models Button
    refreshModelsBtn?.addEventListener('click', refreshFineTunedModels);

    // Export Model
    exportModelBtn?.addEventListener('click', async () => {
        const modelName = testModelSelect.value;
        if (!modelName) {
            showStatus('Seleziona un modello da esportare', true);
            return;
        }
        
        try {
            exportModelBtn.disabled = true;
            exportStatus.textContent = 'Esportazione in corso...';
            
            const response = await fetch(`/api/finetuning/export/${modelName}`, {
                method: 'POST'
            });
            
            if (!response.ok) throw new Error('Export failed');
            
            const result = await response.json();
            
            if (result.success) {
                exportStatus.textContent = 'Esportazione completata!';
                exportStatus.className = 'export-status success';
            } else {
                exportStatus.textContent = `Errore: ${result.error}`;
                exportStatus.className = 'export-status error';
            }
            
        } catch (error) {
            console.error('Export error:', error);
            exportStatus.textContent = `Errore: ${error.message}`;
            exportStatus.className = 'export-status error';
        } finally {
            exportModelBtn.disabled = false;
        }
    });

    // Initialize Fine-Tuning Tab
    const initFineTuning = () => {
        logToFineTuning('🚀 Sistema di Fine-Tuning inizializzato');
        logToFineTuning('Caricamento modelli base e template...');
        
        loadBaseModels();
        loadTrainingTemplates();
        refreshFineTunedModels();
    };

    // Initialize when fine-tuning tab is selected
    document.querySelector('[data-tab="finetuning-tab"]')?.addEventListener('click', () => {
        // Initialize only once
        if (!baseModelSelect.dataset.initialized) {
            baseModelSelect.dataset.initialized = 'true';
            initFineTuning();
        }
    });

    // --- Initial Load ---
    loadConfig();
    loadSampleFiles();
    updatePreviewFromLine();
    loadDownloadedModels();
    loadLogppt2Datasets();
});
