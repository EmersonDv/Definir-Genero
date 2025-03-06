async function updateRequestCount() {
    const response = await fetch('/get_request_count');
    const data = await response.json();
    const requestCountValue = document.getElementById('requestCountValue');
    const requestCount = document.getElementById('requestCount');

    requestCountValue.textContent = data.request_count;

    if (data.request_count >= 1000) {
        requestCount.classList.add('limit-reached');
        document.getElementById('uploadButton').disabled = true;
        document.getElementById('statusMessage').textContent = 'Límite diario alcanzado. Inténtalo de nuevo mañana.';
        document.getElementById('statusMessage').className = 'status-message error';
    } else if (data.request_count >= 900) {
        requestCount.classList.add('near-limit');
    } else {
        requestCount.classList.remove('near-limit', 'limit-reached');
    }
}

async function uploadFile() {
    const fileInput = document.getElementById('excelFile');
    const statusMessage = document.getElementById('statusMessage');
    const uploadedFile = document.getElementById('uploadedFile');
    const loadingSpinner = document.getElementById('loadingSpinner');

    if (fileInput.files.length === 0) {
        statusMessage.textContent = 'Por favor, selecciona un archivo.';
        statusMessage.className = 'status-message error';
        return;
    }

    const file = fileInput.files[0];
    uploadedFile.textContent = `Archivo cargado: ${file.name}`; // Muestra el nombre del archivo

    // Mostrar el spinner
    loadingSpinner.style.display = 'block';
    statusMessage.textContent = 'Procesando datos...';
    statusMessage.className = 'status-message';

    const formData = new FormData();
    formData.append('excelFile', file);

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            // Descargar el archivo directamente
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'processed_file.xlsx';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            statusMessage.textContent = 'Archivo procesado y descargado correctamente.';
            statusMessage.className = 'status-message success';
        } else {
            const result = await response.json();
            statusMessage.textContent = result.error || 'Error al procesar el archivo.';
            statusMessage.className = 'status-message error';
        }
    } catch (error) {
        statusMessage.textContent = 'Error de conexión. Inténtalo de nuevo.';
        statusMessage.className = 'status-message error';
    } finally {
        // Ocultar el spinner
        loadingSpinner.style.display = 'none';
        // Actualizar el contador de solicitudes
        await updateRequestCount();
    }
}

// Actualizar el contador al cargar la página
updateRequestCount();