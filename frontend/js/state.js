/**
 * 足迹 (Footprint) - 全局状态、配置与过滤器管理模块
 */

// 全局业务状态
const state = {
    mode: 'travel',               // 基础模式: 'travel' | 'food'
    footprintFilter: 'all',       // 筛选维度: 'all' | 'travel' | 'food' | 'love'
    records: JSON.parse(localStorage.getItem('footprint_data') || '[]'),
    imageMeta: [],
    markers: [],
    markerClusterGroup: null,
    editingId: null,
    editingIndex: null,
    tempLocation: null,
    theme: localStorage.getItem('footprint_theme') || 'dark',
    lang: localStorage.getItem('footprint_lang') || 'zh',
    apiAvailable: false,
    coupleMode: false,
    activeFilterSet: false
};

// 鉴权状态
const authState = {
    token: localStorage.getItem('footprint_token') || null,
    user: JSON.parse(localStorage.getItem('footprint_user') || 'null'),
    isAuthenticated() { return !!this.token; }
};

// 配置读写
function getConfig() {
    try {
        return JSON.parse(localStorage.getItem('footprint_config') || '{}');
    } catch {
        return {};
    }
}

function saveConfig(config) {
    localStorage.setItem('footprint_config', JSON.stringify(config));
}

async function syncBackendConfig(config) {
    if (!authState.token) return;
    try {
        await apiFetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
    } catch (e) {
        console.log('Sync backend config skipped:', e.message);
    }
}

async function loadConfigFromCloud() {
    if (!authState.token) return;
    try {
        const cloudConfig = await apiFetch('/api/config');
        if (cloudConfig) {
            const localConfig = getConfig();
            const merged = { ...localConfig, ...cloudConfig };
            saveConfig(merged);
            state.coupleMode = !!merged.coupleMode;
            updateCoupleUI();
            if (merged.layoutConfig) {
                applyLayoutConfig(merged.layoutConfig);
            }
        }
    } catch (e) {
        console.log('Config cloud sync unavailable:', e.message);
    }
}

function applyLayoutConfig(layout) {
    if (!layout) return;
    if (layout.siteTitle) {
        const titleEl = document.querySelector('.logo-text');
        if (titleEl) titleEl.textContent = layout.siteTitle;
        document.title = `${layout.siteTitle} · 记录旅行与美食`;
    }
    if (layout.logoEmoji) {
        const iconEl = document.getElementById('logo-icon');
        if (iconEl) iconEl.textContent = layout.logoEmoji;
    }
    if (layout.defaultFilter && !state.activeFilterSet) {
        if (layout.defaultFilter === 'love' && !state.coupleMode) {
            setFootprintFilter('all');
        } else {
            setFootprintFilter(layout.defaultFilter);
        }
        state.activeFilterSet = true;
    }
    if (layout.mapHeight) {
        const mapEl = document.getElementById('footprint-map');
        if (mapEl) mapEl.style.height = layout.mapHeight;
    }
    if (Array.isArray(layout.visibleFeatures)) {
        const featureButtons = document.querySelectorAll('.feature-pills-bar .feature-pill-btn');
        featureButtons.forEach(btn => {
            const clickAttr = btn.getAttribute('onclick') || '';
            const match = clickAttr.match(/handleFeature\('([^']+)'\)/);
            if (match) {
                const featKey = match[1];
                btn.style.display = layout.visibleFeatures.includes(featKey) ? '' : 'none';
            }
        });
    }
    if (layout.cardLayout === 'dense') {
        const gridEl = document.getElementById('record-grid');
        if (gridEl) gridEl.style.gridTemplateColumns = 'repeat(auto-fill, minmax(240px, 1fr))';
    }
}

async function loadFeaturesFromCloud() {
    if (!authState.token) return;
    try {
        const resp = await apiFetch('/api/features');
        if (resp && resp.features) {
            for (const [key, val] of Object.entries(resp.features)) {
                if (val !== undefined && val !== null) {
                    localStorage.setItem(key, JSON.stringify(val));
                }
            }
        }
    } catch (e) {
        console.log('Features cloud sync unavailable, using local:', e.message);
    }
}

async function syncFeatureToCloud(featureKey, data) {
    if (!authState.token) return;
    try {
        await apiFetch(`/api/features/${featureKey}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ data })
        });
    } catch (e) {
        console.warn(`Sync ${featureKey} to cloud failed:`, e.message);
    }
}

// 筛选逻辑：支持 全部(旅行+美食) | 仅旅行 | 仅美食 | 仅情侣
function getFilteredRecords() {
    const f = state.footprintFilter;
    if (f === 'travel') {
        return state.records.filter(r => r.mode === 'travel');
    }
    if (f === 'food') {
        return state.records.filter(r => r.mode === 'food');
    }
    if (f === 'love') {
        return state.records.filter(r => r.is_couple || r.mode === 'love');
    }
    // 默认 'all'：包含全部旅行与美食，未开启情侣模式时自动过滤非情侣
    return state.records;
}

function getLocatedRecords() {
    return getFilteredRecords().filter(r =>
        r.latitude !== null && r.latitude !== undefined &&
        r.longitude !== null && r.longitude !== undefined
    );
}

function setFootprintFilter(filterKey) {
    state.footprintFilter = filterKey;
    document.querySelectorAll('.mode-pill').forEach(pill => {
        pill.classList.toggle('active', pill.dataset.filter === filterKey);
    });
    render();
    if (window.renderMapMarkers) {
        window.renderMapMarkers(getLocatedRecords());
    }
}

// 相恋天数计算
function getTogetherDays() {
    const config = getConfig();
    let startDate = config.togetherDate;
    if (!startDate) {
        const firstRecord = state.records.find(r => r.date);
        if (firstRecord) startDate = firstRecord.date;
    }
    if (!startDate) return null;
    const start = new Date(startDate);
    const now = new Date();
    const diff = Math.floor((now - start) / (1000 * 60 * 60 * 24));
    return diff >= 0 ? diff : 0;
}
