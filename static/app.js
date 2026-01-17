/**
 * MedDoc Dashboard - Professional Edition logic
 */

// === DOM Elements ===
const elements = {
    // Navigation
    navLinks: document.querySelectorAll('.nav-link'),
    sections: document.querySelectorAll('.section-content'),

    // Status
    statusBadge: document.getElementById('status-badge'),
    consultStatus: document.getElementById('consultation-status'),
    welcomeSection: document.getElementById('welcome-section'),

    // Input / Tabs
    tabPills: document.querySelectorAll('.tab-pill'),
    urlInput: document.getElementById('url-input'),
    processUrlBtn: document.getElementById('process-url-btn'),
    fileInput: document.getElementById('file-input'),
    dropZone: document.getElementById('drop-zone'),
    selectedFile: document.getElementById('selected-file'),
    fileName: document.getElementById('file-name'),
    processFileBtn: document.getElementById('process-file-btn'),

    // Results
    processingStatus: document.getElementById('processing-status'),
    resultsSection: document.getElementById('results-section'),
    sidebarResults: document.getElementById('sidebar-results'),
    summaryText: document.getElementById('summary-text'),
    transcriptContainer: document.getElementById('transcript-container'),
    documentationContent: document.getElementById('documentation-content'),
    tasksGrid: document.getElementById('tasks-grid'),
    tasksCount: document.getElementById('tasks-count'),

    // Recording
    micStatus: document.getElementById('mic-status'),
    visualizer: document.getElementById('visualizer'),
    recordTimer: document.getElementById('record-timer'),
    startRecordBtn: document.getElementById('start-record-btn'),
    stopRecordBtn: document.getElementById('stop-record-btn'),
    recordingResult: document.getElementById('recording-result'),
    uploadRecordingBtn: document.getElementById('upload-recording-btn'),

    // Errors
    errorMessage: document.getElementById('error-message'),
    errorText: document.getElementById('error-text')
};

// === State ===
let currentFile = null;
let taskTimers = {};

// === Initialization ===
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initTabs();
    initFileUpload();
    initRecording();
    checkApiStatus();
});

// === Section Navigation ===
function initNavigation() {
    elements.navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const sectionId = link.dataset.section;
            if (!sectionId) return;

            // Update nav active state
            elements.navLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');

            // Switch visibility
            elements.sections.forEach(sec => {
                sec.classList.remove('active');
                if (sec.id === `section-${sectionId}`) {
                    sec.classList.add('active');
                }
            });
        });
    });
}

// === Tab System ===
function initTabs() {
    elements.tabPills.forEach(pill => {
        pill.addEventListener('click', () => {
            // Update active pill
            elements.tabPills.forEach(p => p.classList.remove('active'));
            pill.classList.add('active');

            // Show content
            const tabId = pill.dataset.tab;
            document.querySelectorAll('.input-content').forEach(c => c.classList.remove('active'));
            document.getElementById(`tab-${tabId}`).classList.add('active');
        });
    });
}

// === File Management ===
function initFileUpload() {
    elements.dropZone.addEventListener('click', () => elements.fileInput.click());

    elements.dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        elements.dropZone.style.borderColor = 'var(--primary)';
    });

    elements.dropZone.addEventListener('dragleave', () => {
        elements.dropZone.style.borderColor = 'var(--border)';
    });

    elements.dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        const file = e.dataTransfer.files[0];
        if (file) handleFileSelect(file);
    });

    elements.fileInput.addEventListener('change', (e) => {
        if (e.target.files[0]) handleFileSelect(e.target.files[0]);
    });
}

// === Recording Logic ===
let mediaRecorder = null;
let audioChunks = [];
let recordingStartTime = null;
let recordingInterval = null;
let recordedBlob = null;

function initRecording() {
    elements.startRecordBtn.addEventListener('click', startRecording);
    elements.stopRecordBtn.addEventListener('click', stopRecording);
    elements.uploadRecordingBtn.addEventListener('click', () => {
        if (recordedBlob) {
            // Create a file object from the blob
            const file = new File([recordedBlob], "recording.webm", { type: "audio/webm" });
            runAnalysis('file', file);
        }
    });
}

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = () => {
            recordedBlob = new Blob(audioChunks, { type: 'audio/webm' });

            // Show result UI
            elements.recordingResult.style.display = 'block';
            elements.micStatus.textContent = "Recording captured";

            // cleanup tracks
            stream.getTracks().forEach(track => track.stop());
        };

        mediaRecorder.start();

        // UI Updates
        elements.startRecordBtn.style.display = 'none';
        elements.stopRecordBtn.style.display = 'inline-flex';
        elements.visualizer.style.display = 'flex';
        elements.recordingResult.style.display = 'none';
        elements.micStatus.textContent = "Recording...";
        elements.micStatus.style.color = 'var(--danger)';

        // Timer
        recordingStartTime = Date.now();
        elements.recordTimer.textContent = "00:00";
        recordingInterval = setInterval(updateRecordTimer, 1000);

    } catch (err) {
        showToastError('Microphone access denied or error: ' + err.message);
        console.error(err);
    }
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();

        // UI Updates
        elements.startRecordBtn.style.display = 'inline-flex';
        elements.stopRecordBtn.style.display = 'none';
        elements.visualizer.style.display = 'none';
        elements.micStatus.style.color = 'var(--text-muted)';

        clearInterval(recordingInterval);
    }
}

function updateRecordTimer() {
    const diff = Math.floor((Date.now() - recordingStartTime) / 1000);
    const m = Math.floor(diff / 60).toString().padStart(2, '0');
    const s = (diff % 60).toString().padStart(2, '0');
    elements.recordTimer.textContent = `${m}:${s}`;
}

function handleFileSelect(file) {
    currentFile = file;
    elements.fileName.textContent = file.name;
    elements.selectedFile.style.display = 'block';
}

// === Action Handlers ===
elements.processUrlBtn.addEventListener('click', async () => {
    const url = elements.urlInput.value.trim();
    if (!url) return showToastError('Valid YouTube URL required');
    await runAnalysis('url', url);
});

elements.processFileBtn.addEventListener('click', async () => {
    if (!currentFile) return;
    await runAnalysis('file', currentFile);
});

async function runAnalysis(type, data) {
    // Reset UI
    hideError();
    elements.welcomeSection.style.display = 'none';
    elements.resultsSection.style.display = 'none';
    elements.sidebarResults.style.display = 'none';
    elements.processingStatus.style.display = 'block';

    updateHeaderStatus('Analyzing Consultation...', 'warning');

    try {
        let response;
        if (type === 'url') {
            response = await fetch('/api/process-url', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: data })
            });
        } else {
            const formData = new FormData();
            formData.append('file', data);
            response = await fetch('/api/process-audio', {
                method: 'POST',
                body: formData
            });
        }

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || 'Analysis failed');
        }

        const result = await response.json();
        renderResults(result);

    } catch (err) {
        showError(err.message);
        elements.welcomeSection.style.display = 'block';
    } finally {
        elements.processingStatus.style.display = 'none';
    }
}

// === Rendering Logic ===
function renderResults(result) {
    updateHeaderStatus('Analysis Complete', 'success');

    // Core Documentation
    elements.summaryText.textContent = result.summary;
    renderTranscript(result.transcript_segments);
    renderDetailedDoc(result.documentation);
    renderTasks(result.nurse_tasks);

    // STRATEGIC PILLARS RENDER
    if (result.documentation.insurance_audit) renderInsuranceAudit(result.documentation.insurance_audit);
    if (result.documentation.nurse_handover) renderHandover(result.documentation.nurse_handover);
    if (result.documentation.patient_summary) renderWhatsApp(result.documentation.patient_summary, result.documentation.patient_info?.name);

    // Show Sections
    elements.resultsSection.style.display = 'block';
    elements.sidebarResults.style.display = 'block';
    elements.resultsSection.scrollIntoView({ behavior: 'smooth' });
}

function renderInsuranceAudit(auditList) {
    const container = document.getElementById('audit-container');
    const section = document.getElementById('insurance-section');

    if (!auditList || auditList.length === 0) {
        section.style.display = 'none';
        return;
    }

    section.style.display = 'block';
    container.innerHTML = auditList.map(issue => `
        <div class="insurance-card risk-${issue.severity}">
            <div style="font-weight: 700; display: flex; justify-content: space-between;">
                <span>${issue.missing_evidence}</span>
                <span class="audit-badge badge-${issue.severity}">${issue.severity} RISK</span>
            </div>
            <p style="font-size: 0.85rem; margin: 0.5rem 0; color: var(--text-secondary);">
                ${issue.rule_violated}
            </p>
            <div class="audit-issue">
                <strong style="font-size: 0.8rem; text-transform: uppercase;">Fix:</strong>
                <span style="font-size: 0.9rem;">${issue.suggestion}</span>
            </div>
        </div>
    `).join('');
}

function renderHandover(handover) {
    const btn = document.getElementById('btn-handover');
    if (!handover) {
        btn.style.display = 'none';
        return;
    }
    btn.style.display = 'inline-flex';

    // Inject data into modal structure
    const target = document.getElementById('sbar-inject');
    target.innerHTML = `
        <div class="sbar-section">
            <span class="sbar-label">Situation</span>
            <p class="sbar-content">${escapeHtml(handover.summary_sbar.split('Situation:')[1]?.split('Background:')[0] || handover.summary_sbar)}</p>
        </div>
        <div class="sbar-section" style="border-left-color: var(--info);">
            <span class="sbar-label">Critical Alerts</span>
            <ul style="padding-left: 1rem; margin-bottom: 0;">
                ${handover.critical_alerts.map(a => `<li>${a}</li>`).join('')}
            </ul>
        </div>
        <div class="sbar-section" style="border-left-color: var(--warning);">
            <span class="sbar-label">Pending Actions</span>
            <ul style="padding-left: 1rem; margin-bottom: 0;">
                ${handover.pending_actions.map(a => `<li>${a}</li>`).join('')}
            </ul>
        </div>
    `;

    btn.onclick = () => {
        document.getElementById('modal-backdrop').classList.add('show');
        document.getElementById('handover-modal').classList.add('show');
    };
}

function renderWhatsApp(summary, patientName) {
    const btn = document.getElementById('btn-whatsapp');
    if (!summary) {
        btn.style.display = 'none';
        return;
    }
    btn.style.display = 'inline-flex';

    // Update Modal Data
    document.getElementById('wa-patient-name').textContent = patientName || 'Guest';
    document.getElementById('wa-text-content').innerHTML = summary.whatsapp_message.replace(/\n/g, '<br>');

    // Reset button state
    const sendBtn = document.querySelector('.btn-whatsapp-send');
    if (sendBtn) {
        sendBtn.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
            Send via WhatsApp
        `;
        sendBtn.style.background = '#25D366';
    }

    btn.onclick = () => {
        document.getElementById('modal-backdrop').classList.add('show');
        document.getElementById('wa-modal').classList.add('show');
    };
}

// Global Modal Controls
window.closeWaModal = () => {
    document.getElementById('wa-modal').classList.remove('show');
    document.getElementById('modal-backdrop').classList.remove('show');
};

window.closeHandoverModal = () => {
    document.getElementById('handover-modal').classList.remove('show');
    document.getElementById('modal-backdrop').classList.remove('show');
};

window.simulateSend = () => {
    const btn = document.querySelector('.btn-whatsapp-send');
    if (!btn) return;

    const originalText = btn.innerHTML;
    btn.innerHTML = '✅ Sent!';
    btn.style.background = '#10B981';
    setTimeout(() => {
        window.closeWaModal();
        btn.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
            Send via WhatsApp
        `;
        btn.style.background = '#25D366';
    }, 1500);
};

function renderTranscript(segments) {
    if (!segments) return;
    elements.transcriptContainer.innerHTML = segments.map(seg => `
        <div class="transcript-bubble ${seg.speaker}">
            <div class="bubble-header">
                <span class="bubble-speaker">${seg.speaker}</span>
                <span class="bubble-meta">${seg.timestamp} • ${seg.language} (${seg.emotion})</span>
            </div>
            <p class="bubble-content">${escapeHtml(seg.content)}</p>
            ${seg.translation ? `<p class="bubble-translation">🌐 ${seg.translation}</p>` : ''}
        </div>
    `).join('');
}

function renderDetailedDoc(doc) {
    let html = '';

    if (doc.patient_info) {
        html += renderDocBlock('Patient Demographics', [
            ['Name', doc.patient_info.name],
            ['Age', doc.patient_info.age],
            ['Gender', doc.patient_info.gender],
            ['Bed Number', doc.patient_info.bed_number]
        ]);
    }

    if (doc.chief_complaints?.length) {
        html += renderListBlock('Chief Complaints', doc.chief_complaints);
    }

    if (doc.medications?.length) {
        html += `
            <div class="info-block" style="margin-top: 1rem;">
                <p style="font-size: 0.8rem; text-transform: uppercase; font-weight: 700; color: var(--text-muted); margin-bottom: 0.5rem;">Medications</p>
                ${doc.medications.map(m => `
                    <div class="card" style="padding: 0.75rem; margin-bottom: 0.5rem; background: var(--bg-main);">
                        <div style="font-weight: 700; color: var(--primary);">💊 ${m.drug_name}</div>
                        <div style="font-size: 0.85rem; color: var(--text-secondary);">${m.dosage} - ${m.frequency}</div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    if (doc.instructions?.length) {
        html += renderListBlock('Care Instructions', doc.instructions);
    }

    elements.documentationContent.innerHTML = html;
}

function renderTasks(tasks) {
    if (!tasks) return;
    elements.tasksCount.textContent = tasks.length;

    elements.tasksGrid.innerHTML = tasks.map(task => {
        const priorityClass = task.priority === 'HIGH' ? 'tag-danger' :
            task.priority === 'MEDIUM' ? 'tag-warning' : 'tag-success';

        return `
            <div class="task-item-modern" id="task-${task.task_id}">
                <div class="task-top">
                    <span class="tag-badge ${priorityClass}">${task.priority}</span>
                    <span style="font-size: 0.75rem; font-weight: 700; color: var(--text-muted);">${task.task_type}</span>
                </div>
                <p class="task-desc">${task.description}</p>
                <div class="task-footer">
                    <div class="timer-box">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                        <span>${task.due_time || 'Sched.'}</span>
                    </div>
                    <button class="btn-clinical" style="padding: 0.4rem 0.75rem; font-size: 0.8rem;" onclick="markDone('${task.task_id}')">Done</button>
                </div>
            </div>
        `;
    }).join('');
}

// === Helper Components ===
function renderDocBlock(title, pairs) {
    const rows = pairs.filter(p => p[1]).map(p => `
        <div class="info-row">
            <span class="info-label">${p[0]}</span>
            <span class="info-value">${p[1]}</span>
        </div>
    `).join('');

    return rows ? `
        <div class="info-block" style="margin-top: 0.5rem;">
            <p style="font-size: 0.8rem; text-transform: uppercase; font-weight: 700; color: var(--text-muted); margin-bottom: 0.5rem;">${title}</p>
            <div class="card" style="padding: 0 1rem; margin-bottom: 1rem;">${rows}</div>
        </div>
    ` : '';
}

function renderListBlock(title, items) {
    return items?.length ? `
        <div class="info-block" style="margin-top: 1rem;">
            <p style="font-size: 0.8rem; text-transform: uppercase; font-weight: 700; color: var(--text-muted); margin-bottom: 0.5rem;">${title}</p>
            <ul style="list-style: none; padding-left: 0;">
                ${items.map(i => `<li class="info-row" style="padding-left: 0.5rem;">• ${i}</li>`).join('')}
            </ul>
        </div>
    ` : '';
}

// === Global Funcs (for onclick) ===
window.markDone = (id) => {
    const el = document.getElementById(`task-${id}`);
    if (el) {
        el.style.opacity = '0.4';
        el.style.pointerEvents = 'none';
        el.querySelector('button').textContent = 'Completed';
    }
};

function showToastError(msg) {
    // Reuse existing error display for now
    showError(msg);
}

// === Utility ===
function updateHeaderStatus(text, type) {
    elements.consultStatus.textContent = text;
    elements.statusBadge.style.background = type === 'warning' ? '#FEF3C7' : '#DCFCE7';
    elements.statusBadge.style.color = type === 'warning' ? '#92400E' : '#166534';
}

function showError(msg) {
    elements.errorMessage.style.display = 'block';
    elements.errorText.textContent = msg;
}

function hideError() {
    elements.errorMessage.style.display = 'none';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function checkApiStatus() {
    try {
        const res = await fetch('/api/health');
        const data = await res.json();
        if (!data.api_key_configured) {
            showError('Gemini API Key missing. Please check your .env file.');
        }
    } catch (e) {
        console.warn('API Health check failed');
    }
}
