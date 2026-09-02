/**
 * 足迹 (Footprint) - 地图引擎模块 (Leaflet.js + MarkerCluster)
 */

let mapInstance = null;
let clusterGroup = null;

function initMainMap() {
    const mapEl = document.getElementById('footprint-map');
    if (!mapEl || mapInstance) return;

    // 默认以中国中心为视野
    mapInstance = L.map('footprint-map', {
        zoomControl: true,
        attributionControl: false
    }).setView([34.3416, 108.9398], 5);

    // 瓦片底图 (高德矢量/OSM)
    L.tileLayer('https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}', {
        subdomains: ['1', '2', '3', '4'],
        minZoom: 3,
        maxZoom: 18
    }).addTo(mapInstance);

    // 初始化 MarkerCluster 聚合图层（若已引入插件）
    if (typeof L.markerClusterGroup === 'function') {
        clusterGroup = L.markerClusterGroup({
            showCoverageOnHover: false,
            maxClusterRadius: 45,
            spiderfyOnMaxZoom: true,
            iconCreateFunction: function (cluster) {
                const count = cluster.getChildCount();
                let sizeClass = 'marker-cluster-small';
                if (count > 20) sizeClass = 'marker-cluster-large';
                else if (count > 5) sizeClass = 'marker-cluster-medium';
                return L.divIcon({
                    html: `<div><span>${count}</span></div>`,
                    className: `marker-cluster ${sizeClass}`,
                    iconSize: L.point(40, 40)
                });
            }
        });
        mapInstance.addLayer(clusterGroup);
    } else {
        clusterGroup = L.layerGroup().addTo(mapInstance);
    }

    window.mapInstance = mapInstance;
    renderMapMarkers(getLocatedRecords());
}

function createPinIcon(mode, isCouple) {
    let pinClass = 'pin-travel';
    let iconEmoji = '✈️';

    if (isCouple) {
        pinClass = 'pin-love';
        iconEmoji = '💕';
    } else if (mode === 'food') {
        pinClass = 'pin-food';
        iconEmoji = '🍜';
    }

    return L.divIcon({
        className: 'custom-pin-wrapper',
        html: `
            <div class="custom-map-pin ${pinClass}">
                <span class="pin-icon">${iconEmoji}</span>
            </div>
        `,
        iconSize: [38, 38],
        iconAnchor: [19, 38],
        popupAnchor: [0, -36]
    });
}

function renderMapMarkers(records = []) {
    if (!mapInstance || !clusterGroup) return;

    clusterGroup.clearLayers();
    const bounds = L.latLngBounds();
    const emptyEl = document.getElementById('map-empty');

    if (!records.length) {
        if (emptyEl) emptyEl.style.display = 'flex';
        return;
    }
    if (emptyEl) emptyEl.style.display = 'none';

    records.forEach(r => {
        if (r.latitude === null || r.latitude === undefined || r.longitude === null || r.longitude === undefined) return;
        const lat = parseFloat(r.latitude);
        const lng = parseFloat(r.longitude);
        if (isNaN(lat) || isNaN(lng)) return;

        const isCouple = !!(r.is_couple || r.mode === 'love');
        const icon = createPinIcon(r.mode, isCouple);
        const marker = L.marker([lat, lng], { icon });

        // Popup Content
        const thumb = (r.images && r.images[0]) ? resolveAssetUrl(r.images[0]) : '';
        const badgeLabel = r.mode === 'food' ? '🍜 美食寻味' : (isCouple ? '💕 专属回忆' : '✈️ 旅行探索');
        const priceText = r.price ? ` · 人均¥${r.price}` : '';
        const ratingText = r.rating ? ` · ⭐${r.rating}` : '';

        const popupHtml = `
            <div class="popup-card">
                ${thumb ? `<img class="popup-thumb" src="${thumb}" onerror="this.style.display='none'">` : ''}
                <div class="popup-title">${r.title || '无标题'}</div>
                <div class="popup-meta">
                    <span>${badgeLabel}</span>
                    <span>${r.date || ''}</span>
                    ${priceText || ratingText ? `<span style="color:#F59E0B">${priceText}${ratingText}</span>` : ''}
                </div>
                ${r.location ? `<div style="font-size:11px;color:var(--text-muted);margin-top:4px">📍 ${r.location}</div>` : ''}
            </div>
        `;
        marker.bindPopup(popupHtml);
        clusterGroup.addLayer(marker);
        bounds.extend([lat, lng]);
    });

    if (records.length > 0 && bounds.isValid()) {
        mapInstance.fitBounds(bounds, { padding: [40, 40], maxZoom: 15 });
    }
}

function zoomToRecord(lat, lng) {
    if (!mapInstance) return;
    mapInstance.flyTo([lat, lng], 15, { duration: 1.2 });
}
