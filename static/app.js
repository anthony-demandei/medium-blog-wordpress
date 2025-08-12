// Medium to WordPress Sync - Frontend JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Auto-refresh dashboard every 30 seconds
    if (window.location.pathname === '/') {
        setInterval(refreshDashboard, 30000);
    }
    
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Handle settings form submission
    const settingsForm = document.getElementById('settingsForm');
    if (settingsForm) {
        settingsForm.addEventListener('submit', handleSettingsSubmit);
    }
});

// Refresh dashboard data
function refreshDashboard() {
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            updateDashboardStats(data);
        })
        .catch(error => console.error('Error refreshing dashboard:', error));
}

// Update dashboard statistics
function updateDashboardStats(data) {
    // Update stats cards
    const statsElements = {
        'total-articles': data.stats.total_articles,
        'total-syncs': data.stats.total_syncs,
        'next-sync': data.next_sync
    };
    
    for (const [id, value] of Object.entries(statsElements)) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    }
}

// Handle settings form submission
function handleSettingsSubmit(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const settings = parseFormData(formData);
    
    // Show loading state
    const submitButton = event.target.querySelector('button[type="submit"]');
    const originalText = submitButton.innerHTML;
    submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Salvando...';
    submitButton.disabled = true;
    
    // Send settings to server
    fetch('/settings/save', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(settings)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Configurações salvas com sucesso!', 'success');
            setTimeout(() => window.location.reload(), 1500);
        } else {
            showAlert('Erro ao salvar configurações: ' + data.error, 'danger');
        }
    })
    .catch(error => {
        showAlert('Erro ao salvar configurações', 'danger');
        console.error('Error:', error);
    })
    .finally(() => {
        submitButton.innerHTML = originalText;
        submitButton.disabled = false;
    });
}

// Parse form data into structured object
function parseFormData(formData) {
    const settings = {
        medium_api: {
            rapidapi_key: formData.get('rapidapi_key'),
            rapidapi_host: formData.get('rapidapi_host')
        },
        wordpress: {
            url: formData.get('wordpress_url'),
            username: formData.get('wordpress_username'),
            password: formData.get('wordpress_password'),
            author_name: formData.get('author_name'),
            default_category: formData.get('default_category'),
            post_status: formData.get('post_status')
        },
        gemini: {
            api_key: formData.get('gemini_key'),
            enabled: formData.get('auto_translate') === 'on'
        },
        search: {
            keywords: formData.get('keywords').split(',').map(k => k.trim()),
            max_articles: parseInt(formData.get('max_articles')),
            language_preference: formData.get('language_preference'),
            recent_days: parseInt(formData.get('recent_days'))
        },
        schedule: {
            enabled: formData.get('schedule_enabled') === 'on',
            hour: parseInt(formData.get('schedule_hour')),
            minute: parseInt(formData.get('schedule_minute')),
            timezone: formData.get('timezone')
        },
        content: {
            auto_translate: formData.get('auto_translate') === 'on',
            target_language: 'pt',
            preserve_formatting: true,
            add_source_link: true,
            add_author_credit: true
        }
    };
    
    return settings;
}

// Show alert message
function showAlert(message, type) {
    const alertContainer = document.querySelector('.container');
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    alertContainer.insertBefore(alertDiv, alertContainer.firstChild);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// Manual sync function
function manualSync() {
    const syncButton = document.querySelector('.sync-button');
    const originalText = syncButton.innerHTML;
    
    syncButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Sincronizando...';
    syncButton.disabled = true;
    
    fetch('/api/sync', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert(`Sincronização concluída: ${data.result.synced} artigos sincronizados`, 'success');
            setTimeout(() => window.location.reload(), 2000);
        } else {
            showAlert('Erro na sincronização: ' + data.error, 'danger');
        }
    })
    .catch(error => {
        showAlert('Erro na sincronização', 'danger');
        console.error('Error:', error);
    })
    .finally(() => {
        syncButton.innerHTML = originalText;
        syncButton.disabled = false;
    });
}

// Export settings
function exportSettings() {
    fetch('/settings/export')
        .then(response => response.json())
        .then(data => {
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'medium-wordpress-settings.json';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        });
}

// Import settings
function importSettings() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'application/json';
    
    input.onchange = function(event) {
        const file = event.target.files[0];
        const reader = new FileReader();
        
        reader.onload = function(e) {
            const settings = JSON.parse(e.target.result);
            
            fetch('/settings/import', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(settings)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showAlert('Configurações importadas com sucesso!', 'success');
                    setTimeout(() => window.location.reload(), 1500);
                } else {
                    showAlert('Erro ao importar configurações', 'danger');
                }
            });
        };
        
        reader.readAsText(file);
    };
    
    input.click();
}