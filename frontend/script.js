const elements = {
    taskSelect: document.getElementById('task-select'),
    btnReset: document.getElementById('btn-reset'),
    btnRun: document.getElementById('btn-run'),
    logsContainer: document.getElementById('logs-container'),
    contextWrapper: document.getElementById('context-wrapper'),
    instructionText: document.getElementById('instruction-text'),
    excerptText: document.getElementById('excerpt-text'),
    feedbackBlock: document.getElementById('feedback-block'),
    feedbackText: document.getElementById('feedback-text'),
    statScore: document.getElementById('stat-score'),
    statDelta: document.getElementById('stat-delta'),
    statStep: document.getElementById('stat-step'),
    flagsContainer: document.getElementById('flags-container'),
    actionInput: document.getElementById('action-input')
};

function logMsg(msg, isSystem = true) {
    const p = document.createElement('p');
    p.className = `sys-msg fade-in`;
    p.textContent = isSystem ? `> [SYSTEM] ${msg}` : msg;
    elements.logsContainer.appendChild(p);
    
    if (elements.logsContainer.childElementCount > 5) {
        elements.logsContainer.removeChild(elements.logsContainer.firstChild);
    }
}

async function loadTasks() {
    try {
        const res = await fetch('/tasks');
        const data = await res.json();
        
        elements.taskSelect.innerHTML = '';
        data.tasks.forEach(t => {
            const opt = document.createElement('option');
            opt.value = t.id;
            opt.textContent = `${t.name} (${t.difficulty})`;
            elements.taskSelect.appendChild(opt);
        });
        logMsg('Available tasks loaded.');
    } catch (err) {
        logMsg('Failed to load tasks. ' + err.message);
    }
}

function updateStateUI(state) {
    const obs = state.observation || {};
    elements.contextWrapper.classList.remove('hidden');
    elements.instructionText.textContent = obs.instruction || '';
    elements.excerptText.textContent = obs.contract_excerpt || '';
    
    if (obs.previous_analysis) {
        elements.feedbackBlock.classList.remove('hidden');
        elements.feedbackText.textContent = obs.previous_analysis;
    } else {
        elements.feedbackBlock.classList.add('hidden');
    }
    
    const prog = obs.progress || {};
    elements.statStep.textContent = `${prog.step || 0}/${prog.max_steps || 0}`;
    
    elements.btnRun.disabled = state.done;
    
    if (state.done) {
        elements.actionInput.value = '';
        elements.actionInput.placeholder = 'Episode complete.';
        elements.actionInput.disabled = true;
        logMsg(`Episode done. Final Score: ${Number(prog.rewards_so_far || 0).toFixed(2)}`);
    } else {
        elements.actionInput.disabled = false;
        elements.actionInput.value = JSON.stringify({
            analysis: "Enter your analysis here...",
            flags: [],
            risk_assessment: "medium"
        }, null, 2);
    }
}

async function actReset() {
    const taskId = elements.taskSelect.value;
    if (!taskId) return;
    
    elements.btnReset.disabled = true;
    logMsg(`Initializing environment for task: ${taskId}...`);
    
    try {
        const res = await fetch(`/reset?task_id=${taskId}`, { method: 'POST' });
        const data = await res.json();
        
        elements.statScore.textContent = '0.00';
        elements.statDelta.textContent = '+0.00';
        elements.flagsContainer.innerHTML = '<p class="placeholder-text">No issues flagged yet.</p>';
        updateStateUI(data);
        logMsg('Link established. Awaiting solution.');
    } catch (err) {
        logMsg('Reset failed: ' + err.message);
    } finally {
        elements.btnReset.disabled = false;
    }
}

async function actRun() {
    let actionData;
    try {
        actionData = JSON.parse(elements.actionInput.value);
    } catch (e) {
        alert('Invalid JSON in Action Submission');
        return;
    }
    
    elements.btnRun.disabled = true;
    logMsg('Executing action...');
    
    try {
        const res = await fetch('/step', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(actionData)
        });
        const data = await res.json();
        
        // Update flags
        const flagsHtml = (actionData.flags || []).map(f => 
            `<div class="flag-item severity-${f.severity || 'low'}">
                <span>${f.title}</span>
                <span>[${f.clause_reference}]</span>
            </div>`
        ).join('');
        
        if (flagsHtml) {
            elements.flagsContainer.innerHTML = flagsHtml;
        }
        
        // Update stats
        const reward = data.reward || 0;
        const currentScore = parseFloat(elements.statScore.textContent);
        const newScore = currentScore + reward;
        elements.statScore.textContent = newScore.toFixed(2);
        
        const deltaStr = reward >= 0 ? `+${reward.toFixed(2)}` : reward.toFixed(2);
        elements.statDelta.textContent = deltaStr;
        elements.statDelta.style.color = reward >= 0 ? 'var(--positive)' : 'var(--alert)';
        
        updateStateUI(data);
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
});
