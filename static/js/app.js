/**
 * 🎨 Premium Dashboard - Main Application Logic
 * Handles UI interactions, API calls, and real-time updates
 */

// Global State
const state = {
  user: USER_DATA || {},
  tasks: [],
  currentTask: null,
  loading: false
};

// DOM Elements
const $ = (id) => document.getElementById(id);
const els = {
  points: $('pointsDisplay'),
  usd: $('usdDisplay'),
  tasks: $('tasksDisplay'),
  pending: $('pendingDisplay'),
  tasksContainer: $('tasksContainer'),
  taskCount: $('taskCount'),
  toast: $('toast'),
  toastMsg: $('toastMessage'),
  toastSub: $('toastSub'),
  toastIcon: $('toastIcon'),
  modal: $('submitModal'),
  modalTitle: $('modalTitle'),
  modalReqs: $('modalRequirements'),
  screenshotUrl: $('screenshotUrl'),
  proofText: $('proofText'),
  submitBtn: $('submitBtn'),
  notifBtn: $('notifBtn'),
  notifBadge: $('notifBadge'),
  notifModal: $('notifModal'),
  notifList: $('notifList'),
  referralLink: $('referralLink'),
  totalReferrals: $('totalReferrals'),
  bonusEarned: $('bonusEarned'),
  withdrawBalance: $('withdrawBalance'),
  withdrawBtn: $('withdrawBtn')
};

// ─────────────────────────────────────────────────────────────────────
// 🚀 Initialization
// ─────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
  initNavigation();
  initNotifications();
  
  // Load initial data
  await Promise.all([
    loadUserData(),
    loadTasks()
  ]);
  
  // Setup real-time listeners
  setupRealtimeUpdates();
  
  // Handle URL params for deep linking
  handleDeepLink();
  
  // Show welcome toast for new users
  if (!localStorage.getItem('welcomed_' + state.user.telegram_id)) {
    showToast('🎉 Welcome!', 'Start earning by completing tasks below', '✨');
    localStorage.setItem('welcomed_' + state.user.telegram_id, 'true');
  }
});

function initNavigation() {
  // Bottom nav buttons
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const section = e.currentTarget.dataset.section;
      navigateTo(section);
    });
  });
  
  // Initial section from URL
  const section = INITIAL_DATA?.section || 'home';
  navigateTo(section);
}

function navigateTo(section) {
  // Update active nav button
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.section === section);
  });
  
  // Show/hide sections
  ['home', 'tasks', 'referral', 'withdraw'].forEach(s => {
    const el = $(s + 'Section');
    if (el) el.classList.toggle('hidden', s !== section && s !== 'home');
  });
  
  // Special handling
  if (section === 'referral') loadReferralStats();
  if (section === 'withdraw') updateWithdrawUI();
  
  // Telegram Haptic Feedback
  if (window.Telegram?.WebApp?.HapticFeedback) {
    window.Telegram.WebApp.HapticFeedback.impactOccurred('light');
  }
}

// ─────────────────────────────────────────────────────────────────────
// 📊 Data Loading
// ─────────────────────────────────────────────────────────────────────

async function loadUserData() {
  try {
    const res = await fetch('/api/user', {
      headers: { 'X-User-ID': state.user.telegram_id }
    });
    const { success, data, error } = await res.json();
    
    if (success && data) {
      state.user = { ...state.user, ...data };
      updateStatsUI();
    } else {
      console.error('Failed to load user:', error);
    }
  } catch (err) {
    console.error('Load user error:', err);
  }
}

async function loadTasks() {
  try {
    els.tasksContainer.innerHTML = '<div class="skeleton h-20 rounded-xl"></div>'.repeat(3);
    
    const res = await fetch('/api/tasks', {
      headers: { 'X-User-ID': state.user.telegram_id }
    });
    const { success, data, error } = await res.json();
    
    if (success && data?.tasks) {
      state.tasks = data.tasks;
      renderTasks();
    } else {
      els.tasksContainer.innerHTML = '<p class="text-center text-gray-400 py-4">Failed to load tasks</p>';
    }
  } catch (err) {
    console.error('Load tasks error:', err);
    els.tasksContainer.innerHTML = '<p class="text-center text-danger py-4">Connection error</p>';
  }
}

function updateStatsUI() {
  // Animate number changes
  animateValue(els.points, parseInt(els.points.textContent) || 0, state.user.points || 0, 400);
  els.usd.textContent = `$${((state.user.points || 0) / APP_CONFIG.points_per_dollar).toFixed(2)}`;
  els.tasks.textContent = state.user.tasks_completed || 0;
  els.pending.textContent = Object.keys(state.user.pending_submissions || {}).length;
  
  // Update withdraw button state
  if (els.withdrawBtn) {
    const canWithdraw = (state.user.points || 0) >= APP_CONFIG.points_per_dollar;
    els.withdrawBtn.disabled = !canWithdraw;
    els.withdrawBtn.classList.toggle('opacity-50', !canWithdraw);
  }
}

function animateValue(el, start, end, duration) {
  let startTimestamp = null;
  const step = (timestamp) => {
    if (!startTimestamp) startTimestamp = timestamp;
    const progress = Math.min((timestamp - startTimestamp) / duration, 1);
    const value = Math.floor(progress * (end - start) + start);
    el.textContent = value.toLocaleString();
    if (progress < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

function renderTasks() {
  if (!state.tasks.length) {
    els.tasksContainer.innerHTML = '<p class="text-center text-gray-400 py-4">No tasks available</p>';
    els.taskCount.textContent = '0';
    return;
  }
  
  els.taskCount.textContent = `${state.tasks.length} tasks`;
  
  els.tasksContainer.innerHTML = state.tasks.map(task => `
    <div class="task-card glass rounded-xl p-4 flex items-center gap-4 ${task.completed ? 'completed' : ''}" 
         onclick="${task.completed ? '' : `openTaskModal('${task.id}')`}">
      <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-500/20 to-purple-600/20 flex items-center justify-center text-2xl flex-shrink-0">
        ${task.icon}
      </div>
      <div class="flex-1 min-w-0">
        <h4 class="font-medium truncate">${task.title}</h4>
        <p class="text-xs text-gray-400 truncate">${task.description}</p>
        <div class="flex items-center gap-2 mt-1">
          <span class="text-xs font-medium text-success">+${task.points} pts</span>
          ${task.completed ? '<span class="text-xs text-gray-500">✓ Completed</span>' : ''}
        </div>
      </div>
      <button class="glass px-4 py-2 rounded-lg text-sm font-medium ${task.completed ? 'text-gray-500' : 'text-primary-400 hover:text-primary-300'}">
        ${task.completed ? 'Done' : 'Start'}
      </button>
    </div>
  `).join('');
}

// ─────────────────────────────────────────────────────────────────────
// 🎯 Task Interactions
// ─────────────────────────────────────────────────────────────────────

async function watchAd() {
  if (state.loading) return;
  
  state.loading = true;
  const btn = event.currentTarget;
  const originalText = btn.innerHTML;
  
  try {
    btn.disabled = true;
    btn.innerHTML = '<span class="animate-pulse">⏳ Watching...</span>';
    
    // Open ad in new tab
    window.open(APP_CONFIG.ad_link, '_blank');
    
    // Wait 30 seconds (simulated ad view)
    await new Promise(resolve => setTimeout(resolve, 30000));
    
    // Claim points
    const res = await fetch('/api/earn/ad', {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'X-User-ID': state.user.telegram_id 
      },
      body: JSON.stringify({ user_id: state.user.telegram_id })
    });
    
    const { success, data, error } = await res.json();
    
    if (success) {
      showToast('🎉 Points Added!', `+${data.points_added} points to your balance`, '✨');
      await loadUserData();
    } else {
      showToast('⚠️ Claim Failed', error || 'Please try again', '⚠️');
    }
    
  } catch (err) {
    console.error('Ad watch error:', err);
    showToast('❌ Error', 'Connection issue. Try again.', '⚠️');
  } finally {
    state.loading = false;
    btn.disabled = false;
    btn.innerHTML = originalText;
  }
}

function openTaskModal(taskId) {
  const task = state.tasks.find(t => t.id === taskId);
  if (!task || task.type !== 'verification') return;
  
  state.currentTask = task;
  els.modalTitle.textContent = task.title;
  
  // Render requirements
  if (task.requirements) {
    els.modalReqs.innerHTML = `
      <p class="text-gray-300"><strong>📝 Instructions:</strong><br>${task.requirements.instruction}</p>
      <div class="mt-2">
        <p class="text-gray-400 text-xs"><strong>✅ What we check:</strong></p>
        <ul class="text-xs text-gray-400 mt-1 space-y-1">
          ${task.requirements.expected_elements.map(el => `<li>• ${el}</li>`).join('')}
        </ul>
      </div>
      ${task.requirements.proof_text_hint ? `<p class="text-xs text-gray-500 mt-2">📝 <em>${task.requirements.proof_text_hint}</em></p>` : ''}
    `;
  }
  
  // Reset form
  els.screenshotUrl.value = '';
  els.proofText.value = '';
  els.submitBtn.disabled = false;
  
  // Show modal
  els.modal.classList.add('active');
  
  // Telegram Haptic
  if (window.Telegram?.WebApp?.HapticFeedback) {
    window.Telegram.WebApp.HapticFeedback.impactOccurred('medium');
  }
}

function closeModal() {
  els.modal.classList.remove('active');
  state.currentTask = null;
}

async function submitTask() {
  const screenshotUrl = els.screenshotUrl.value.trim();
  const proofText = els.proofText.value.trim();
  
  if (!screenshotUrl) {
    showToast('⚠️ Required', 'Please enter screenshot URL', '⚠️');
    els.screenshotUrl.focus();
    return;
  }
  
  if (!screenshotUrl.match(/^https?:\/\/.+\.(jpg|jpeg|png|webp)/i)) {
    showToast('⚠️ Invalid URL', 'Must be direct image link (.jpg, .png, etc.)', '⚠️');
    return;
  }
  
  els.submitBtn.disabled = true;
  els.submitBtn.innerHTML = '<span class="animate-pulse">⏳ Submitting...</span>';
  
  try {
    const res = await fetch('/api/submit/task', {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'X-User-ID': state.user.telegram_id 
      },
      body: JSON.stringify({
        task_type: state.currentTask.id,
        screenshot_url: screenshotUrl,
        proof_text: proofText
      })
    });
    
    const { success, data, error } = await res.json();
    
    if (success) {
      showToast('✅ Submitted!', data.message || 'Awaiting review (~24h)', '🎉');
      closeModal();
      await loadUserData();
      await loadTasks();
    } else {
      showToast('❌ Submission Failed', error || 'Please try again', '⚠️');
    }
    
  } catch (err) {
    console.error('Submit error:', err);
    showToast('❌ Error', 'Connection issue. Try again.', '⚠️');
  } finally {
    els.submitBtn.disabled = false;
    els.submitBtn.textContent = 'Submit for Review';
  }
}

// ─────────────────────────────────────────────────────────────────────
// 👥 Referral System
// ─────────────────────────────────────────────────────────────────────

async function loadReferralStats() {
  try {
    const res = await fetch('/api/referral/stats', {
      headers: { 'X-User-ID': state.user.telegram_id }
    });
    const { success, data } = await res.json();
    
    if (success && data) {
      els.referralLink.textContent = data.referral_link;
      els.totalReferrals.textContent = data.total_referrals;
      els.bonusEarned.textContent = `${data.total_bonus_earned} pts`;
    }
  } catch (err) {
    console.error('Referral stats error:', err);
  }
}

function showReferral() {
  navigateTo('referral');
  loadReferralStats();
}

function copyReferral() {
  const link = els.referralLink.textContent;
  navigator.clipboard.writeText(link).then(() => {
    showToast('🔗 Copied!', 'Referral link copied to clipboard', '✅');
    
    // Telegram share
    if (window.Telegram?.WebApp?.shareToStory) {
      window.Telegram.WebApp.shareToStory({
        text: `🎁 Join me on Ultimate Media Search! Earn points by completing simple tasks. Use my link: ${link}`
      });
    }
  });
}

// ─────────────────────────────────────────────────────────────────────
// 💰 Withdrawal
// ─────────────────────────────────────────────────────────────────────

function updateWithdrawUI() {
  const balance = state.user.points || 0;
  const minWithdraw = APP_CONFIG.points_per_dollar;
  
  els.withdrawBalance.textContent = `$${(balance / minWithdraw).toFixed(2)}`;
  
  if (els.withdrawBtn) {
    els.withdrawBtn.disabled = balance < minWithdraw;
    els.withdrawBtn.classList.toggle('opacity-50', balance < minWithdraw);
  }
}

async function requestWithdrawal() {
  const method = $('withdrawMethod').value;
  const details = $('withdrawDetails').value.trim();
  
  if (!method) {
    showToast('⚠️ Select Method', 'Choose a payment method first', '⚠️');
    return;
  }
  
  if (!details) {
    showToast('⚠️ Required', 'Enter your payment details', '⚠️');
    $('withdrawDetails').focus();
    return;
  }
  
  if (state.loading) return;
  state.loading = true;
  
  try {
    // In production, this would call a real withdrawal API
    // For demo, we simulate success
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    showToast('✅ Request Submitted!', 'Your withdrawal will be processed within 24-48 hours', '🎉');
    
    // Reset form
    $('withdrawMethod').value = '';
    $('withdrawDetails').value = '';
    
    // Log the request (in production, send to backend)
    console.log('Withdrawal request:', { method, details, amount: state.user.points });
    
  } catch (err) {
    console.error('Withdrawal error:', err);
    showToast('❌ Error', 'Failed to submit request', '⚠️');
  } finally {
    state.loading = false;
  }
}

// ─────────────────────────────────────────────────────────────────────
// 🔔 Notifications
// ─────────────────────────────────────────────────────────────────────

function initNotifications() {
  // Show badge if there are unread notifications
  const notifications = INITIAL_DATA?.notifications || [];
  const unread = notifications.filter(n => !n.read).length;
  
  if (unread > 0) {
    els.notifBadge.textContent = unread;
    els.notifBadge.classList.remove('hidden');
  }
  
  // Click handler
  els.notifBtn?.addEventListener('click', () => {
    renderNotifications();
    els.notifModal.classList.add('active');
  });
}

function renderNotifications() {
  const notifications = INITIAL_DATA?.notifications || [];
  
  if (!notifications.length) {
    els.notifList.innerHTML = '<p class="text-sm text-gray-400 text-center py-4">No notifications</p>';
    return;
  }
  
  els.notifList.innerHTML = notifications.map(note => `
    <div class="glass rounded-lg p-3 ${!note.read ? 'border-l-4 border-primary-500' : ''}">
      <div class="flex items-start gap-3">
        <span class="text-lg">${note.type === 'broadcast' ? '📢' : '🔔'}</span>
        <div class="flex-1 min-w-0">
          <p class="text-sm">${note.message}</p>
          <p class="text-xs text-gray-500 mt-1">${formatTime(note.sent_at)}</p>
        </div>
      </div>
    </div>
  `).join('');
  
  // Mark as read (in production, call API)
  notifications.forEach(n => n.read = true);
  els.notifBadge?.classList.add('hidden');
}

function closeNotifModal() {
  els.notifModal.classList.remove('active');
}

function formatTime(timestamp) {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now - date;
  
  if (diff < 60000) return 'Just now';
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return date.toLocaleDateString();
}

// ─────────────────────────────────────────────────────────────────────
// 🔄 Real-time Updates
// ─────────────────────────────────────────────────────────────────────

function setupRealtimeUpdates() {
  if (!state.user.telegram_id) return;
  
  // Listen for point updates
  db.ref(`users/${state.user.telegram_id}`).on('value', (snapshot) => {
    const data = snapshot.val();
    if (data && data.points !== state.user.points) {
      state.user = { ...state.user, ...data };
      updateStatsUI();
      showToast('💰 Balance Updated!', 'Your points have been updated', '✨');
    }
  });
  
  // Listen for new notifications
  db.ref(`users/${state.user.telegram_id}/notifications`).limitToLast(1).on('child_added', (snapshot) => {
    const note = snapshot.val();
    if (note && !note.read) {
      showToast('🔔 New Notification', note.message?.substring(0, 50) + '...', '📬');
      // Reload notifications
      loadUserData();
    }
  });
}

function refreshData() {
  showToast('🔄 Refreshing...', 'Updating your data', '⚡');
  Promise.all([loadUserData(), loadTasks()]).then(() => {
    showToast('✅ Updated!', 'All data refreshed', '✨');
  });
}

// ─────────────────────────────────────────────────────────────────────
// 🎨 UI Helpers
// ─────────────────────────────────────────────────────────────────────

function showToast(title, message, icon = '✅') {
  els.toastIcon.textContent = icon;
  els.toastMsg.textContent = title;
  els.toastSub.textContent = message;
  els.toast.classList.add('show');
  
  setTimeout(() => {
    els.toast.classList.remove('show');
  }, 4000);
  
  // Haptic feedback
  if (window.Telegram?.WebApp?.HapticFeedback) {
    window.Telegram.WebApp.HapticFeedback.notificationOccurred('success');
  }
}

function handleDeepLink() {
  const params = new URLSearchParams(window.location.search);
  const task = params.get('task');
  
  if (task && state.tasks.some(t => t.id === task)) {
    setTimeout(() => openTaskModal(task), 500);
  }
}

// Close modals on backdrop click
els.modal?.addEventListener('click', (e) => {
  if (e.target === els.modal) closeModal();
});

els.notifModal?.addEventListener('click', (e) => {
  if (e.target === els.notifModal) closeNotifModal();
});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    closeModal();
    closeNotifModal();
  }
});

// Prevent pull-to-refresh on mobile (optional)
document.addEventListener('touchmove', (e) => {
  if (e.target.closest('.modal') || e.target.closest('.overflow-y-auto')) {
    e.stopPropagation();
  }
}, { passive: false });
