const app = getApp();
const api = require('../../utils/api.js');

Page({
    data: {
        modes: [
            { key: 'travel', name: '旅行', icon: '✈️' },
            { key: 'food', name: '美食', icon: '🍜' },
            { key: 'love', name: '情侣', icon: '💕' }
        ],
        mode: 'travel',
        theme: 'dark',
        total: 0,
        // API 配置
        apiBase: api.getApiBase(),
        apiAvailable: false,
        loggedIn: !!api.getToken(),
        username: '',
        password: '',
        showLoginForm: false
    },

    onShow() {
        const settings = app.globalData.settings;
        this.setData({
            mode: settings.mode || 'travel',
            theme: settings.theme || 'dark',
            total: app.getRecords().length,
            apiAvailable: app.globalData.apiAvailable,
            loggedIn: !!api.getToken()
        });
    },

    selectMode(event) {
        const mode = event.currentTarget.dataset.mode;
        app.saveSettings({ mode });
        this.setData({ mode });
        app.showToast('已切换');
    },

    selectTheme(event) {
        const theme = event.currentTarget.dataset.theme;
        app.saveSettings({ theme });
        this.setData({ theme });
        app.showToast('已保存');
    },

    clearData() {
        wx.showModal({
            title: '清空数据',
            content: '确定删除本机所有足迹记录吗？',
            success: (res) => {
                if (!res.confirm) return;
                app.globalData.records = [];
                wx.setStorageSync('records', []);
                this.setData({ total: 0 });
                app.showToast('已清空');
            }
        });
    },

    // API 配置
    onApiBaseInput(e) {
        this.setData({ apiBase: e.detail.value });
    },

    saveApiBase() {
        const url = this.data.apiBase.trim();
        if (!url) {
            app.showToast('请输入API地址', 'none');
            return;
        }
        api.setApiBase(url);
        app.showToast('API地址已保存');
        // 重新检查 API
        app.checkApi();
        setTimeout(() => {
            this.setData({ apiAvailable: app.globalData.apiAvailable });
        }, 2000);
    },

    toggleLoginForm() {
        this.setData({ showLoginForm: !this.data.showLoginForm });
    },

    onUsernameInput(e) {
        this.setData({ username: e.detail.value });
    },

    onPasswordInput(e) {
        this.setData({ password: e.detail.value });
    },

    doLogin() {
        const { username, password } = this.data;
        if (!username.trim() || !password.trim()) {
            app.showToast('请输入用户名和密码', 'none');
            return;
        }
        app.showLoading('登录中...');
        api.login(username.trim(), password.trim())
            .then(res => {
                app.hideLoading();
                const token = res.token || res.data?.token || '';
                if (token) {
                    api.setToken(token);
                    app.globalData.token = token;
                    app.globalData.user = res.user || res.data?.user || { username: username.trim() };
                    this.setData({ loggedIn: true, showLoginForm: false, username: '', password: '' });
                    app.showToast('登录成功');
                    // 同步数据
                    app.syncFromApi();
                } else {
                    app.showToast('登录失败', 'none');
                }
            })
            .catch(e => {
                app.hideLoading();
                console.log('Login failed:', e);
                const msg = (e.data && e.data.message) || '登录失败';
                app.showToast(msg, 'none');
            });
    },

    doRegister() {
        const { username, password } = this.data;
        if (!username.trim() || !password.trim()) {
            app.showToast('请输入用户名和密码', 'none');
            return;
        }
        app.showLoading('注册中...');
        api.register(username.trim(), password.trim())
            .then(res => {
                app.hideLoading();
                const token = res.token || res.data?.token || '';
                if (token) {
                    api.setToken(token);
                    app.globalData.token = token;
                    app.globalData.user = res.user || res.data?.user || { username: username.trim() };
                    this.setData({ loggedIn: true, showLoginForm: false, username: '', password: '' });
                    app.showToast('注册成功');
                } else {
                    app.showToast('注册成功，请登录');
                    this.setData({ showLoginForm: true });
                }
            })
            .catch(e => {
                app.hideLoading();
                console.log('Register failed:', e);
                const msg = (e.data && e.data.message) || '注册失败';
                app.showToast(msg, 'none');
            });
    },

    doLogout() {
        api.clearToken();
        app.globalData.token = '';
        app.globalData.user = null;
        this.setData({ loggedIn: false });
        app.showToast('已退出登录');
    }
});
