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

    const loadDownloadedModels = async () => {
        try {
            const response = await fetch('/api/models');
            if (!response.ok) throw new Error('Could not load downloaded models.');
            const data = await response.json();
            
            if (data.models.length === 0) {
                // No models downloaded
                downloadedModelsList.innerHTML = `
                    <tr>
                        <td colspan="3" style="text-align: center; color: #666; padding: 20px;">
                            No models downloaded yet. Download a model from above to use LogPPT.
                        </td>
                    </tr>
                `;
                
                logpptModelSelect.innerHTML = `
                    <option value="">-- No models available --</option>
                    <option value="" disabled>Please download a model first</option>
                `;
            } else {
                // Models available
                const modelOptions = data.models.map(model => `<option value="${model.name}">${model.name}</option>`).join('');

                downloadedModelsList.innerHTML = data.models.map(model => `
                    <tr>
                        <td>${model.name}</td>
                        <td>${model.size_mb}</td>
                        <td><button class="delete-model-btn" data-model-name="${model.name}">Delete</button></td>
                    </tr>
                `).join('');

                logpptModelSelect.innerHTML = `
                    <option value="">-- Select a downloaded model --</option>
                    ${modelOptions}
                `;
            }
        } catch (error) {
            showStatus(error.message, true);
            // Set default state on error
            downloadedModelsList.innerHTML = `
                <tr>
                    <td colspan="3" style="text-align: center; color: #666; padding: 20px;">
                        Error loading models. Please refresh the page.
                    </td>
                </tr>
            `;
            logpptModelSelect.innerHTML = `
                <option value="">-- Error loading models --</option>
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
    closeModalBtn.addEventListener('click', closeLogModal);
    downloadedModelsList.addEventListener('click', (e) => {
        if (e.target.classList.contains('delete-model-btn')) {
            const modelName = e.target.dataset.modelName;
            deleteModel(modelName);
        }
    });

    // --- Initial Load ---
    loadConfig();
    loadSampleFiles();
    updatePreviewFromLine();
    loadDownloadedModels();
});
