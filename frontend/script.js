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
    actionInput: document.getElementById('action-input')
};

/**
 * Session Persistence
 */
const getSessionId = () => {
    let sid = sessionStorage.getItem('lex_session_id');
    if (!sid) {
        sid = 'sess_' + Math.random().toString(36).substring(2, 15);
        sessionStorage.setItem('lex_session_id', sid);
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
    
    // Prune logs if too many
    if (elements.logsContainer.childElementCount > 20) {
        elements.logsContainer.removeChild(elements.logsContainer.firstChild);
    }
}

/**
 * Fetch and Populate Tasks
 */
async function loadTasks() {
    try {
        const res = await fetch('/tasks', {
            headers: { 'X-Session-ID': getSessionId() }
        });
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

    // Update reward displays if available
    const reward = state.reward || 0;
    const currentScore = parseFloat(elements.statScore.textContent);
    elements.statScore.textContent = (currentScore + reward).toFixed(2);
    elements.statDelta.textContent = (reward >= 0 ? '+' : '') + reward.toFixed(2);
    elements.statDelta.style.color = reward >= 0 ? 'var(--pos-green)' : 'var(--neg-red)';
    
    // Action Controls
    elements.btnRun.disabled = state.done;
    
    if (state.done) {
        elements.actionInput.disabled = true;
        logMsg(`Episode Terminated. Final Score: ${elements.statScore.textContent}`, 'sys');
    } else {
        elements.actionInput.disabled = false;
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
        const res = await fetch(`/reset?task_id=${taskId}`, { 
            method: 'POST',
            headers: { 'X-Session-ID': getSessionId() }
        });
        const data = await res.json();
        
        // Zero out UI stats
        elements.statScore.textContent = '0.00';
        elements.statDelta.textContent = '0.00';
        elements.statDelta.style.color = 'var(--pos-green)';
        elements.flagsContainer.innerHTML = '<p class="empty-hint">Scanning document...</p>';
        
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
    const action = elements.actionInput.value;
    if (!action.trim()) return;
    
    elements.btnRun.disabled = true;
    logMsg('Processing inference step...', 'sys');
    
    try {
        const payload = {
            action: { "analysis": action, "risk_assessment": "high" }
        };

        const res = await fetch('/step', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-Session-ID': getSessionId()
            },
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
    
    // Update task and AUTO-RESET on change
    elements.taskSelect.addEventListener('change', () => {
        const selected = elements.taskSelect.options[elements.taskSelect.selectedIndex];
        elements.taskBrief.textContent = selected.dataset.desc;
        actReset(); // Auto-sync
    });
});
