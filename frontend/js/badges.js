/**
 * 足迹 (Footprint) - 旅行家里程碑成就勋章体系 (Traveler Badges & Milestones)
 * 提供持续探索正反馈与成就感，告别单一记录工具属性。
 */

const BadgesModule = {
    getBadges() {
        const records = (typeof state !== 'undefined' && state.records) ? state.records : [];
        const cities = new Set();
        const provinces = new Set();
        let foodCount = 0;
        let fiveStarCount = 0;
        let photoCount = 0;
        let coupleCount = 0;

        const allProvinces = [
            '北京', '天津', '河北', '山西', '内蒙古', '辽宁', '吉林', '黑龙江',
            '上海', '江苏', '浙江', '安徽', '福建', '江西', '山东', '河南',
            '湖北', '湖南', '广东', '广西', '海南', '重庆', '四川', '贵州',
            '云南', '西藏', '陕西', '甘肃', '青海', '宁夏', '新疆', '台湾', '香港', '澳门'
        ];

        records.forEach(r => {
            const loc = r.location || r.title || '';
            const city = loc.split('·')[0].split('市')[0].trim();
            if (city) cities.add(city);

            allProvinces.forEach(p => {
                if (loc.includes(p)) provinces.add(p);
            });

            if (r.mode === 'food') foodCount++;
            if (Number(r.rating) === 5) fiveStarCount++;
            if (r.images && r.images.length) photoCount += r.images.length;
            if (r.mode === 'love' || (r.tags && r.tags.includes('couple'))) coupleCount++;
        });

        const isCouplePaired = (window.CouplePair && window.CouplePair.status && window.CouplePair.status.paired);

        return [
            {
                id: 'novice',
                title: '初级漫游者',
                icon: '🌲',
                desc: '探索点亮 3 座不同的城市',
                current: cities.size,
                target: 3,
                unlocked: cities.size >= 3
            },
            {
                id: 'provinces',
                title: '山海拾遗人',
                icon: '🏔️',
                desc: '足迹覆盖 5 个省级行政区',
                current: provinces.size,
                target: 5,
                unlocked: provinces.size >= 5
            },
            {
                id: 'gourmet',
                title: '深夜食堂探索官',
                icon: '🍜',
                desc: '完成 5 家特色美食探店打卡',
                current: foodCount,
                target: 5,
                unlocked: foodCount >= 5
            },
            {
                id: 'fivestar',
                title: '挑剔寻味家',
                icon: '⭐',
                desc: '寻获并打卡 3 家 5 星满分美味',
                current: fiveStarCount,
                target: 3,
                unlocked: fiveStarCount >= 3
            },
            {
                id: 'shutter',
                title: '快门收藏家',
                icon: '📸',
                desc: '旅途与美食累计拍摄记录 15 张照片',
                current: photoCount,
                target: 15,
                unlocked: photoCount >= 15
            },
            {
                id: 'couple_lovers',
                title: '浪漫同游人',
                icon: '💑',
                desc: '开启双人空间配对或留下情侣回忆',
                current: isCouplePaired ? 1 : coupleCount,
                target: 1,
                unlocked: Boolean(isCouplePaired || coupleCount >= 1)
            },
            {
                id: 'conquest_master',
                title: '版图征服家',
                icon: '🗺️',
                desc: '宏大版图！涉足 10 个以上省份',
                current: provinces.size,
                target: 10,
                unlocked: provinces.size >= 10
            },
            {
                id: 'world_traveler',
                title: '百川归海旅行家',
                icon: '🧭',
                desc: '累计沉淀 20 条旅行与生活足迹',
                current: records.length,
                target: 20,
                unlocked: records.length >= 20
            }
        ];
    },

    open() {
        let modal = document.getElementById('modal-badges');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'modal-badges';
            modal.className = 'modal-overlay';
            document.body.appendChild(modal);
        }

        const badges = this.getBadges();
        const unlockedCount = badges.filter(b => b.unlocked).length;

        modal.innerHTML = `
            <div class="modal" style="max-width: 780px; width: 95vw; max-height: 90vh; padding: 0; background: #0E121A; border: 1px solid rgba(255,255,255,0.12); border-radius: 16px; overflow: hidden;">
                <!-- 顶栏 -->
                <div style="background: #141A26; padding: 20px 24px; border-bottom: 1px solid rgba(255,255,255,0.08); display: flex; justify-content: space-between; align-items: center;">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <span style="font-size: 28px;">🎖️</span>
                        <div>
                            <div style="font-size: 11px; font-weight: 700; letter-spacing: 0.15em; color: #F59E0B; text-transform: uppercase;">
                                EXPLORER MILESTONES & ACHIEVEMENTS
                            </div>
                            <div style="font-size: 18px; font-weight: 800; color: #F8FAFC;">
                                旅行家里程碑 · 成就勋章墙
                            </div>
                        </div>
                    </div>
                    <div style="display: flex; align-items: center; gap: 16px;">
                        <span style="font-size: 13px; color: #94A3B8; font-family: monospace;">已解封: <strong style="color: #10B981; font-size: 16px;">${unlockedCount} / ${badges.length}</strong></span>
                        <button class="modal-close" onclick="BadgesModule.close()" style="font-size: 20px;">✕</button>
                    </div>
                </div>

                <!-- 勋章网格展示 -->
                <div style="padding: 24px; max-height: calc(90vh - 85px); overflow-y: auto;">
                    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px;">
                        ${badges.map(b => `
                            <div style="
                                background: ${b.unlocked ? 'linear-gradient(135deg, rgba(245,158,11,0.08), rgba(16,185,129,0.06))' : 'rgba(255,255,255,0.02)'};
                                border: 1px solid ${b.unlocked ? 'rgba(245,158,11,0.4)' : 'rgba(255,255,255,0.06)'};
                                border-radius: 12px;
                                padding: 18px 16px;
                                text-align: center;
                                position: relative;
                                filter: ${b.unlocked ? 'none' : 'grayscale(0.85) opacity(0.6)'};
                                transition: all 0.25s;
                            ">
                                <div style="font-size: 38px; margin-bottom: 8px;">
                                    ${b.icon}
                                </div>
                                <div style="font-size: 15px; font-weight: 800; color: ${b.unlocked ? '#F59E0B' : '#94A3B8'}; margin-bottom: 4px;">
                                    ${b.title}
                                </div>
                                <div style="font-size: 12px; color: #64748B; margin-bottom: 12px; min-height: 32px; line-height: 1.4;">
                                    ${b.desc}
                                </div>

                                <!-- 进度条 -->
                                <div style="background: rgba(255,255,255,0.08); border-radius: 999px; height: 6px; overflow: hidden; margin-bottom: 6px;">
                                    <div style="
                                        background: ${b.unlocked ? '#10B981' : '#64748B'};
                                        width: ${Math.min(100, (b.current / b.target) * 100)}%;
                                        height: 100%;
                                    "></div>
                                </div>
                                <div style="font-size: 11px; font-family: monospace; color: #94A3B8; display: flex; justify-content: space-between;">
                                    <span>${b.unlocked ? '✅ 已达成' : '探索中'}</span>
                                    <span>${Math.min(b.target, b.current)} / ${b.target}</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;
        modal.classList.add('active');
    },

    close() {
        const modal = document.getElementById('modal-badges');
        if (modal) modal.classList.remove('active');
    }
};

window.BadgesModule = BadgesModule;
