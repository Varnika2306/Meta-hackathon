const elements = {
    // Nav & Controls
    taskSelect: document.getElementById('task-select'),
    btnReset: document.getElementById('btn-reset'),
    btnRun: document.getElementById('btn-run'),
    
    // Displays
    taskNameDisplay: document.getElementById('task-name-display'),
    taskBrief: document.getElementById('task-brief'),
    logsContainer: document.getElementById('logs-container'),
    
    // Content Panels
    emptyState: document.getElementById('empty-state'),
    contextView: document.getElementById('context-view'),
    instructionText: document.getElementById('instruction-text'),
    excerptText: document.getElementById('excerpt-text'),
    feedbackBlock: document.getElementById('feedback-block'),
    feedbackText: document.getElementById('feedback-text'),
    
    // Intel Stats
    statScore: document.getElementById('stat-score'),
    statDelta: document.getElementById('stat-delta'),
    statStep: document.getElementById('stat-step'),
    flagsContainer: document.getElementById('flags-container'),
    actionInput: document.getElementById('action-input'),
    toneBar: document.getElementById('tone-bar'),
    toneFeedback: document.getElementById('tone-feedback')
};

/**
 * Session Persistence - Using LocalStorage for durability
 */
const getSessionId = () => {
    let sid = localStorage.getItem('lex_session_id');
    if (!sid) {
        sid = 'sess_' + Math.random().toString(36).substring(2, 10);
        localStorage.setItem('lex_session_id', sid);
    }
    return sid;
};

/**
 * Enhanced Logging with auto-scroll
 */
function logMsg(msg, type = 'sys') {
    const entry = document.createElement('div');
    entry.className = `log-entry ${type} fade-in`;
    const time = new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit' });
    entry.textContent = `[${time}] ${msg}`;
    
    elements.logsContainer.appendChild(entry);
    elements.logsContainer.scrollTop = elements.logsContainer.scrollHeight;
    
    if (elements.logsContainer.childElementCount > 20) {
        elements.logsContainer.removeChild(elements.logsContainer.firstChild);
    }
}

/**
 * Fetch and Populate Tasks
 */
async function loadTasks() {
    try {
        const sid = getSessionId();
        const res = await fetch(`/tasks?session_id=${sid}`);
        const data = await res.json();
        const tasks = data.tasks || data;
        
        elements.taskSelect.innerHTML = '<option value="" disabled selected>Select Task...</option>';
        tasks.forEach(t => {
            const opt = document.createElement('option');
            opt.value = t.id;
            opt.textContent = t.name;
            opt.dataset.desc = t.description || 'Legal analysis task';
            elements.taskSelect.appendChild(opt);
        });
        logMsg('Network established. Tasks synchronized.', 'ready');
    } catch (err) {
        logMsg('Connection error: ' + err.message);
    }
}

/**
 * Update UI state based on Backend response
 */
function updateStateUI(state) {
    const obs = state.observation || {};
    
    // Swap views
    elements.emptyState.classList.add('hidden');
    elements.contextView.classList.remove('hidden');
    
    // Identity
    elements.taskNameDisplay.textContent = obs.task_name || 'Active Task';
    
    // Content
    elements.instructionText.textContent = obs.instruction || '';
    elements.excerptText.textContent = obs.contract_excerpt || '';
    
    if (obs.previous_analysis) {
        elements.feedbackBlock.classList.remove('hidden');
        elements.feedbackText.textContent = obs.previous_analysis;
    } else {
        elements.feedbackBlock.classList.add('hidden');
    }
    
    // Stats
    const prog = obs.progress || {};
    elements.statStep.textContent = `${prog.step || 0} / ${prog.max_steps || 0}`;

    // Update reward displays correctly
    const reward = state.reward !== undefined ? state.reward : (obs.reward || 0);
    const currentScore = parseFloat(elements.statScore.textContent);
    
    if (prog.step > 0) {
        elements.statScore.textContent = (currentScore + reward).toFixed(2);
    } else {
        elements.statScore.textContent = '0.00';
    }
    
    elements.statDelta.textContent = (reward >= 0 ? '+' : '') + reward.toFixed(2);
    elements.statDelta.style.color = reward >= 0 ? 'var(--pos-green)' : 'var(--neg-red)';
    
    // Update Tone Meter
    const tone = obs.tone_analysis || {};
    const toneScore = tone.score || 0;
    elements.toneBar.style.width = `${toneScore * 100}%`;
    elements.toneFeedback.textContent = tone.feedback || 'Legalese quality being appraised...';

    // Update Risk Flags
    const flags = obs.identified_flags || [];
    elements.flagsContainer.innerHTML = '';
    
    if (flags.length > 0) {
        flags.forEach(f => {
            const badge = document.createElement('div');
            badge.className = `flag-badge sev-${(f.severity || 'medium').toLowerCase()}`;
            badge.innerHTML = `
                <span class="flag-title">${f.title}</span>
                <span class="flag-sev">${f.severity.toUpperCase()}</span>
            `;
            elements.flagsContainer.appendChild(badge);
        });
    } else {
        const hint = document.createElement('p');
        hint.className = 'empty-hint';
        hint.textContent = 'No risks detected in this analysis.';
        elements.flagsContainer.appendChild(hint);
    }

    // Action Controls
    const isDone = state.done || obs.done;
    elements.btnRun.disabled = isDone;
    
    if (isDone) {
        elements.actionInput.disabled = true;
        elements.actionInput.placeholder = "Session complete.";
        logMsg(`Episode Terminated. Final Score: ${elements.statScore.textContent}`, 'sys');
    } else {
        elements.actionInput.disabled = false;
        elements.actionInput.placeholder = "Enter your legal analysis here...";
        
        // Smart Template
        const actionVal = elements.actionInput.value;
        if (!actionVal.trim() || actionVal.includes("Analyzing")) {
            elements.actionInput.value = `Analyzing ${obs.task_name || "contract"}...`;
        }
    }
}

/**
 * Execute Environment Reset
 */
async function actReset() {
    const taskId = elements.taskSelect.value;
    if (!taskId) return;
    
    elements.btnReset.disabled = true;
    logMsg(`Mounting task environment: ${taskId}`, 'sys');
    
    try {
        const sid = getSessionId();
        const payload = {
            task_id: taskId,
            session_id: sid
        };

        const res = await fetch(`/reset?session_id=${sid}`, { 
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        
        // Reset UI stats
        elements.statScore.textContent = '0.00';
        elements.statDelta.textContent = '0.00';
        elements.statDelta.style.color = 'var(--pos-green)';
        elements.flagsContainer.innerHTML = '<p class="empty-hint">Scanning document...</p>';
        elements.actionInput.value = "";
        
        updateStateUI(data);
        logMsg('Initialization complete. Agent ready.', 'ready');
    } catch (err) {
        logMsg('Boot error: ' + err.message);
    } finally {
        elements.btnReset.disabled = false;
    }
}

/**
 * Execute Step/Action
 */
async function actRun() {
    const analysis = elements.actionInput.value;
    if (!analysis.trim()) return;
    
    elements.btnRun.disabled = true;
    logMsg('Processing inference step...', 'sys');
    
    try {
        const sid = getSessionId();
        // SLEDGEHAMMER: session_id goes directly into action object
        const payload = {
            action: { 
                "analysis": analysis, 
                "risk_assessment": "high",
                "session_id": sid 
            },
            session_id: sid
        };

        const res = await fetch(`/step?session_id=${sid}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        
        updateStateUI(data);
        logMsg(`Step ${data.observation.step} processed. Reward calculated.`, 'ready');
    } catch (err) {
        logMsg('Step failed: ' + err.message);
    } finally {
        if (!elements.actionInput.disabled) elements.btnRun.disabled = false;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadTasks();
    elements.btnReset.addEventListener('click', actReset);
    elements.btnRun.addEventListener('click', actRun);
    
    elements.taskSelect.addEventListener('change', () => {
        const selected = elements.taskSelect.options[elements.taskSelect.selectedIndex];
        elements.taskBrief.textContent = selected.dataset.desc;
        actReset();
    });
});
