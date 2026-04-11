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
        const res = await fetch('/tasks');
        const data = await res.json();
        
        elements.taskSelect.innerHTML = '<option value="" disabled selected>Select Task...</option>';
        data.tasks.forEach(t => {
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
    
    // Action Controls
    elements.btnRun.disabled = state.done;
    
    if (state.done) {
        elements.actionInput.value = '';
        elements.actionInput.placeholder = 'OS Session Ended.';
        elements.actionInput.disabled = true;
        logMsg(`Episode Terminated. Efficiency: ${prog.step}/${prog.max_steps}`, 'sys');
    } else {
        elements.actionInput.disabled = false;
        // Smart Template Pre-fill
        if (!elements.actionInput.value || elements.actionInput.value.includes("Enter your analysis")) {
            elements.actionInput.value = JSON.stringify({
                analysis: "Synthesizing legal risks...",
                flags: [],
                risk_assessment: "medium"
            }, null, 2);
        }
    }
}

/**
 * Execute Environment Reset
 */
async function actReset() {
    const taskId = elements.taskSelect.value;
    if (!taskId) {
        logMsg('ERR: Select task definition code first.');
        return;
    }
    
    elements.btnReset.disabled = true;
    logMsg(`Mounting task environment: ${taskId}`, 'sys');
    
    try {
        const res = await fetch(`/reset?task_id=${taskId}`, { method: 'POST' });
        const data = await res.json();
        
        // Zero out UI
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
    let actionData;
    try {
        actionData = JSON.parse(elements.actionInput.value);
    } catch (e) {
        logMsg('PARSE ERR: Invalid JSON payload in buffer.');
        return;
    }
    
    elements.btnRun.disabled = true;
    logMsg('Processing inference step...', 'sys');
    
    try {
        const res = await fetch('/step', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: actionData })
        });
        const data = await res.json();
        
        // Update flags
        if (actionData.flags && actionData.flags.length > 0) {
            const flagsHtml = actionData.flags.map(f => `
                <div class="flag">
                    <strong style="color:var(--accent-violet)">[${(f.severity || 'low').toUpperCase()}]</strong> 
                    ${f.title}
                </div>
            `).join('');
            elements.flagsContainer.innerHTML = flagsHtml;
        }
        
        // Visual stat update
        const reward = data.reward || 0;
        const currentScore = parseFloat(elements.statScore.textContent);
        elements.statScore.textContent = (currentScore + reward).toFixed(2);
        
        elements.statDelta.textContent = (reward >= 0 ? '+' : '') + reward.toFixed(2);
        elements.statDelta.style.color = reward >= 0 ? 'var(--pos-green)' : 'var(--neg-red)';
        
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
    
    // Update task description on select
    elements.taskSelect.addEventListener('change', () => {
        const selected = elements.taskSelect.options[elements.taskSelect.selectedIndex];
        elements.taskBrief.textContent = selected.dataset.desc;
    });
});
