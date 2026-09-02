/**
 * 足迹 (Footprint) - 情侣时光胶囊与纪念日里程碑倒数模块 (Love Capsule & Milestone Countdowns)
 * 赋予情侣模式深层实用性与情感羁绊，拒绝噱头。
 */

const LoveCapsuleModule = {
    getTogetherDate() {
        const config = (typeof getConfig === 'function') ? getConfig() : {};
        return config.togetherDate || '2024-05-20';
    },

    // 计算下一个重要相恋里程碑倒数
    calcMilestones() {
        const startDate = new Date(this.getTogetherDate());
        const now = new Date();
        const diffDays = Math.floor((now - startDate) / (1000 * 60 * 60 * 24));

        // 目标整百天/浪漫天数
        const dayTargets = [100, 200, 300, 520, 600, 800, 999, 1000, 1314, 2000, 3000];
        let nextDayMilestone = null;
        for (const t of dayTargets) {
            if (t > diffDays) {
                nextDayMilestone = {
                    title: `相恋 ${t} 天纪念日`,
                    targetDays: t,
                    remaining: t - diffDays,
                    icon: t === 520 || t === 1314 ? '💖' : '🎉'
                };
                break;
            }
        }

        // 目标周年纪念日
        const currentYear = now.getFullYear();
        let nextAnniversaryDate = new Date(currentYear, startDate.getMonth(), startDate.getDate());
        if (nextAnniversaryDate < now) {
            nextAnniversaryDate = new Date(currentYear + 1, startDate.getMonth(), startDate.getDate());
        }
        const remainingAnniversaryDays = Math.ceil((nextAnniversaryDate - now) / (1000 * 60 * 60 * 24));
        const anniversaryYears = nextAnniversaryDate.getFullYear() - startDate.getFullYear();

        return {
            diffDays,
            nextDayMilestone,
            nextAnniversary: {
                title: `相爱 ${anniversaryYears} 周年纪念日`,
                remaining: remainingAnniversaryDays,
                dateStr: nextAnniversaryDate.toISOString().split('T')[0]
            }
        };
    },

    getCapsules() {
        try {
            const saved = localStorage.getItem('footprint_love_capsules');
            if (saved) return JSON.parse(saved);
        } catch (e) {}
        return [
            {
                id: 'sample_capsule',
                title: '写给一周年后的我们',
                author: 'TA',
                unlockDate: '2026-12-31',
                content: '希望到那个时候，我们已经一起看过了雪山日落，尝遍了心愿单上的十种美食，依然一如既往地深爱彼此！❤️',
                createdAt: '2025-01-01'
            }
        ];
    },

    saveCapsules(list) {
        localStorage.setItem('footprint_love_capsules', JSON.stringify(list));
        if (typeof apiFetch === 'function') {
            apiFetch('/api/features/love_capsules', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ data: list })
            }).catch(() => {});
        }
    },

    open() {
        let modal = document.getElementById('modal-love-capsule');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'modal-love-capsule';
            modal.className = 'modal-overlay';
            document.body.appendChild(modal);
        }

        const milestones = this.calcMilestones();
        const capsules = this.getCapsules();
        const todayStr = new Date().toISOString().split('T')[0];

        modal.innerHTML = `
            <div class="modal" style="max-width: 680px; width: 95vw; max-height: 90vh; display: flex; flex-direction: column; background: #131722; border: 1px solid rgba(225,29,72,0.35); border-radius: 18px;">
                <div class="modal-header" style="background: linear-gradient(180deg, rgba(225,29,72,0.15) 0%, transparent 100%); border-bottom: 1px solid rgba(255,255,255,0.08);">
                    <div class="modal-title" style="display:flex;align-items:center;gap:8px;color:#F43F5E;">
                        <span>💌</span>
                        <span>相伴时光 · 倒数日与时光胶囊</span>
                    </div>
                    <button class="modal-close" onclick="LoveCapsuleModule.close()">✕</button>
                </div>
                <div class="modal-body" style="padding: 24px; overflow-y: auto;">
                    <!-- 倒数日看板 -->
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; margin-bottom: 24px;">
                        ${milestones.nextDayMilestone ? `
                            <div style="background: linear-gradient(135deg, rgba(225,29,72,0.12), rgba(147,51,234,0.12)); border: 1px solid rgba(225,29,72,0.3); border-radius: 14px; padding: 18px; text-align: center;">
                                <div style="font-size: 11px; color: #FDA4AF; text-transform: uppercase; font-weight: 700; margin-bottom: 4px;">
                                    ${milestones.nextDayMilestone.icon} 下一个大日子倒数
                                </div>
                                <div style="font-size: 16px; font-weight: 800; color: #F8FAFC; margin-bottom: 8px;">
                                    ${milestones.nextDayMilestone.title}
                                </div>
                                <div style="font-size: 34px; font-weight: 900; color: #F43F5E; font-family: ui-monospace, monospace;">
                                    ${milestones.nextDayMilestone.remaining} <span style="font-size: 14px; font-weight: normal; color: #94A3B8;">天</span>
                                </div>
                            </div>
                        ` : ''}

                        <div style="background: linear-gradient(135deg, rgba(245,158,11,0.12), rgba(225,29,72,0.12)); border: 1px solid rgba(245,158,11,0.3); border-radius: 14px; padding: 18px; text-align: center;">
                            <div style="font-size: 11px; color: #FCD34D; text-transform: uppercase; font-weight: 700; margin-bottom: 4px;">
                                🎂 周年庆典倒数
                            </div>
                            <div style="font-size: 16px; font-weight: 800; color: #F8FAFC; margin-bottom: 8px;">
                                ${milestones.nextAnniversary.title}
                            </div>
                            <div style="font-size: 34px; font-weight: 900; color: #F59E0B; font-family: ui-monospace, monospace;">
                                ${milestones.nextAnniversary.remaining} <span style="font-size: 14px; font-weight: normal; color: #94A3B8;">天</span>
                            </div>
                        </div>
                    </div>

                    <!-- 时光胶囊密信区域 -->
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                        <div>
                            <div style="font-size: 16px; font-weight: 800; color: #F8FAFC;">封存的时光胶囊</div>
                            <div style="font-size: 12px; color: #94A3B8;">写给未来的信，未到开启日期无法查看</div>
                        </div>
                        <button class="btn btn-sm btn-primary" style="background: linear-gradient(135deg, #E11D48, #9333EA); border: none;" onclick="LoveCapsuleModule.createCapsulePrompt()">
                            ➕ 埋下新胶囊
                        </button>
                    </div>

                    <div style="display: flex; flex-direction: column; gap: 12px;">
                        ${capsules.map(c => {
                            const isLocked = c.unlockDate > todayStr;
                            return `
                                <div style="
                                    background: rgba(255,255,255,0.03);
                                    border: 1px solid ${isLocked ? 'rgba(255,255,255,0.08)' : 'rgba(244,63,94,0.4)'};
                                    border-radius: 12px;
                                    padding: 16px;
                                ">
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                        <div style="font-weight: 700; font-size: 14px; color: #F8FAFC; display: flex; align-items: center; gap: 6px;">
                                            <span>${isLocked ? '🔒' : '🔓'}</span>
                                            <span>${c.title}</span>
                                        </div>
                                        <span style="font-size: 11px; padding: 2px 8px; border-radius: 999px; background: ${isLocked ? 'rgba(255,255,255,0.08)' : 'rgba(244,63,94,0.15)'}; color: ${isLocked ? '#94A3B8' : '#F43F5E'}; font-family: monospace;">
                                            ${isLocked ? `解锁日期: ${c.unlockDate}` : '✨ 已解锁'}
                                        </span>
                                    </div>
                                    ${isLocked ? `
                                        <div style="font-size: 12px; color: #64748B; font-style: italic; padding: 12px 0;">
                                            这是一段处于封存中的甜蜜密信，请耐心等待指定日期的到来再一起启封...
                                        </div>
                                    ` : `
                                        <div style="font-size: 13px; color: #CBD5E1; line-height: 1.6; background: rgba(225,29,72,0.06); padding: 12px 14px; border-radius: 8px; border-left: 3px solid #E11D48;">
                                            ${c.content}
                                        </div>
                                    `}
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            </div>
        `;
        modal.classList.add('active');
    },

    close() {
        const modal = document.getElementById('modal-love-capsule');
        if (modal) modal.classList.remove('active');
    },

    createCapsulePrompt() {
        const title = prompt('请输入时光胶囊的标题（如：写给两周年后的我们）:');
        if (!title || !title.trim()) return;
        const unlockDate = prompt('请输入解锁开启日期 (格式: YYYY-MM-DD，如 2026-12-31):', '2026-12-31');
        if (!unlockDate || !unlockDate.trim()) return;
        const content = prompt('请输入封存给未来的密信内容:');
        if (!content || !content.trim()) return;

        const list = this.getCapsules();
        list.unshift({
            id: 'cap_' + Date.now(),
            title: title.trim(),
            unlockDate: unlockDate.trim(),
            content: content.trim(),
            createdAt: new Date().toISOString().split('T')[0]
        });
        this.saveCapsules(list);
        this.open();
        toast('💌 时光胶囊已成功封存入库！');
    }
};

window.LoveCapsuleModule = LoveCapsuleModule;
