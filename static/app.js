// Medium to WordPress - Simplified JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Auto-refresh dashboard every 60 seconds
    if (window.location.pathname === '/') {
        setInterval(refreshDashboard, 60000);
    }
});

// Refresh dashboard data
function refreshDashboard() {
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            // Reload page if data changed
            window.location.reload();
        })
        .catch(error => console.error('Error:', error));
}

// Manual sync
function manualSync() {
    if (!confirm('Iniciar sincronização manual?')) return;
    
    fetch('/api/sync', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(`Sincronização concluída: ${data.result.synced} artigos`);
                window.location.reload();
            } else {
                alert('Erro: ' + data.error);
            }
        })
        .catch(error => {
            alert('Erro na sincronização');
        });
}

// Sync single article
function syncArticle(url) {
    
    fetch('/api/sync_article', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({url: url})
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            alert('Artigo sincronizado com sucesso!');
        } else {
            alert('Erro: ' + (data.message || 'Falha na sincronização'));
        }
    })
    .catch(error => {
        alert('Erro: ' + error.message);
    });
}

// Test connections
function testConnections() {
    const modal = document.getElementById('testModal');
    const resultsDiv = document.getElementById('testResults');
    
    resultsDiv.innerHTML = '<div class="loading">Testando conexões...</div>';
    modal.classList.add('active');
    
    fetch('/test-connection', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            let html = '<table>';
            html += `<tr><td>Medium API</td><td>${data.medium ? '✅' : '❌'}</td></tr>`;
            html += `<tr><td>WordPress</td><td>${data.wordpress ? '✅' : '❌'}</td></tr>`;
            html += '</table>';
            resultsDiv.innerHTML = html;
        })
        .catch(error => {
            resultsDiv.innerHTML = 'Erro ao testar conexões';
        });
}

// Close modal
function closeModal() {
    document.getElementById('testModal').classList.remove('active');
}

// Toggle automation
function toggleAutomation(checkbox) {
    const enabled = checkbox.checked;
    
    fetch('/api/automation/toggle', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ enabled: enabled })
    })
    .then(response => response.json())
    .then(data => {
        if (!data.success) {
            checkbox.checked = !enabled;
            alert('Erro ao alterar automação');
        }
    })
    .catch(error => {
        checkbox.checked = !enabled;
        alert('Erro ao alterar automação');
    });
}

// Save settings
function saveSettings() {
    const form = document.getElementById('settingsForm') || document.querySelector('form');
    const formData = new FormData(form);
    
    // Build settings object with proper structure
    const settings = {
        medium_api: {
            rapidapi_key: formData.get('rapidapi_key') || '',
            rapidapi_host: formData.get('rapidapi_host') || 'medium2.p.rapidapi.com'
        },
        wordpress: {
            url: formData.get('wordpress_url') || '',
            username: formData.get('wordpress_username') || '',
            password: formData.get('wordpress_password') || '',
            default_category: formData.get('default_category') || 'Technology',
            post_status: formData.get('post_status') || 'draft'
        },
        gemini: {
            api_key: formData.get('gemini_key') || '',
            enabled: document.querySelector('input[name="auto_translate"]')?.checked || false
        },
        search: {
            keywords: (formData.get('keywords') || '').split(',').map(k => k.trim()).filter(k => k),
            max_articles: parseInt(formData.get('max_articles') || '2'),
            language_preference: formData.get('language_preference') || 'both',
            recent_days: parseInt(formData.get('recent_days') || '30')
        },
        schedule: {
            enabled: document.querySelector('input[name="schedule_enabled"]')?.checked || false,
            hour: parseInt(formData.get('schedule_hour') || '8'),
            minute: parseInt(formData.get('schedule_minute') || '0'),
            timezone: formData.get('timezone') || 'America/Sao_Paulo'
        },
        content: {
            auto_translate: document.querySelector('input[name="auto_translate"]')?.checked || false,
            target_language: 'pt',
            preserve_formatting: true,
            add_source_link: true,
            add_author_credit: true
        }
    };
    
    // Send settings to server
    fetch('/settings/save', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(settings)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Configurações salvas com sucesso!');
            window.location.reload();
        } else {
            alert('Erro ao salvar configurações: ' + (data.error || 'Erro desconhecido'));
        }
    })
    .catch(error => {
        alert('Erro ao salvar configurações: ' + error.message);
    });
    
    return false; // Prevent form submission
}