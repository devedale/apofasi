document.addEventListener('DOMContentLoaded', () => {

    const refreshDebugBtn = document.getElementById('refresh-debug-info');
    const debugOutput = document.getElementById('debug-output').querySelector('code');

    const loadDebugInfo = async () => {
        debugOutput.textContent = 'Loading...';
        try {
            const response = await fetch('/api/debug-info');
            // We don't check response.ok here, because we want to see the raw error text if it's a 500
            const data = await response.json();
            debugOutput.textContent = JSON.stringify(data, null, 2); // Pretty print the JSON
        } catch (error) {
            // This catch block will handle network errors or if the response is not valid JSON
            debugOutput.textContent = `A critical error occurred while trying to fetch debug info. This might be a JSON parsing error, meaning the server returned something other than JSON (like an HTML error page).\n\nError: ${error.message}`;
        }
    };

    if (refreshDebugBtn) {
        refreshDebugBtn.addEventListener('click', loadDebugInfo);
    }

    // Automatically load the debug info when the page loads
    loadDebugInfo();
});
