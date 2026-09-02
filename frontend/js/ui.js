/**
 * 足迹 (Footprint) - UI 渲染、动效与模态框模块
 */

function toast(msg) {
    let el = document.getElementById('toast');
    if (!el) {
        el = document.createElement('div');
        el.id = 'toast';
        el.className = 'toast';
        document.body.appendChild(el);
    }
    el.textContent = msg;
    el.classList.add('show');
    setTimeout(() => el.classList.remove('show'), 2800);
}

function openModal(id) {
    const el = document.getElementById(`modal-${id}`) || document.getElementById(id);
    if (el) el.classList.add('active');
}

function closeModal(id) {
    const el = document.getElementById(`modal-${id}`) || document.getElementById(id);
    if (el) el.classList.remove('active');
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    state.theme = next;
    localStorage.setItem('footprint_theme', next);
    const btn = document.getElementById('theme-btn');
    if (btn) btn.textContent = next === 'dark' ? '🌙' : '☀️';
}

function loadTheme() {
    const saved = localStorage.getItem('footprint_theme') || 'dark';
    document.documentElement.setAttribute('data-theme', saved);
    const btn = document.getElementById('theme-btn');
    if (btn) btn.textContent = saved === 'dark' ? '🌙' : '☀️';
}

function toggleLang() {
    const next = state.lang === 'zh' ? 'en' : 'zh';
    state.lang = next;
    localStorage.setItem('footprint_lang', next);
    applyLang();
}

function applyLang() {
    const isEn = state.lang === 'en';
    const langBtn = document.getElementById('lang-btn');
    if (langBtn) langBtn.textContent = isEn ? 'EN' : '🌐';
}

// 浪漫粒子礼花动效 (支持情侣心愿达成与纪念日)
function confettiCelebration(isLoveTheme = true) {
    if (typeof confetti !== 'function') return;
    if (isLoveTheme) {
        confetti({
            particleCount: 60,
            spread: 70,
            origin: { y: 0.65 },
            colors: ['#EC4899', '#F472B6', '#8B5CF6', '#F43F5E', '#FFFFFF']
        });
    } else {
        confetti({
            particleCount: 50,
            spread: 60,
            origin: { y: 0.7 }
        });
    }
}

// 渲染主流程
function render() {
    const filtered = getFilteredRecords();
    renderStats();
    renderGrid(filtered);
    if (window.renderMapMarkers) {
        window.renderMapMarkers(getLocatedRecords());
    }
}

function renderStats() {
    const totalEl = document.getElementById('stat-total');
    const locatedEl = document.getElementById('stat-located');
    const photosEl = document.getElementById('stat-photos');

    const total = state.records.length;
    const located = state.records.filter(r => r.latitude !== null && r.latitude !== undefined).length;
    const totalPhotos = state.records.reduce((sum, r) => sum + (r.images ? r.images.length : 0), 0);

    if (totalEl) totalEl.textContent = total;
    if (locatedEl) locatedEl.textContent = located;
    if (photosEl) photosEl.textContent = totalPhotos;
}

function renderGrid(records = []) {
    const grid = document.getElementById('record-grid');
    const emptyEl = document.getElementById('empty-state');
    if (!grid) return;

    if (!records.length) {
        grid.style.display = 'none';
        if (emptyEl) emptyEl.style.display = 'block';
        return;
    }

    grid.style.display = 'grid';
    if (emptyEl) emptyEl.style.display = 'none';

    grid.innerHTML = records.map((r, idx) => {
        const isCouple = !!(r.is_couple || r.mode === 'love');
        const tagClass = r.mode === 'food' ? 'tag-food' : (isCouple ? 'tag-love' : 'tag-travel');
        const tagLabel = r.mode === 'food' ? '🍜 美食' : (isCouple ? '💕 专属回忆' : '✈️ 旅行');
        const thumb = (r.images && r.images[0]) ? resolveAssetUrl(r.images[0]) : 'data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><rect fill=%22%23222%22 width=%22100%22 height=%22100%22/><text y=%2255%22 x=%2250%22 text-anchor=%22middle%22 font-size=%2222%22 fill=%22%23777%22>No Photo</text></svg>';

        const priceBadge = r.price ? `<span class="food-price-badge">¥${r.price}</span>` : '';
        const ratingBadge = r.rating ? `<span>⭐ ${r.rating}</span>` : '';

        return `
            <div class="photo-card" onclick="openRecordDetail('${r.id || idx}')">
                <span class="photo-card-tag ${tagClass}">${tagLabel}</span>
                <img src="${thumb}" alt="${r.title || ''}" loading="lazy">
                <div class="photo-card-body">
                    <div class="photo-card-title">${r.title || '无标题'}</div>
                    <div class="photo-card-meta">
                        <span>${r.date || ''}</span>
                        ${r.location ? `<span>📍 ${r.location}</span>` : ''}
                        ${ratingBadge}
                        ${priceBadge}
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// 情侣模式动态界面更新
function updateCoupleUI() {
    const pill = document.getElementById('couple-filter-pill');
    const banner = document.getElementById('together-banner');
    const tools = document.getElementById('couple-tools-section');
    const tag = document.getElementById('group-couple-tag');
    const loveHeader = document.getElementById('love-header');
    const logoIcon = document.getElementById('logo-icon');

    if (state.coupleMode) {
        document.body.classList.add('couple-mode-active');
        if (pill) pill.style.display = 'inline-flex';
        if (tools) tools.style.display = 'block';
        if (tag) tag.style.display = 'block';
        if (loveHeader) loveHeader.style.display = 'flex';
        if (logoIcon) logoIcon.style.display = 'none';
        updateTogetherBanner();
    } else {
        document.body.classList.remove('couple-mode-active');
        if (pill) pill.style.display = 'none';
        if (tools) tools.style.display = 'none';
        if (tag) tag.style.display = 'none';
        if (loveHeader) loveHeader.style.display = 'none';
        if (logoIcon) logoIcon.style.display = 'flex';
        if (banner) banner.style.display = 'none';
    }
}

function updateTogetherBanner() {
    const banner = document.getElementById('together-banner');
    if (!banner) return;

    if (!state.coupleMode) {
        banner.style.display = 'none';
        return;
    }

    banner.style.display = 'flex';
    const config = getConfig();
    const partnerName = config.partnerName;
    const labelEl = document.getElementById('together-label');
    if (labelEl) {
        labelEl.textContent = partnerName ? `与 ${partnerName} 在一起` : '我们已经在一起';
    }

    const days = getTogetherDays();
    if (days !== null) {
        const daysEl = document.getElementById('together-days');
        if (daysEl) daysEl.textContent = `第 ${days} 天`;
        checkAnniversaryCelebration(days);
    }
}

function checkAnniversaryCelebration(days) {
    const milestones = [100, 200, 365, 520, 730, 1000, 1314];
    if (milestones.includes(days)) {
        setTimeout(() => {
            confettiCelebration(true);
            toast(`🎉 恭喜！今天是相恋 ${days} 天纪念日！`);
        }, 1200);
    }
}
