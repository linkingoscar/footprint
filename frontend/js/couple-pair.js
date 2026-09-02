/**
 * 足迹 (Footprint) - 双人情侣空间协同绑定模块 (Couple Pairing Manager)
 */

const CouplePair = {
    status: {
        paired: false,
        couple_space_id: null,
        partner: null
    },

    async _fetch(path, options) {
        if (typeof apiFetch === 'function') return apiFetch(path, options);
        if (typeof api === 'function') return api(path, options);
        const token = localStorage.getItem('footprint_token');
        const headers = { 'Content-Type': 'application/json', ...(options?.headers || {}) };
        if (token) headers['Authorization'] = `Bearer ${token}`;
        const resp = await fetch(path, { ...options, headers });
        const data = await resp.json().catch(() => ({}));
        if (!resp.ok) throw new Error(data.error || `HTTP ${resp.status}`);
        return data;
    },

    async fetchStatus() {
        try {
            const data = await this._fetch('/api/couple/status');
            this.status = data || { paired: false };
            this.updateUI();
            return this.status;
        } catch (e) {
            console.warn('Fetch couple status failed:', e.message);
            return null;
        }
    },

    async generateInvite() {
        try {
            const data = await this._fetch('/api/couple/invite', { method: 'POST' });
            return data;
        } catch (e) {
            toast('生成失败: ' + e.message);
            throw e;
        }
    },

    async pair(code) {
        try {
            const data = await this._fetch('/api/couple/pair', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ invite_code: code })
            });
            if (typeof confetti === 'function') {
                confetti({
                    particleCount: 90,
                    spread: 90,
                    origin: { y: 0.6 },
                    colors: ['#EC4899', '#8B5CF6', '#F43F5E', '#FFFFFF']
                });
            }
            toast(data.message || '🎉 配对成功！');
            await this.fetchStatus();
            return data;
        } catch (e) {
            toast('绑定失败: ' + e.message);
            throw e;
        }
    },

    async unbind() {
        if (!confirm('确定要解除双人情侣空间绑定吗？解除后将恢复单人模式。')) return;
        try {
            await this._fetch('/api/couple/unbind', { method: 'POST' });
            toast('已解除绑定');
            await this.fetchStatus();
        } catch (e) {
            toast('解除失败: ' + e.message);
        }
    },

    updateUI() {
        const partnerNameEl = document.getElementById('couple-partner-badge');
        if (partnerNameEl) {
            if (this.status.paired && this.status.partner) {
                partnerNameEl.innerHTML = `<span>💕 与 ${this.status.partner.username} 协同共建中</span>`;
                partnerNameEl.style.display = 'inline-flex';
            } else {
                partnerNameEl.style.display = 'none';
            }
        }
    },

    // 渲染管理后台与设置页面的双人配对卡片
    renderCard(targetElId) {
        const container = document.getElementById(targetElId);
        if (!container) return;

        if (this.status.paired && this.status.partner) {
            container.innerHTML = `
                <div style="background: linear-gradient(135deg, rgba(236,72,153,0.12), rgba(139,92,246,0.12)); border: 1px solid rgba(236,72,153,0.3); border-radius: var(--radius-sm); padding: 18px; margin-top: 12px;">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                        <div style="display: flex; align-items: center; gap: 8px; font-weight: 700; color: #EC4899; font-size: 15px;">
                            <span>💑 双人浪漫空间已连通</span>
                        </div>
                        <button class="btn btn-sm btn-danger" onclick="CouplePair.unbind()">解除绑定</button>
                    </div>
                    <div style="font-size: 13px; color: var(--text-sec); margin-bottom: 6px;">
                        伴侣账号：<strong>${this.status.partner.username}</strong>
                    </div>
                    <div style="font-size: 12px; color: var(--text-muted);">
                        你们已共享同一个浪漫足迹空间，双方添加的恋爱手账、打卡点与 100 件事愿望将实时双向同步！
                    </div>
                </div>
            `;
        } else {
            container.innerHTML = `
                <div style="background: var(--bg-elevated); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 18px; margin-top: 12px;">
                    <div style="font-size: 14px; font-weight: 700; color: var(--text); margin-bottom: 6px; display: flex; align-items: center; gap: 6px;">
                        <span>💌 双人空间配对 (邀请另一半加入)</span>
                    </div>
                    <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 14px;">
                        告别单机！绑定后双方可共同维护足迹相册、勾选完成 100 件心愿、同屏看地图。
                    </div>
                    <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 12px;">
                        <button class="btn btn-sm btn-primary" onclick="CouplePair.handleGenerateCode()">
                            ✨ 生成我的配对码
                        </button>
                    </div>
                    <div id="couple-invite-display" style="display: none; padding: 10px; background: var(--glass); border: 1px dashed #EC4899; border-radius: 8px; margin-bottom: 12px; font-size: 13px;"></div>
                    <div style="display: flex; gap: 8px; align-items: center; max-width: 360px;">
                        <input type="text" id="input-couple-code" class="form-input" placeholder="输入伴侣的 6 位配对码" style="text-transform: uppercase;">
                        <button class="btn btn-sm btn-ghost" onclick="CouplePair.handlePairInput()">立即绑定</button>
                    </div>
                </div>
            `;
        }
    },

    async handleGenerateCode() {
        const res = await this.generateInvite();
        const display = document.getElementById('couple-invite-display');
        if (display && res.invite_code) {
            display.style.display = 'block';
            display.innerHTML = `
                <div style="color: #EC4899; font-weight: 700; font-size: 16px; margin-bottom: 4px;">
                    你的配对码: <span style="font-family: monospace; letter-spacing: 2px;">${res.invite_code}</span>
                </div>
                <div style="color: var(--text-muted); font-size: 11px;">
                    有效期 24 小时，将配对码发送给你的另一半在后台输入即可完成绑定！
                </div>
            `;
        }
    },

    async handlePairInput() {
        const input = document.getElementById('input-couple-code');
        const code = input ? input.value.trim() : '';
        if (!code) {
            toast('请输入配对码');
            return;
        }
        await this.pair(code);
        this.renderCard('couple-pair-card-container');
    }
};

window.CouplePair = CouplePair;
