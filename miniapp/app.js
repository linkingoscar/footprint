// app.js - 小程序入口文件
const api = require('./utils/api.js');

App({
    globalData: {
        userInfo: null,
        records: [],
        settings: {
            mode: 'travel', // travel, food, love
            theme: 'dark',
            lang: 'zh'
        },
        apiAvailable: false,
        token: api.getToken(),
        user: null
    },

    onLaunch() {
        // 从本地存储加载数据
        const records = wx.getStorageSync('records');
        if (records) {
            this.globalData.records = records;
        }

        const settings = wx.getStorageSync('settings');
        if (settings) {
            this.globalData.settings = settings;
        }

        // 检查登录状态
        this.checkLogin();

        // 检查 API 可用性并同步数据
        this.checkApi();
    },

    // 检查登录状态
    checkLogin() {
        wx.getSetting({
            success: (res) => {
                if (res.authSetting['scope.userInfo']) {
                    wx.getUserInfo({
                        success: (res) => {
                            this.globalData.userInfo = res.userInfo;
                        }
                    });
                }
            }
        });
    },

    // 检查后端 API 可用性
    checkApi() {
        api.healthCheck()
            .then(res => {
                this.globalData.apiAvailable = true;
                console.log('API connected:', res);
                // 如果有 token，尝试从 API 同步数据
                if (this.globalData.token) {
                    this.syncFromApi();
                }
            })
            .catch(() => {
                this.globalData.apiAvailable = false;
                console.log('API not available, using local storage');
            });
    },

    // 从 API 同步记录到本地缓存
    syncFromApi() {
        api.getRecords()
            .then(records => {
                if (Array.isArray(records)) {
                    this.globalData.records = records;
                    wx.setStorageSync('records', records);
                    console.log('Synced records from API:', records.length);
                }
            })
            .catch(e => {
                console.log('Sync from API failed:', e);
            });
    },

    // 保存记录（API 优先，本地 fallback）
    saveRecord(record) {
        record.id = record.id || this.generateId();
        record.createdAt = record.createdAt || new Date().toISOString();

        // 始终先写本地缓存
        this.globalData.records.unshift(record);
        wx.setStorageSync('records', this.globalData.records);

        // 尝试同步到 API
        if (this.globalData.apiAvailable && this.globalData.token) {
            api.createRecord(record)
                .then(result => {
                    console.log('Record saved to API:', result);
                    // 如果 API 返回了 id，更新本地记录
                    if (result && result.id) {
                        record.id = result.id;
                        wx.setStorageSync('records', this.globalData.records);
                    }
                })
                .catch(e => {
                    console.log('API save failed, record saved locally:', e);
                });
        }

        return record;
    },

    // 删除记录（API 优先，本地 fallback）
    deleteRecord(id) {
        // 始终先更新本地缓存
        this.globalData.records = this.globalData.records.filter(r => r.id !== id);
        wx.setStorageSync('records', this.globalData.records);

        // 尝试从 API 删除
        if (this.globalData.apiAvailable && this.globalData.token) {
            api.deleteRecord(id)
                .then(() => console.log('Record deleted from API:', id))
                .catch(e => console.log('API delete failed, removed locally:', e));
        }
    },

    // 获取记录（从本地缓存读取，保持同步接口）
    getRecords(mode = 'all') {
        if (mode === 'all') {
            return this.globalData.records;
        }
        return this.globalData.records.filter(r => r.mode === mode);
    },

    // 保存设置
    saveSettings(settings) {
        this.globalData.settings = { ...this.globalData.settings, ...settings };
        wx.setStorageSync('settings', this.globalData.settings);
    },

    // 生成ID
    generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    },

    // 显示提示
    showToast(title, icon = 'success') {
        wx.showToast({
            title,
            icon,
            duration: 2000
        });
    },

    // 显示加载
    showLoading(title = '加载中...') {
        wx.showLoading({ title });
    },

    // 隐藏加载
    hideLoading() {
        wx.hideLoading();
    }
});
