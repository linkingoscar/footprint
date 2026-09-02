/**
 * 足迹 (Footprint) - “今天吃什么” 美食幸运大转盘 (Food Decision Wheel)
 * 解决情侣/单人出行世纪难题，基于已打卡足迹与经典菜系随机摇号，搭配礼花动效。
 */

const FoodWheel = {
    defaultCuisines: [
        { name: '🔥 热辣火锅', desc: '红汤沸腾，毛肚鸭肠七上八下' },
        { name: '🍣 精致日料', desc: '刺身厚切，鳗鱼饭与炙烤寿司' },
        { name: '🥩 炭火烤肉', desc: '滋滋作响，生菜包肉大快朵颐' },
        { name: '🌶️ 川湘小馆', desc: '麻辣下饭，干锅辣子鸡香气扑鼻' },
        { name: '☕ 咖啡甜品', desc: '巴斯克蛋糕与拿铁的惬意下午' },
        { name: '🍲 潮汕牛肉', desc: '鲜切吊龙，沙茶酱与牛骨清汤' },
        { name: '🍜 地道面食', desc: '热气腾腾，劲道爽滑的大碗面' },
        { name: '🦐 粤式早茶', desc: '水晶虾饺皇、豉汁蒸排骨' },
        { name: '🍕 披萨意面', desc: '拉丝芝士与意式浓郁肉酱' },
        { name: '🥗 减脂轻食', desc: '羽衣甘蓝、慢烤鸡胸与油醋汁' }
    ],

    isSpinning: false,

    // 获取当前候选名单（优先结合用户真实录入的美食记录）
    getCandidates() {
        const records = (typeof state !== 'undefined' && state.records) ? state.records : [];
        const foodRecords = records.filter(r => r.mode === 'food');

        const candidates = [];
        // 如果用户有高分美食记录，优先加入
        foodRecords.forEach(r => {
            candidates.push({
                name: r.title,
                desc: `${r.location || '已打卡探店'} · ${r.rating ? '⭐' + r.rating : '推荐'}`,
                id: r.id,
                isRecord: true
            });
        });

        // 融合经典菜系保证选项丰富度
        this.defaultCuisines.forEach(c => {
            if (!candidates.some(item => item.name.includes(c.name.slice(2)))) {
                candidates.push(c);
            }
        });

        return candidates.slice(0, 16);
    },

    open() {
        let modal = document.getElementById('modal-food-wheel');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'modal-food-wheel';
            modal.className = 'modal-overlay';
            document.body.appendChild(modal);
        }

        const candidates = this.getCandidates();
        modal.innerHTML = `
            <div class="modal" style="max-width: 480px; text-align: center;">
                <div class="modal-header">
                    <div class="modal-title" style="display:flex;align-items:center;gap:8px">
                        <span>🎲</span>
                        <span>今天吃什么？· 寻味轮盘</span>
                    </div>
                    <button class="modal-close" onclick="FoodWheel.close()">✕</button>
                </div>
                <div class="modal-body" style="padding: 28px 20px;">
                    <div style="font-size: 13px; color: var(--text-sec); margin-bottom: 20px;">
                        选择困难症终结者 · 结合你的探店足迹与精选菜系
                    </div>

                    <!-- 动态抽签卡片 -->
                    <div id="wheel-display-card" style="
                        background: linear-gradient(135deg, rgba(245, 158, 11, 0.12), rgba(239, 68, 68, 0.12));
                        border: 2px solid rgba(245, 158, 11, 0.4);
                        border-radius: var(--radius);
                        padding: 32px 16px;
                        margin-bottom: 24px;
                        transition: all 0.3s;
                        box-shadow: 0 10px 30px rgba(245, 158, 11, 0.1);
                    ">
                        <div id="wheel-result-name" style="font-size: 26px; font-weight: 800; color: #F59E0B; margin-bottom: 8px;">
                            准备就绪
                        </div>
                        <div id="wheel-result-desc" style="font-size: 14px; color: var(--text-muted);">
                            点击下方按钮开始摇号！
                        </div>
                    </div>

                    <!-- 按钮控制组 -->
                    <div style="display: flex; gap: 12px; justify-content: center;">
                        <button id="btn-spin-wheel" class="btn btn-primary" style="padding: 12px 32px; font-size: 15px; font-weight: 700; background: linear-gradient(135deg, #F59E0B, #EF4444);" onclick="FoodWheel.spin()">
                            🎰 立即摇号
                        </button>
                        <button class="btn btn-ghost" onclick="FoodWheel.close()">
                            稍后再选
                        </button>
                    </div>

                    <!-- 备选池标签流 -->
                    <div style="margin-top: 24px; text-align: left;">
                        <div style="font-size: 12px; font-weight: 600; color: var(--text-muted); margin-bottom: 8px;">
                            📋 当前候选池 (${candidates.length} 项):
                        </div>
                        <div style="display: flex; flex-wrap: wrap; gap: 6px; max-height: 100px; overflow-y: auto;">
                            ${candidates.map(c => `
                                <span style="font-size: 11px; padding: 3px 8px; background: var(--bg-elevated); border: 1px solid var(--border); border-radius: 999px;">
                                    ${c.name}
                                </span>
                            `).join('')}
                        </div>
                    </div>
                </div>
            </div>
        `;
        modal.classList.add('active');
    },

    close() {
        const modal = document.getElementById('modal-food-wheel');
        if (modal) modal.classList.remove('active');
    },

    spin() {
        if (this.isSpinning) return;
        this.isSpinning = true;

        const candidates = this.getCandidates();
        const displayCard = document.getElementById('wheel-display-card');
        const nameEl = document.getElementById('wheel-result-name');
        const descEl = document.getElementById('wheel-result-desc');
        const btn = document.getElementById('btn-spin-wheel');

        btn.disabled = true;
        btn.textContent = '🎲 挑选美味中...';

        let count = 0;
        const totalSpins = 25;
        let speed = 60;

        const rollStep = () => {
            const randomIndex = Math.floor(Math.random() * candidates.length);
            const current = candidates[randomIndex];
            nameEl.textContent = current.name;
            descEl.textContent = current.desc;

            count++;
            if (count < totalSpins) {
                speed += 12; // 逐渐减速
                setTimeout(rollStep, speed);
            } else {
                // 停稳！
                this.isSpinning = false;
                btn.disabled = false;
                btn.textContent = '🔄 再摇一次';

                // 礼花与高亮效果
                if (typeof confetti === 'function') {
                    confetti({
                        particleCount: 70,
                        spread: 80,
                        origin: { y: 0.6 },
                        colors: ['#F59E0B', '#EF4444', '#10B981', '#3B82F6']
                    });
                }
                displayCard.style.transform = 'scale(1.05)';
                setTimeout(() => { displayCard.style.transform = 'scale(1)'; }, 300);
                toast(`🎉 命中美味：${nameEl.textContent}！`);
            }
        };

        rollStep();
    }
};

window.FoodWheel = FoodWheel;
