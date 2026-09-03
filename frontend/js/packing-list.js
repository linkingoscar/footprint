/**
 * 足迹 (Footprint) - 行前行李准备清单模块 (Packing Checklist)
 * 出游前全流程防遗漏清单，支持分类勾选、一键复位与自定义扩充。
 */

const PackingListModule = {
    defaultCategories: [
        {
            name: '🪪 证件资料',
            items: [
                { id: 'p_id', name: '身份证 / 户口本', checked: true },
                { id: 'p_passport', name: '护照 / 港澳通行证', checked: false },
                { id: 'p_driver', name: '驾驶证 (租车自驾必备)', checked: false },
                { id: 'p_cash', name: '适量现金 / 备用银行卡', checked: true }
            ]
        },
        {
            name: '📱 数码装备',
            items: [
                { id: 'd_power', name: '大容量充电宝 (已充满)', checked: true },
                { id: 'd_cables', name: '多合一快充线 / 充电头', checked: true },
                { id: 'd_earphone', name: '降噪耳机 (飞机高铁神器)', checked: false },
                { id: 'd_camera', name: '相机 / 备用储存卡', checked: false }
            ]
        },
        {
            name: '👕 衣物洗护',
            items: [
                { id: 'c_clothes', name: '换洗衣物 / 贴身防寒保暖', checked: false },
                { id: 'c_disposable', name: '一次性内裤 / 压缩毛巾', checked: true },
                { id: 'c_shoes', name: '舒适暴走鞋 / 拖鞋', checked: false },
                { id: 'c_sunscreen', name: '防晒霜 / 墨镜 / 遮阳伞', checked: true },
                { id: 'c_toiletries', name: '便携洗漱分装套装', checked: false }
            ]
        },
        {
            name: '💊 应急常备',
            items: [
                { id: 'm_motion', name: '晕车 / 晕船贴', checked: false },
                { id: 'm_bandaid', name: '创可贴 / 碘伏棉棒', checked: true },
                { id: 'm_stomach', name: '肠胃消食片 / 止泻药', checked: true },
                { id: 'm_mosquito', name: '驱蚊喷雾 / 清凉油', checked: false }
            ]
        }
    ],

    getData() {
        try {
            const saved = localStorage.getItem('footprint_packing_list');
            if (saved) return JSON.parse(saved);
        } catch (e) {}
        return this.defaultCategories;
    },

    saveData(data) {
        localStorage.setItem('footprint_packing_list', JSON.stringify(data));
        if (typeof apiFetch === 'function') {
            apiFetch('/api/features/packing_list', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ data })
            }).catch(() => {});
        }
    },

    toggleItem(catIdx, itemIdx) {
        const data = this.getData();
        if (data[catIdx] && data[catIdx].items[itemIdx]) {
            data[catIdx].items[itemIdx].checked = !data[catIdx].items[itemIdx].checked;
            this.saveData(data);
            this.renderBody();
            if (this.calcProgress(data).isAllDone) {
                if (typeof confetti === 'function') {
                    confetti({ particleCount: 70, spread: 80, origin: { y: 0.6 } });
                }
                toast('🎉 行李全量齐备，随时准备出发！');
            }
        }
    },

    async resetAll() {
        const ok = (window.AppDialog) ? await AppDialog.confirm({
            title: '重置行前清单',
            message: '确定要清空所有已勾选项，开启下一次旅途准备吗？',
            confirmText: '重置清单'
        }) : confirm('确定要清空所有已勾选项，开启下一次旅途准备吗？');
        if (!ok) return;
        const data = this.getData();
        data.forEach(c => c.items.forEach(i => i.checked = false));
        this.saveData(data);
        this.renderBody();
        toast('已重置清单');
    },

    async addNewItem(catIdx) {
        const name = (window.AppDialog) ? await AppDialog.prompt({
            title: '新增行李物品',
            placeholder: '例如: 防晒霜 / 转换插头 / 护照',
            icon: '🎒',
            confirmText: '添加物品'
        }) : prompt('请输入新增行李物品名称:');
        if (!name || !name.trim()) return;
        const data = this.getData();
        data[catIdx].items.push({
            id: 'custom_' + Date.now(),
            name: name.trim(),
            checked: false
        });
        this.saveData(data);
        this.renderBody();
    },

    calcProgress(data) {
        let total = 0, checked = 0;
        data.forEach(c => {
            total += c.items.length;
            checked += c.items.filter(i => i.checked).length;
        });
        const percent = total ? Math.round((checked / total) * 100) : 0;
        return { total, checked, percent, isAllDone: total > 0 && checked === total };
    },

    open() {
        let modal = document.getElementById('modal-packing-list');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'modal-packing-list';
            modal.className = 'modal-overlay';
            document.body.appendChild(modal);
        }

        modal.innerHTML = `
            <div class="modal" style="max-width: 640px; width: 95vw; max-height: 90vh; display: flex; flex-direction: column;">
                <div class="modal-header">
                    <div class="modal-title" style="display:flex;align-items:center;gap:8px">
                        <span>🧳</span>
                        <span>行前行李准备清单 · 防漏利器</span>
                    </div>
                    <button class="modal-close" onclick="PackingListModule.close()">✕</button>
                </div>
                <div id="packing-list-body" class="modal-body" style="padding: 20px; overflow-y: auto;">
                    <!-- 动态生成清单 -->
                </div>
            </div>
        `;
        modal.classList.add('active');
        this.renderBody();
    },

    close() {
        const modal = document.getElementById('modal-packing-list');
        if (modal) modal.classList.remove('active');
    },

    renderBody() {
        const container = document.getElementById('packing-list-body');
        if (!container) return;
        const data = this.getData();
        const progress = this.calcProgress(data);

        container.innerHTML = `
            <!-- 准备进度环/条 -->
            <div style="background: var(--bg-elevated); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 16px; margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div style="font-weight: 700; font-size: 14px; color: var(--text);">
                        打包完成度：<strong style="color: #10B981; font-size: 18px;">${progress.percent}%</strong>
                    </div>
                    <div style="font-size: 12px; color: var(--text-muted);">
                        已备齐 ${progress.checked} / ${progress.total} 件
                    </div>
                </div>
                <div style="height: 8px; background: rgba(255,255,255,0.08); border-radius: 999px; overflow: hidden;">
                    <div style="height: 100%; width: ${progress.percent}%; background: linear-gradient(90deg, #10B981, #06B6D4); transition: width 0.3s;"></div>
                </div>
            </div>

            <!-- 分组渲染 -->
            <div style="display: flex; flex-direction: column; gap: 18px;">
                ${data.map((cat, cIdx) => `
                    <div style="background: var(--glass); border: 1px solid var(--border); border-radius: 12px; padding: 14px 16px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                            <div style="font-size: 14px; font-weight: 700; color: var(--text);">
                                ${cat.name}
                            </div>
                            <button class="btn btn-sm btn-ghost" style="font-size: 11px; padding: 2px 8px;" onclick="PackingListModule.addNewItem(${cIdx})">
                                ➕ 添加物品
                            </button>
                        </div>
                        <div style="display: flex; flex-direction: column; gap: 8px;">
                            ${cat.items.map((item, iIdx) => `
                                <label style="display: flex; align-items: center; gap: 10px; cursor: pointer; user-select: none; font-size: 13px; color: ${item.checked ? 'var(--text-muted)' : 'var(--text)'}; text-decoration: ${item.checked ? 'line-through' : 'none'};">
                                    <input type="checkbox" ${item.checked ? 'checked' : ''} onchange="PackingListModule.toggleItem(${cIdx}, ${iIdx})" style="width: 16px; height: 16px; accent-color: #10B981;">
                                    <span>${item.name}</span>
                                </label>
                            `).join('')}
                        </div>
                    </div>
                `).join('')}
            </div>

            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 24px; padding-top: 14px; border-top: 1px solid var(--border);">
                <button class="btn btn-sm btn-danger" onclick="PackingListModule.resetAll()">
                    🔄 重置清单 (准备下次出行)
                </button>
                <button class="btn btn-sm btn-primary" onclick="PackingListModule.close()">
                    完成退出
                </button>
            </div>
        `;
    }
};

window.PackingListModule = PackingListModule;
