/**
 * 足迹 (Footprint) - 虚拟旅行通关护照与海关印章册 (Digital Passport & Stamp Collection)
 * 赋予每一次打卡真实的海关入境戳与收藏仪式感，彻底摆脱单一记录与 AI 塑料感。
 */

const PassportModule = {
    // 经典城市三字码映射表
    cityCodes: {
        '北京': 'BJS', '上海': 'SHA', '广州': 'CAN', '深圳': 'SZX', '杭州': 'HGH',
        '成都': 'CTU', '重庆': 'CKG', '南京': 'NKG', '武汉': 'WUH', '西安': 'XIY',
        '厦门': 'XMN', '长沙': 'CSX', '青岛': 'TAO', '苏州': 'SZV', '三亚': 'SYX',
        '昆明': 'KMG', '丽江': 'LJG', '大理': 'DLU', '拉萨': 'LXA', '乌鲁木齐': 'URC',
        '哈尔滨': 'HRB', '香港': 'HKG', '澳门': 'MFM', '台北': 'TPE', '东京': 'TYO',
        '巴黎': 'PAR', '伦敦': 'LON', '纽约': 'NYC', '曼谷': 'BKK', '新加坡': 'SIN'
    },

    getCityCode(cityName) {
        for (const [k, v] of Object.entries(this.cityCodes)) {
            if (cityName.includes(k)) return v;
        }
        // 兜底提取拼音前三字母或随机三字码
        return (cityName.slice(0, 3).toUpperCase() || 'FPX');
    },

    // 提取所有打卡印章
    getStamps() {
        const records = (typeof state !== 'undefined' && state.records) ? state.records : [];
        const stampMap = new Map();

        records.forEach(r => {
            if (!r.location && !r.title) return;
            const fullLoc = r.location || r.title;
            const cityName = fullLoc.split('·')[0].split('市')[0].trim() || '旅行足迹';
            
            if (!stampMap.has(cityName)) {
                stampMap.set(cityName, {
                    city: cityName,
                    code: this.getCityCode(cityName),
                    firstDate: r.date || '2024-01-01',
                    lat: r.latitude ? Number(r.latitude).toFixed(2) : '30.27',
                    lng: r.longitude ? Number(r.longitude).toFixed(2) : '120.15',
                    mode: r.mode || 'travel',
                    count: 1
                });
            } else {
                stampMap.get(cityName).count++;
            }
        });

        return Array.from(stampMap.values());
    },

    open() {
        let modal = document.getElementById('modal-passport');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'modal-passport';
            modal.className = 'modal-overlay';
            document.body.appendChild(modal);
        }

        const stamps = this.getStamps();
        modal.innerHTML = `
            <div class="modal" style="max-width: 820px; width: 95vw; max-height: 90vh; padding: 0; background: #14171F; border: 2px solid #2A303C; border-radius: 16px; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.7);">
                <!-- 仿实体护照页顶栏 -->
                <div style="background: linear-gradient(180deg, #1C2230 0%, #161A24 100%); padding: 18px 24px; border-bottom: 2px solid #2B3345; display: flex; justify-content: space-between; align-items: center;">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <span style="font-size: 28px;">🛂</span>
                        <div>
                            <div style="font-size: 11px; font-weight: 700; letter-spacing: 0.2em; color: #D97706; text-transform: uppercase;">
                                PASSPORT VISAS & ENTRY STAMPS
                            </div>
                            <div style="font-size: 18px; font-weight: 800; color: #F1F5F9; letter-spacing: -0.01em;">
                                旅行者通关护照 · 签证印章册
                            </div>
                        </div>
                    </div>
                    <div style="display: flex; align-items: center; gap: 16px;">
                        <span style="font-size: 13px; color: #94A3B8; font-family: monospace;">已盖印章: <strong style="color: #F59E0B; font-size: 16px;">${stamps.length}</strong> 枚</span>
                        <button class="modal-close" onclick="PassportModule.close()" style="font-size: 20px;">✕</button>
                    </div>
                </div>

                <!-- 仿羊皮纸护照内页 (带细微噪点纸纹) -->
                <div style="
                    padding: 32px 28px;
                    background: #F4EFE6;
                    color: #1E293B;
                    max-height: calc(90vh - 90px);
                    overflow-y: auto;
                    box-shadow: inset 0 0 40px rgba(0,0,0,0.06);
                ">
                    <div style="display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 2px dashed #CBD5E1; padding-bottom: 12px; margin-bottom: 24px;">
                        <div>
                            <span style="font-size: 11px; font-family: monospace; letter-spacing: 0.15em; color: #64748B;">HOLDER'S TRAVEL LOG</span>
                            <div style="font-size: 16px; font-weight: 800; color: #0F172A;">城市探索入境章存根</div>
                        </div>
                        <div style="font-size: 11px; color: #94A3B8; font-family: monospace;">PAGE 01 · OFFICIAL ENTRY</div>
                    </div>

                    ${stamps.length === 0 ? `
                        <div style="text-align: center; padding: 60px 20px; color: #64748B;">
                            <div style="font-size: 40px; margin-bottom: 12px;">📭</div>
                            <div style="font-weight: 700; font-size: 16px; margin-bottom: 4px;">护照本尚无通关印章</div>
                            <div style="font-size: 13px;">录入你的第一条旅行或美食足迹，海关通关印章将自动盖上！</div>
                        </div>
                    ` : `
                        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 20px;">
                            ${stamps.map((s, idx) => `
                                <div style="
                                    border: 2px solid ${idx % 3 === 0 ? '#B91C1C' : (idx % 3 === 1 ? '#1D4ED8' : '#047857')};
                                    border-radius: ${idx % 2 === 0 ? '50%' : '14px'};
                                    width: 100%;
                                    aspect-ratio: 1 / 1;
                                    display: flex;
                                    flex-direction: column;
                                    align-items: center;
                                    justify-content: center;
                                    padding: 12px;
                                    text-align: center;
                                    background: rgba(255,255,255,0.4);
                                    transform: rotate(${(idx % 5 - 2) * 2.5}deg);
                                    box-shadow: 2px 3px 8px rgba(0,0,0,0.06);
                                    transition: transform 0.2s;
                                    user-select: none;
                                ">
                                    <div style="font-size: 9px; font-weight: 800; letter-spacing: 0.15em; color: #64748B; text-transform: uppercase;">
                                        IMMIGRATION · 入境
                                    </div>
                                    <div style="font-size: 26px; font-weight: 900; font-family: monospace; letter-spacing: 2px; color: ${idx % 3 === 0 ? '#B91C1C' : (idx % 3 === 1 ? '#1D4ED8' : '#047857')}; margin: 2px 0;">
                                        ${s.code}
                                    </div>
                                    <div style="font-size: 13px; font-weight: 800; color: #1E293B;">
                                        ${s.city}
                                    </div>
                                    <div style="font-size: 10px; font-family: monospace; color: #64748B; margin-top: 4px;">
                                        📅 ${s.firstDate}
                                    </div>
                                    <div style="font-size: 9px; font-family: monospace; color: #94A3B8; margin-top: 2px;">
                                        ${s.lat}°N, ${s.lng}°E
                                    </div>
                                    <div style="font-size: 9px; font-weight: 700; color: #F59E0B; margin-top: 4px; background: rgba(245,158,11,0.15); padding: 1px 6px; border-radius: 999px;">
                                        打卡 ${s.count} 次
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    `}
                </div>
            </div>
        `;
        modal.classList.add('active');
    },

    close() {
        const modal = document.getElementById('modal-passport');
        if (modal) modal.classList.remove('active');
    }
};

window.PassportModule = PassportModule;
