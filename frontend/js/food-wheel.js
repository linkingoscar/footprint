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

    // 读取用户本地保存的自定义美味
    getCustomFoods() {
        try {
            return JSON.parse(localStorage.getItem('footprint_custom_foods') || '[]');
        } catch {
            return [];
        }
    },

    saveCustomFoods(list) {
        localStorage.setItem('footprint_custom_foods', JSON.stringify(list));
    },

    addCustomFood(name, desc) {
        if (!name || !name.trim()) return;
        const list = this.getCustomFoods();
        const trimmed = name.trim();
        if (list.some(item => (typeof item === 'string' ? item : item.name) === trimmed)) {
            toast('该美味已经在候选池里啦 ✨');
            return;
        }
        list.push({
            name: trimmed,
            desc: desc ? desc.trim() : '我的定制私房美味',
            isCustom: true
        });
        this.saveCustomFoods(list);
        toast(`✨ 已将「${trimmed}」加入寻味候选池！`);
        this.open();
    },

    addFromInput() {
        const input = document.getElementById('food-custom-input');
        if (!input) return;
        const val = input.value.trim();
        if (!val) {
            toast('请输入你想吃的美食名称');
            return;
        }
        this.addCustomFood(val);
    },

    removeCustomFood(index) {
        const list = this.getCustomFoods();
        if (index >= 0 && index < list.length) {
            const removed = list.splice(index, 1);
            this.saveCustomFoods(list);
            const itemName = removed[0].name || removed[0];
            toast(`已从轮盘移除「${itemName}」`);
            this.open();
        }
    },

    // 获取当前候选名单（优先结合用户自定义美味 + 真实录入的美食记录 + 经典菜系兜底）
    getCandidates() {
        const records = (typeof state !== 'undefined' && state.records) ? state.records : [];
        const foodRecords = records.filter(r => r.mode === 'food');

        const candidates = [];

        // 1. 用户自定义添加的专属美味（最高优先级）
        const customFoods = this.getCustomFoods();
        customFoods.forEach((c, idx) => {
            const name = typeof c === 'string' ? c : c.name;
            const desc = typeof c === 'string' ? '我的定制私房美味' : (c.desc || '我的定制私房美味');
            candidates.push({
                name: name.startsWith('⭐') ? name : `⭐ ${name}`,
                rawName: name,
                desc: desc,
                isCustom: true,
                customIndex: idx
            });
        });

        // 2. 如果用户有探店打卡记录，融合进转盘
        foodRecords.forEach(r => {
            if (!candidates.some(item => item.name.includes(r.title))) {
                candidates.push({
                    name: r.title,
                    desc: `${r.location || '已打卡探店'} · ${r.rating ? '⭐' + r.rating : '推荐'}`,
                    id: r.id,
                    isRecord: true
                });
            }
        });

        // 3. 融合经典菜系保证选项丰富度
        this.defaultCuisines.forEach(c => {
            if (!candidates.some(item => item.name.includes(c.name.slice(2)))) {
                candidates.push(c);
            }
        });

        return candidates.slice(0, 24);
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
        const customFoods = this.getCustomFoods();

        modal.innerHTML = `
            <div class="modal" style="max-width: 520px; text-align: center;">
                <div class="modal-header">
                    <div class="modal-title" style="display:flex;align-items:center;gap:8px">
                        <span>🎲</span>
                        <span>今天吃什么？· 寻味轮盘</span>
                    </div>
                    <button class="modal-close" onclick="FoodWheel.close()">✕</button>
                </div>
                <div class="modal-body" style="padding: 24px 20px;">
                    <div style="font-size: 13px; color: var(--text-sec); margin-bottom: 16px;">
                        选择困难症终结者 · 结合你的探店足迹、自定义美味与精选菜系
                    </div>

                    <!-- 动态抽签展示卡片 -->
                    <div id="wheel-display-card" style="
                        background: linear-gradient(135deg, rgba(245, 158, 11, 0.12), rgba(239, 68, 68, 0.12));
                        border: 2px solid rgba(245, 158, 11, 0.4);
                        border-radius: var(--radius);
                        padding: 26px 16px;
                        margin-bottom: 20px;
                        transition: all 0.3s;
                        box-shadow: 0 10px 30px rgba(245, 158, 11, 0.1);
                    ">
                        <div id="wheel-result-name" style="font-size: 26px; font-weight: 800; color: #F59E0B; margin-bottom: 6px;">
                            准备就绪
                        </div>
                        <div id="wheel-result-desc" style="font-size: 13px; color: var(--text-muted);">
                            点击下方按钮开始摇号！
                        </div>
                    </div>

                    <!-- 按钮控制组 -->
                    <div style="display: flex; gap: 12px; justify-content: center; margin-bottom: 20px;">
                        <button id="btn-spin-wheel" class="btn btn-primary" style="padding: 12px 36px; font-size: 15px; font-weight: 700; background: linear-gradient(135deg, #F59E0B, #EF4444);" onclick="FoodWheel.spin()">
                            🎰 立即摇号
                        </button>
                        <button class="btn btn-ghost" onclick="FoodWheel.close()">
                            稍后再选
                        </button>
                    </div>

                    <!-- 自定义添加美食区域 -->
                    <div style="background: var(--bg-elevated); border: 1px dashed rgba(245, 158, 11, 0.4); border-radius: var(--radius-sm); padding: 14px 16px; margin-bottom: 18px; text-align: left;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <div style="font-size: 13px; font-weight: 700; color: #F59E0B; display: flex; align-items: center; gap: 6px;">
                                <span>➕</span><span>自定义专属美味</span>
                            </div>
                            <span style="font-size: 11px; color: var(--text-muted);">支持随心加入爱吃菜品或餐厅</span>
                        </div>
                        <div style="display: flex; gap: 8px; margin-bottom: 10px;">
                            <input type="text" id="food-custom-input" class="form-input" placeholder="输入你想吃的餐厅/菜品（如: 螺蛳粉、黄焖鸡、楼下老火锅...）" style="flex: 1; font-size: 13px; padding: 8px 12px;" onkeypress="if(event.key==='Enter')FoodWheel.addFromInput()">
                            <button class="btn btn-primary btn-sm" style="background: linear-gradient(135deg, #F59E0B, #EF4444); border: none; white-space: nowrap; font-weight: 700; padding: 0 16px;" onclick="FoodWheel.addFromInput()">
                                加入转盘
                            </button>
                        </div>
                        <div style="display: flex; flex-wrap: wrap; gap: 5px; align-items: center;">
                            <span style="font-size: 11px; color: var(--text-muted);">灵感快选:</span>
                            ${['麻辣烫', '螺蛳粉', '汉堡炸鸡', '烤冷面', '老火锅', '羊肉泡馍', '黄焖鸡', '兰州拉面', '日式寿喜烧', '酸菜鱼'].map(name => `
                                <button type="button" class="btn btn-xs btn-ghost" style="padding: 2px 8px; font-size: 11px; border-radius: 999px; background: rgba(255,255,255,0.06); border: 1px solid var(--border);" onclick="FoodWheel.addCustomFood('${name}')">
                                    +${name}
                                </button>
                            `).join('')}
                        </div>
                    </div>

                    <!-- 备选池标签流 -->
                    <div style="text-align: left;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <div style="font-size: 12px; font-weight: 700; color: var(--text-muted);">
                                📋 当前转盘候选池 (${candidates.length} 项):
                            </div>
                            ${customFoods.length > 0 ? `
                                <span style="font-size: 11px; color: #F59E0B; font-weight: 600;">已包含 ${customFoods.length} 个专属自定义美味</span>
                            ` : ''}
                        </div>
                        <div style="display: flex; flex-wrap: wrap; gap: 6px; max-height: 120px; overflow-y: auto; padding: 2px;">
                            ${candidates.map(c => `
                                <span style="
                                    font-size: 11px;
                                    padding: 4px 10px;
                                    background: ${c.isCustom ? 'rgba(245, 158, 11, 0.16)' : 'var(--bg-elevated)'};
                                    border: 1px solid ${c.isCustom ? '#F59E0B' : 'var(--border)'};
                                    color: ${c.isCustom ? '#F59E0B' : 'var(--text)'};
                                    border-radius: 999px;
                                    display: inline-flex;
                                    align-items: center;
                                    gap: 6px;
                                ">
                                    <span>${c.name}</span>
                                    ${c.isCustom ? `<span style="cursor: pointer; opacity: 0.75; font-weight: 800; padding: 0 2px;" onclick="event.stopPropagation();FoodWheel.removeCustomFood(${c.customIndex})" title="从候选池删除此自定义项">✕</span>` : ''}
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
