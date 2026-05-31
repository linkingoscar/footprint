const app = getApp();

Page({
    data: {
        modes: [
            { key: 'travel', name: '旅行', icon: '✈️' },
            { key: 'food', name: '美食', icon: '🍜' },
            { key: 'love', name: '情侣', icon: '💕' }
        ],
        mode: 'travel',
        theme: 'dark',
        total: 0
    },

    onShow() {
        const settings = app.globalData.settings;
        this.setData({
            mode: settings.mode || 'travel',
            theme: settings.theme || 'dark',
            total: app.getRecords().length
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
    }
});
