/**
 * 足迹 (Footprint) - 统一 API 与智能脱机/本地伪应用双模引擎 (Smart Dual-Mode Engine)
 * - 云端后端存在时：自动走 RESTful API，双向云同步；
 * - 无后端/未配置/双击直接打开时：无缝降级为 100% 纯本地桌面伪应用，所有数据与照片均持久化存储于本机浏览器！
 */

function getApiBase() {
    const config = getConfig();
    if (config.apiBase) return config.apiBase.replace(/\/$/, '');
    return location.protocol === 'file:' ? 'http://localhost:5000' : '';
}

function apiUrl(path) {
    return `${getApiBase()}${path}`;
}

function resolveAssetUrl(url) {
    if (!url || /^(data:|blob:)/.test(url)) return url;
    const base = getApiBase();
    const isLocalUpload = url.startsWith('/uploads/') || (base && url.startsWith(`${base}/uploads/`));
    const resolved = (base && url.startsWith('/')) ? `${base}${url}` : url;
    // 严格安全策略：仅使用受限的短期 Media Token，坚决不回退主登录凭据 JWT 到图片 URL
    const tokenToUse = (typeof _cachedMediaToken !== 'undefined' && _cachedMediaToken) || null;
    if (isLocalUpload && tokenToUse) {
        const sep = resolved.includes('?') ? '&' : '?';
        return `${resolved}${sep}token=${encodeURIComponent(tokenToUse)}`;
    }
    return resolved;
}

function getAuthHeaders() {
    const headers = {};
    if (authState.token) {
        headers['Authorization'] = `Bearer ${authState.token}`;
    }
    return headers;
}

// 更新界面上的连接状态指示器
function updateConnectionBadge(isCloud) {
    const badge = document.getElementById('connection-status-badge');
    if (badge) {
        if (isCloud) {
            badge.innerHTML = '<span>🟢</span><span>云端已连接</span>';
            badge.style.color = '#10B981';
            badge.title = '后端服务正常运行，数据已多端同步';
        } else {
            badge.innerHTML = '<span>🍃</span><span>本地免装模式</span>';
            badge.style.color = '#F59E0B';
            badge.title = '无需任何后端服务，数据与照片 100% 安全保存在本机浏览器';
        }
    }
}

// 纯本地离线模拟服务 (Zero-Backend Mock Service)
const LocalFallbackEngine = {
    handle(path, options = {}) {
        const method = (options.method || 'GET').toUpperCase();
        const body = options.body ? (typeof options.body === 'string' ? JSON.parse(options.body) : options.body) : {};

        // 1. Records CRUD
        if (path === '/api/records') {
            const list = JSON.parse(localStorage.getItem('footprint_data') || '[]');
            if (method === 'GET') {
                return list;
            }
            if (method === 'POST') {
                const item = { id: 'local_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6), ...body };
                list.unshift(item);
                localStorage.setItem('footprint_data', JSON.stringify(list));
                return item;
            }
            if (method === 'DELETE') {
                localStorage.removeItem('footprint_data');
                return { success: true, message: '本地数据已清空' };
            }
        }

        if (path.startsWith('/api/records/')) {
            const id = path.replace('/api/records/', '');
            const list = JSON.parse(localStorage.getItem('footprint_data') || '[]');
            if (method === 'PUT') {
                const idx = list.findIndex(r => r.id === id);
                if (idx >= 0) {
                    list[idx] = { ...list[idx], ...body, id };
                    localStorage.setItem('footprint_data', JSON.stringify(list));
                    return list[idx];
                }
                return { id, ...body };
            }
            if (method === 'DELETE') {
                const filtered = list.filter(r => r.id !== id);
                localStorage.setItem('footprint_data', JSON.stringify(filtered));
                return { success: true };
            }
        }

        // 2. Config
        if (path === '/api/config') {
            if (method === 'GET') {
                return JSON.parse(localStorage.getItem('footprint_config') || '{}');
            }
            if (method === 'POST') {
                const existing = JSON.parse(localStorage.getItem('footprint_config') || '{}');
                const merged = { ...existing, ...body };
                localStorage.setItem('footprint_config', JSON.stringify(merged));
                return { success: true, config: merged };
            }
        }

        // 3. Features (扩展特性)
        if (path === '/api/features') {
            const features = JSON.parse(localStorage.getItem('footprint_features') || '{}');
            return { features, owner_id: 'local_user' };
        }

        if (path.startsWith('/api/features/')) {
            const key = path.replace('/api/features/', '');
            const features = JSON.parse(localStorage.getItem('footprint_features') || '{}');
            if (method === 'GET') {
                return { feature_key: key, data: features[key] || [] };
            }
            if (method === 'PUT' || method === 'POST') {
                const data = body.data !== undefined ? body.data : body;
                features[key] = data;
                localStorage.setItem('footprint_features', JSON.stringify(features));
                return { success: true, feature_key: key, count: Array.isArray(data) ? data.length : 1 };
            }
            if (method === 'DELETE') {
                delete features[key];
                localStorage.setItem('footprint_features', JSON.stringify(features));
                return { success: true };
            }
        }

        // 4. Couple Status
        if (path === '/api/couple/status') {
            const config = JSON.parse(localStorage.getItem('footprint_config') || '{}');
            return {
                paired: !!config.coupleMode,
                couple_space_id: config.coupleMode ? 'local_couple_space' : null,
                partner: config.coupleMode ? { id: 'partner_local', username: config.partnerName || '伴侣' } : null
            };
        }

        // 5. Geocode Reverse Fallback
        if (path.startsWith('/api/geocode/reverse') || path.startsWith('/api/reverse-geocode')) {
            const params = new URLSearchParams(path.split('?')[1] || '');
            const lat = Number(params.get('lat') || 0).toFixed(4);
            const lng = Number(params.get('lng') || 0).toFixed(4);
            return { address: `地理位置 (${lat}, ${lng})` };
        }

        return {};
    }
};

async function apiFetch(path, options = {}) {
    // 若已确认后端不可用或直接 file: 打开未配置后端，直接走极致本地模拟
    if (state.apiAvailable === false && !options._forceCloud) {
        try {
            return LocalFallbackEngine.handle(path, options);
        } catch (e) {
            console.warn('Local fallback error:', e);
        }
    }

    let response;
    try {
        const authHeaders = getAuthHeaders();
        const mergedHeaders = { ...(authHeaders || {}), ...(options.headers || {}) };
        response = await fetch(apiUrl(path), { ...options, headers: mergedHeaders });
    } catch (networkErr) {
        // 仅在真实网络通信异常时判定为后端未连接，进入本地引擎
        state.apiAvailable = false;
        updateConnectionBadge(false);
        console.log(`[Footprint] 后端未连接或网络离线 (${networkErr.message})，已切换到纯本地脱机引擎: ${path}`);
        return LocalFallbackEngine.handle(path, options);
    }

    // 收到 HTTP 响应说明后端存活
    state.apiAvailable = true;
    updateConnectionBadge(true);

    let data = null;
    try { data = await response.json(); } catch { data = null; }

    if (!response.ok) {
        const err = new Error(data?.error || `HTTP ${response.status}`);
        err.status = response.status;
        err.data = data;
        throw err;
    }

    return data;
}

// 智能图片处理：优先云端，离线时转为本地存储
async function uploadImageFile(file) {
    if (state.apiAvailable !== false) {
        try {
            const formData = new FormData();
            formData.append('file', file);
            const authHeaders = getAuthHeaders();
            const resp = await fetch(apiUrl('/api/upload'), {
                method: 'POST',
                headers: authHeaders,
                body: formData
            });
            const data = await resp.json().catch(() => ({}));
            if (resp.ok && data.url) {
                return data.url;
            }
            if (resp.status === 401) {
                throw new Error('登录已过期，请重新登录后上传');
            }
            if (!resp.ok) {
                throw new Error(data.error || `上传失败 (HTTP ${resp.status})`);
            }
        } catch (e) {
            if (e.message && (e.message.includes('401') || e.message.includes('登录') || e.message.includes('上传失败'))) {
                throw e;
            }
            console.log('云端上传不可用，正在转为本地存储...');
        }
    }

    // 本地伪应用模式：优先调用 ImageCompressor 压缩，防止大图撑爆存储
    if (typeof window !== 'undefined' && window.ImageCompressor) {
        const comp = await window.ImageCompressor.compressImageFile(file);
        return comp.dataUrl;
    }

    return new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload = (e) => {
            resolve(e.target.result);
        };
        reader.readAsDataURL(file);
    });
}
