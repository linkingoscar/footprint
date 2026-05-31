const app = getApp();

Page({
    data: {
        center: { latitude: 39.9042, longitude: 116.4074 },
        scale: 4,
        records: [],
        markers: [],
        polyline: []
    },

    onShow() {
        const records = app.getRecords().filter(record => record.latitude && record.longitude);
        const markers = records.map((record, index) => ({
            id: index + 1,
            latitude: record.latitude,
            longitude: record.longitude,
            title: record.title,
            callout: {
                content: record.title,
                display: 'BYCLICK',
                padding: 8,
                borderRadius: 6
            }
        }));
        const points = records.map(record => ({ latitude: record.latitude, longitude: record.longitude }));
        this.setData({
            records,
            markers,
            center: points[0] || this.data.center,
            scale: records.length > 1 ? 5 : 12,
            polyline: points.length > 1 ? [{ points, color: '#3B82F6', width: 4 }] : []
        });
    }
});
