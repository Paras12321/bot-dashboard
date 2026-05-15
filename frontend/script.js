/**
 * Bot Automation Dashboard — Frontend Logic
 */
const API = '/api';

// ===== TOAST =====
function showToast(message, type = 'info') {
    const c = document.getElementById('toastContainer'); if (!c) return;
    const t = document.createElement('div');
    const icons = { success: '✅', error: '❌', info: 'ℹ️' };
    t.className = `toast ${type}`;
    t.innerHTML = `<span>${icons[type]||'ℹ️'}</span><span class="toast-message">${message}</span><button class="toast-close" onclick="this.parentElement.remove()">×</button>`;
    c.appendChild(t); setTimeout(() => t.remove(), 4000);
}

// ===== API HELPERS =====
async function apiGet(ep) {
    try { const r = await fetch(API+ep); if(!r.ok) throw new Error(`HTTP ${r.status}`); return await r.json(); }
    catch(e) { console.error('GET '+ep, e); return null; }
}
async function apiPost(ep, data) {
    try {
        const r = await fetch(API+ep, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data) });
        const j = await r.json(); if(!r.ok) throw new Error(j.detail||`HTTP ${r.status}`); return j;
    } catch(e) { showToast('Error: '+e.message,'error'); return null; }
}
async function apiDelete(ep) {
    try { const r = await fetch(API+ep,{method:'DELETE'}); return r.ok || r.status===204; }
    catch(e) { showToast('Delete failed','error'); return false; }
}
async function apiPatch(ep) {
    try { const r = await fetch(API+ep,{method:'PATCH'}); if(!r.ok) throw new Error(); return await r.json(); }
    catch(e) { return null; }
}

// ===== SIDEBAR NAVIGATION =====
function showSection(section) {
    // Update active link
    document.querySelectorAll('.sidebar-link').forEach(l => l.classList.remove('active'));
    const link = document.querySelector(`.sidebar-link[data-section="${section}"]`);
    if (link) link.classList.add('active');

    // Show/hide sections
    const allSections = ['addbot','sendmsg','scheduler','autoreply','welcome','logs','botlist','profile'];
    const dashSections = ['addbot','sendmsg','scheduler','autoreply','welcome','logs'];

    if (section === 'dashboard') {
        // Show main dashboard panels
        document.getElementById('statsRow').style.display = '';
        dashSections.forEach(s => { const el = document.getElementById('sec-'+s); if(el) el.closest('.panel-row') ? el.closest('.panel-row').style.display='' : el.style.display=''; });
        document.querySelectorAll('.panel-row').forEach(r => r.style.display = '');
        document.getElementById('sec-botlist').style.display = 'none';
        document.getElementById('sec-profile').style.display = 'none';
    } else {
        document.getElementById('statsRow').style.display = 'none';
        document.querySelectorAll('.panel-row').forEach(r => r.style.display = 'none');
        document.getElementById('sec-botlist').style.display = 'none';
        document.getElementById('sec-profile').style.display = 'none';

        if (section === 'addbot') {
            // Show add bot + bot list
            showPanelRow('sec-addbot');
            document.getElementById('sec-botlist').style.display = '';
        } else if (section === 'profile') {
            document.getElementById('sec-profile').style.display = '';
        } else {
            showPanelRow('sec-'+section);
        }
    }
    // Close mobile sidebar
    document.getElementById('sidebar')?.classList.remove('open');
}

function showPanelRow(panelId) {
    const panel = document.getElementById(panelId);
    if (panel) {
        const row = panel.closest('.panel-row');
        if (row) row.style.display = '';
        else panel.style.display = '';
    }
}

function toggleSidebar() {
    document.getElementById('sidebar')?.classList.toggle('open');
}

function toggleTokenVis() {
    const input = document.getElementById('botToken');
    input.type = input.type === 'password' ? 'text' : 'password';
}

// ===== BOTS =====
let botsCache = [];

async function loadBots() {
    const bots = await apiGet('/bots/');
    if (!bots) return;
    botsCache = bots;
    renderBotTable(bots);
    populateBotSelects(bots);
    updateStats();
    // System status
    const dc = bots.filter(b => b.platform==='discord').length;
    const tg = bots.filter(b => b.platform==='telegram').length;
    setText('sysDiscord', dc);
    setText('sysTelegram', tg);
}

function renderBotTable(bots) {
    const tbody = document.getElementById('botTableBody'); if (!tbody) return;
    if (!bots.length) { tbody.innerHTML = '<tr><td colspan="6" class="empty-cell">No bots registered yet</td></tr>'; return; }
    tbody.innerHTML = bots.map(b => `<tr>
        <td><strong>${esc(b.name)}</strong></td>
        <td><span class="badge badge-${b.platform}">${b.platform==='discord'?'🎮':'✈️'} ${b.platform}</span></td>
        <td>${esc(b.role)}</td>
        <td><span class="badge ${b.is_active?'badge-active':'badge-inactive'}">${b.is_active?'● Active':'○ Inactive'}</span></td>
        <td>${fmtDate(b.created_at)}</td>
        <td><button class="btn btn-secondary btn-sm" onclick="toggleBot(${b.id})">${b.is_active?'Pause':'Start'}</button>
            <button class="btn btn-danger btn-sm" onclick="deleteBot(${b.id})">Delete</button></td>
    </tr>`).join('');
}

function populateBotSelects(bots) {
    const active = bots.filter(b => b.is_active);
    ['msgBot','arBot','schedBot'].forEach(id => {
        const el = document.getElementById(id); if(!el) return;
        el.innerHTML = '<option value="">Select bot</option>' + active.map(b => `<option value="${b.id}">${b.name} (${b.platform})</option>`).join('');
    });
    // Welcome only shows discord bots
    const welEl = document.getElementById('welBot');
    if (welEl) {
        const discordBots = active.filter(b => b.platform === 'discord');
        welEl.innerHTML = '<option value="">Select Discord bot</option>' + discordBots.map(b => `<option value="${b.id}">${b.name}</option>`).join('');
    }
}

async function toggleBot(id) {
    const r = await apiPatch(`/bots/${id}/toggle`);
    if (r) { showToast(`Bot ${r.is_active?'activated':'paused'}`, 'success'); loadBots(); }
}
async function deleteBot(id) {
    if (!confirm('Delete this bot and all its data?')) return;
    if (await apiDelete(`/bots/${id}`)) { showToast('Bot deleted','success'); loadBots(); }
}

// ===== TASKS =====
async function loadTasks() { updateStats(); }

// ===== LOGS =====
async function loadLogs() {
    const logs = await apiGet('/logs/?limit=10');
    if (!logs) return;
    const tbody = document.getElementById('logTableBody'); if (!tbody) return;
    if (!logs.length) { tbody.innerHTML = '<tr><td colspan="5" class="empty-cell">No logs yet</td></tr>'; return; }
    tbody.innerHTML = logs.map(log => {
        const bot = botsCache.find(b => b.id === log.bot_id);
        const platform = bot ? bot.platform : 'unknown';
        const statusClass = log.level === 'success' ? 'badge-success' : log.level === 'error' ? 'badge-failed' : 'badge-pending';
        return `<tr>
            <td>${fmtDate(log.timestamp)}</td>
            <td><span class="platform-icon ${platform}">${platform==='discord'?'D':'T'}</span></td>
            <td>${bot ? esc(bot.name) : 'Bot #'+(log.bot_id||'-')}</td>
            <td>${esc(log.message).substring(0,40)}</td>
            <td><span class="badge ${statusClass}">${capitalize(log.level)}</span></td>
        </tr>`;
    }).join('');
}

// ===== AUTO REPLY =====
async function loadAutoReplies() {
    const rules = await apiGet('/auto-reply/');
    if (!rules) return;
    const container = document.getElementById('autoReplyList'); if (!container) return;
    if (!rules.length) { container.innerHTML = ''; return; }
    container.innerHTML = rules.map(r => {
        const bot = botsCache.find(b => b.id === r.bot_id);
        return `<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 12px;background:rgba(255,255,255,.03);border-radius:6px;margin-bottom:6px;font-size:.82rem;">
            <div><strong>"${esc(r.trigger_keyword)}"</strong> → ${esc(r.response_text.substring(0,35))}
            <div style="font-size:.72rem;color:var(--text-muted);">${bot?bot.name:'Bot #'+r.bot_id}</div></div>
            <button class="btn btn-danger btn-sm" onclick="delAutoReply(${r.id})">×</button>
        </div>`;
    }).join('');
    setText('statAutoReply', rules.length);
}
async function delAutoReply(id) {
    if (await apiDelete(`/auto-reply/${id}`)) { showToast('Rule deleted','success'); loadAutoReplies(); }
}

// ===== STATS =====
async function updateStats() {
    const stats = await apiGet('/tasks/stats');
    if (stats) {
        animateNum('statMessages', stats.done);
        animateNum('statScheduled', stats.pending);
        setText('statMsgSub', `+${stats.done} total`);
        setText('statSchedSub', `${stats.pending} pending`);
        setText('sysPending', stats.pending);
    }
    const totalBots = botsCache.length;
    const dc = botsCache.filter(b => b.platform==='discord').length;
    const tg = botsCache.filter(b => b.platform==='telegram').length;
    animateNum('statBots', totalBots);
    setText('statBotsSub', `${dc} Discord \u2022 ${tg} Telegram`);
}

function animateNum(id, target) {
    const el = document.getElementById(id); if (!el) return;
    const start = parseInt(el.textContent)||0, dur = 500, t0 = performance.now();
    function tick(now) {
        const p = Math.min((now-t0)/dur,1), e = 1-Math.pow(1-p,3);
        el.textContent = Math.round(start+(target-start)*e);
        if (p<1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
}

// ===== INIT =====
document.addEventListener('DOMContentLoaded', () => {
    loadBots(); loadLogs(); loadAutoReplies();

    // Add Bot
    document.getElementById('addBotForm')?.addEventListener('submit', async e => {
        e.preventDefault();
        const data = { name: val('botName'), platform: val('botPlatform'), token: val('botToken'), role: 'general' };
        if (!data.name||!data.platform||!data.token) { showToast('Fill all fields','error'); return; }
        const r = await apiPost('/bots/', data);
        if (r) { showToast(r.name+' registered!','success'); e.target.reset(); loadBots(); }
    });

    // Send Message
    document.getElementById('sendMessageForm')?.addEventListener('submit', async e => {
        e.preventDefault();
        const data = { bot_id: +val('msgBot'), target_id: val('msgTarget'), message: val('msgContent') };
        if (!data.bot_id||!data.target_id||!data.message) { showToast('Fill all fields','error'); return; }
        const r = await apiPost('/tasks/send-message', data);
        if (r) { showToast('Message queued!','success'); e.target.reset(); loadLogs(); updateStats(); }
    });

    // Schedule Message
    document.getElementById('scheduleForm')?.addEventListener('submit', async e => {
        e.preventDefault();
        const data = { bot_id: +val('schedBot'), target_id: val('schedTarget'), message: val('schedMessage'), action: 'send_message' };
        if (!data.bot_id||!data.target_id||!data.message) { showToast('Fill all fields','error'); return; }
        const r = await apiPost('/tasks/', data);
        if (r) { showToast('Message scheduled!','success'); e.target.reset(); updateStats(); }
    });

    // Auto Reply
    document.getElementById('autoReplyForm')?.addEventListener('submit', async e => {
        e.preventDefault();
        const data = { bot_id: +val('arBot'), trigger_keyword: val('arKeyword'), response_text: val('arResponse'), match_type: 'contains' };
        if (!data.bot_id||!data.trigger_keyword||!data.response_text) { showToast('Fill all fields','error'); return; }
        const r = await apiPost('/auto-reply/', data);
        if (r) { showToast('Rule added!','success'); e.target.reset(); loadAutoReplies(); }
    });

    // Welcome Message
    document.getElementById('welcomeForm')?.addEventListener('submit', async e => {
        e.preventDefault();
        const data = { bot_id: +val('welBot'), channel_id: 'general', message_template: val('welMessage') };
        if (!data.bot_id||!data.message_template) { showToast('Fill all fields','error'); return; }
        const r = await apiPost('/welcome/', data);
        if (r) { showToast('Welcome message saved!','success'); e.target.reset(); }
    });

    // Auto refresh
    setInterval(() => { loadLogs(); updateStats(); }, 10000);
});

// ===== UTILS =====
function val(id) { const el=document.getElementById(id); return el?el.value.trim():''; }
function setText(id,v) { const el=document.getElementById(id); if(el) el.textContent=v; }
function esc(s) { if(!s) return ''; const d=document.createElement('div'); d.textContent=s; return d.innerHTML; }
function capitalize(s) { return s ? s.charAt(0).toUpperCase()+s.slice(1) : ''; }
function fmtDate(d) {
    if(!d) return '-';
    const dt = new Date(d);
    return dt.toLocaleDateString('en-IN',{day:'2-digit',month:'short',year:'numeric'}) + ', ' +
           dt.toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'});
}
