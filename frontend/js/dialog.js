/**
 * Footprint - AppDialog Module
 * Replaces native browser confirm() and prompt() with sleek, glassmorphic custom modal dialogs.
 */
(function(window) {
    'use strict';

    function ensureDialogDom() {
        let overlay = document.getElementById('app-dialog-overlay');
        if (overlay) return overlay;

        overlay = document.createElement('div');
        overlay.id = 'app-dialog-overlay';
        overlay.className = 'app-dialog-overlay';
        overlay.innerHTML = `
            <div class="app-dialog-box" id="app-dialog-box" role="dialog" aria-modal="true">
                <div class="app-dialog-header">
                    <div class="app-dialog-icon" id="app-dialog-icon">💬</div>
                    <div class="app-dialog-title" id="app-dialog-title">提示</div>
                    <button class="app-dialog-close" id="app-dialog-close-btn" aria-label="关闭">✕</button>
                </div>
                <div class="app-dialog-body" id="app-dialog-body">
                    <div class="app-dialog-msg" id="app-dialog-msg"></div>
                    <div class="app-dialog-input-wrap" id="app-dialog-input-wrap" style="display:none">
                        <input type="text" class="form-input app-dialog-input" id="app-dialog-input" autocomplete="off" />
                    </div>
                </div>
                <div class="app-dialog-footer">
                    <button class="btn btn-ghost app-dialog-btn" id="app-dialog-cancel-btn">取消</button>
                    <button class="btn btn-primary app-dialog-btn" id="app-dialog-confirm-btn">确定</button>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);

        // Inject CSS if not already present
        if (!document.getElementById('app-dialog-style')) {
            const style = document.createElement('style');
            style.id = 'app-dialog-style';
            style.textContent = `
                .app-dialog-overlay {
                    position: fixed;
                    inset: 0;
                    background: rgba(11, 14, 20, 0.72);
                    backdrop-filter: blur(14px);
                    -webkit-backdrop-filter: blur(14px);
                    z-index: 10000;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 20px;
                    opacity: 0;
                    visibility: hidden;
                    transition: opacity 0.24s cubic-bezier(0.4, 0, 0.2, 1), visibility 0.24s;
                }
                .app-dialog-overlay.active {
                    opacity: 1;
                    visibility: visible;
                }
                .app-dialog-box {
                    width: 100%;
                    max-width: 420px;
                    background: var(--bg-card, #1A1F2C);
                    border: 1px solid var(--border, rgba(255, 255, 255, 0.12));
                    border-radius: 20px;
                    box-shadow: 0 25px 60px -15px rgba(0, 0, 0, 0.5), 0 0 1px 1px rgba(255, 255, 255, 0.05);
                    padding: 24px;
                    transform: scale(0.92) translateY(10px);
                    transition: transform 0.24s cubic-bezier(0.34, 1.56, 0.64, 1);
                    color: var(--text, #F8FAFC);
                    font-family: var(--font, inherit);
                }
                .app-dialog-overlay.active .app-dialog-box {
                    transform: scale(1) translateY(0);
                }
                .app-dialog-header {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    margin-bottom: 14px;
                }
                .app-dialog-icon {
                    width: 36px;
                    height: 36px;
                    border-radius: 10px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 18px;
                    background: rgba(59, 130, 246, 0.12);
                    color: var(--primary, #3B82F6);
                    flex-shrink: 0;
                }
                .app-dialog-icon.danger {
                    background: rgba(239, 68, 68, 0.15);
                    color: #EF4444;
                }
                .app-dialog-icon.love {
                    background: rgba(236, 72, 153, 0.15);
                    color: #EC4899;
                }
                .app-dialog-title {
                    font-size: 16px;
                    font-weight: 700;
                    flex: 1;
                    color: var(--text, #F8FAFC);
                }
                .app-dialog-close {
                    background: transparent;
                    border: none;
                    color: var(--text-muted, #94A3B8);
                    cursor: pointer;
                    font-size: 16px;
                    padding: 4px 8px;
                    border-radius: 6px;
                    transition: var(--transition, all 0.2s);
                }
                .app-dialog-close:hover {
                    color: var(--text, #FFF);
                    background: rgba(255, 255, 255, 0.08);
                }
                .app-dialog-body {
                    margin-bottom: 22px;
                }
                .app-dialog-msg {
                    font-size: 14px;
                    line-height: 1.6;
                    color: var(--text-sec, rgba(255, 255, 255, 0.75));
                    margin-bottom: 12px;
                }
                .app-dialog-input-wrap {
                    margin-top: 12px;
                }
                .app-dialog-input {
                    width: 100%;
                    padding: 10px 14px;
                    background: var(--bg-elevated, rgba(255, 255, 255, 0.06));
                    border: 1px solid var(--border, rgba(255, 255, 255, 0.15));
                    border-radius: 12px;
                    font-size: 14px;
                    color: var(--text, #F8FAFC);
                    outline: none;
                    transition: border-color 0.2s, box-shadow 0.2s;
                    box-sizing: border-box;
                }
                .app-dialog-input:focus {
                    border-color: var(--primary, #3B82F6);
                    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
                }
                .app-dialog-footer {
                    display: flex;
                    justify-content: flex-end;
                    gap: 10px;
                }
                .app-dialog-btn {
                    padding: 9px 18px;
                    border-radius: 999px;
                    font-size: 13px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: var(--transition, all 0.2s);
                }
                .app-dialog-btn.btn-danger {
                    background: #EF4444;
                    color: white;
                    border: none;
                }
                .app-dialog-btn.btn-danger:hover {
                    background: #DC2626;
                }
                [data-theme="light"] .app-dialog-box {
                    background: #FFFFFF;
                    color: #0F172A;
                    box-shadow: 0 20px 50px -10px rgba(0, 0, 0, 0.25);
                }
                [data-theme="light"] .app-dialog-msg {
                    color: #475569;
                }
                [data-theme="light"] .app-dialog-input {
                    background: #F8FAFC;
                    border-color: #E2E8F0;
                    color: #0F172A;
                }
            `;
            document.head.appendChild(style);
        }
        return overlay;
    }

    const AppDialog = {
        /**
         * Custom confirm dialog replacing window.confirm()
         * @param {Object} options
         * @returns {Promise<boolean>}
         */
        confirm(options = {}) {
            const {
                title = '确认操作',
                message = '确定要继续吗？',
                confirmText = '确定',
                cancelText = '取消',
                danger = false,
                icon = danger ? '⚠️' : '❓',
                onConfirm = null,
                onCancel = null
            } = (typeof options === 'string' ? { message: options } : options);

            return new Promise((resolve) => {
                const overlay = ensureDialogDom();
                const titleEl = document.getElementById('app-dialog-title');
                const msgEl = document.getElementById('app-dialog-msg');
                const iconEl = document.getElementById('app-dialog-icon');
                const inputWrap = document.getElementById('app-dialog-input-wrap');
                const confirmBtn = document.getElementById('app-dialog-confirm-btn');
                const cancelBtn = document.getElementById('app-dialog-cancel-btn');
                const closeBtn = document.getElementById('app-dialog-close-btn');

                titleEl.textContent = title;
                msgEl.innerHTML = message;
                iconEl.textContent = icon;
                iconEl.className = 'app-dialog-icon' + (danger ? ' danger' : '');
                inputWrap.style.display = 'none';

                confirmBtn.textContent = confirmText;
                confirmBtn.className = 'btn app-dialog-btn ' + (danger ? 'btn-danger' : 'btn-primary');
                cancelBtn.textContent = cancelText;

                function cleanup() {
                    overlay.classList.remove('active');
                    confirmBtn.onclick = null;
                    cancelBtn.onclick = null;
                    closeBtn.onclick = null;
                    document.removeEventListener('keydown', onKeyDown);
                }

                function handleConfirm() {
                    cleanup();
                    if (onConfirm) onConfirm();
                    resolve(true);
                }

                function handleCancel() {
                    cleanup();
                    if (onCancel) onCancel();
                    resolve(false);
                }

                function onKeyDown(e) {
                    if (e.key === 'Escape') handleCancel();
                    if (e.key === 'Enter') handleConfirm();
                }

                confirmBtn.onclick = handleConfirm;
                cancelBtn.onclick = handleCancel;
                closeBtn.onclick = handleCancel;
                document.addEventListener('keydown', onKeyDown);

                overlay.classList.add('active');
                confirmBtn.focus();
            });
        },

        /**
         * Custom prompt dialog replacing window.prompt()
         * @param {Object} options
         * @returns {Promise<string|null>}
         */
        prompt(options = {}) {
            const {
                title = '请输入内容',
                message = '',
                defaultValue = '',
                placeholder = '',
                type = 'text',
                confirmText = '确定',
                cancelText = '取消',
                icon = '✏️',
                onConfirm = null,
                onCancel = null
            } = (typeof options === 'string' ? { message: options } : options);

            return new Promise((resolve) => {
                const overlay = ensureDialogDom();
                const titleEl = document.getElementById('app-dialog-title');
                const msgEl = document.getElementById('app-dialog-msg');
                const iconEl = document.getElementById('app-dialog-icon');
                const inputWrap = document.getElementById('app-dialog-input-wrap');
                const input = document.getElementById('app-dialog-input');
                const confirmBtn = document.getElementById('app-dialog-confirm-btn');
                const cancelBtn = document.getElementById('app-dialog-cancel-btn');
                const closeBtn = document.getElementById('app-dialog-close-btn');

                titleEl.textContent = title;
                msgEl.innerHTML = message || '';
                msgEl.style.display = message ? 'block' : 'none';
                iconEl.textContent = icon;
                iconEl.className = 'app-dialog-icon';

                inputWrap.style.display = 'block';
                input.type = type;
                input.value = defaultValue;
                input.placeholder = placeholder;

                confirmBtn.textContent = confirmText;
                confirmBtn.className = 'btn btn-primary app-dialog-btn';
                cancelBtn.textContent = cancelText;

                function cleanup() {
                    overlay.classList.remove('active');
                    confirmBtn.onclick = null;
                    cancelBtn.onclick = null;
                    closeBtn.onclick = null;
                    document.removeEventListener('keydown', onKeyDown);
                }

                function handleConfirm() {
                    const val = input.value;
                    cleanup();
                    if (onConfirm) onConfirm(val);
                    resolve(val);
                }

                function handleCancel() {
                    cleanup();
                    if (onCancel) onCancel();
                    resolve(null);
                }

                function onKeyDown(e) {
                    if (e.key === 'Escape') handleCancel();
                    if (e.key === 'Enter') handleConfirm();
                }

                confirmBtn.onclick = handleConfirm;
                cancelBtn.onclick = handleCancel;
                closeBtn.onclick = handleCancel;
                document.addEventListener('keydown', onKeyDown);

                overlay.classList.add('active');
                setTimeout(() => {
                    input.focus();
                    if (input.select) input.select();
                }, 50);
            });
        }
    };

    window.AppDialog = AppDialog;
})(window);
