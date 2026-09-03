/**
 * 足迹 (Footprint) - 轨迹回放模块 (Replay)
 */

function initReplayMap(sorted) {
    const el = document.getElementById('replay-map');
    if (!el || !sorted?.length) return;

    window._replayProvider = null;
    window._replayRecords = sorted;
    window._replayMap = null;
    window._replayMarkers = [];
    window._replayPath = [];
    window._replayBaidu = null;
    window._replayTencent = null;
    window._replayBing = null;

    const provider = (typeof getConfig === 'function' ? getConfig().mapProvider : null) || 'amap';

    if (provider === 'baidu' && typeof BMap !== 'undefined') {
        const map = new BMap.Map('replay-map');
        const points = sorted.map(r => new BMap.Point(r.longitude, r.latitude));
        map.centerAndZoom(points[0], 8);
        map.enableScrollWheelZoom(true);
        const markers = points.map((point, i) => {
            const marker = new BMap.Marker(point);
            map.addOverlay(marker);
            return marker;
        });
        const line = new BMap.Polyline(points, {
            strokeColor: '#3B82F6',
            strokeWeight: 3,
            strokeOpacity: 0.8
        });
        map.addOverlay(line);
        if (points.length > 1) map.setViewport(points);
        window._replayProvider = 'baidu';
        window._replayBaidu = { map, points, markers };
        return;
    }

    if (provider === 'tencent' && typeof TMap !== 'undefined') {
        const center = new TMap.LatLng(sorted[0].latitude, sorted[0].longitude);
        const map = new TMap.Map(el, { center, zoom: 8 });
        const geometries = sorted.map((r, i) => ({
            id: r.id || String(i),
            position: new TMap.LatLng(r.latitude, r.longitude),
            properties: { title: r.title, index: i + 1 }
        }));
        const markers = new TMap.MultiMarker({ map, geometries });
        let line = null;
        if (TMap.MultiPolyline) {
            line = new TMap.MultiPolyline({
                map,
                geometries: [{
                    id: 'full-route',
                    paths: sorted.map(r => new TMap.LatLng(r.latitude, r.longitude))
                }],
                styles: {
                    route: new TMap.PolylineStyle({
                        color: '#3B82F6',
                        width: 4,
                        borderWidth: 0
                    })
                }
            });
        }
        window._replayProvider = 'tencent';
        window._replayTencent = { map, markers, line, points: sorted.map(r => new TMap.LatLng(r.latitude, r.longitude)) };
        return;
    }

    if (provider === 'bing' && window.Microsoft?.Maps) {
        const map = new Microsoft.Maps.Map(el, {
            center: new Microsoft.Maps.Location(sorted[0].latitude, sorted[0].longitude),
            zoom: 8
        });
        const locations = sorted.map(r => new Microsoft.Maps.Location(r.latitude, r.longitude));
        const pins = sorted.map((r, i) => {
            const pin = new Microsoft.Maps.Pushpin(locations[i], { title: String(i + 1), subTitle: r.title });
            map.entities.push(pin);
            return pin;
        });
        const route = new Microsoft.Maps.Polyline(locations, { strokeColor: '#3B82F6', strokeThickness: 3 });
        map.entities.push(route);
        if (locations.length > 1) map.setView({ bounds: Microsoft.Maps.LocationRect.fromLocations(locations) });
        window._replayProvider = 'bing';
        window._replayBing = { map, locations, pins };
        return;
    }

    if (typeof AMap !== 'undefined') {
        const map = new AMap.Map('replay-map', {
            zoom: 10,
            center: [sorted[0].longitude, sorted[0].latitude],
            mapStyle: 'amap://styles/normal'
        });

        const markers = sorted.map((r, i) => new AMap.Marker({
            position: new AMap.LngLat(r.longitude, r.latitude),
            content: replayMarkerHtml(i, false),
            anchor: 'center'
        }));

        markers.forEach(m => m.setMap(map));
        const path = sorted.map(r => new AMap.LngLat(r.longitude, r.latitude));
        const polyline = new AMap.Polyline({
            path,
            strokeColor: '#3B82F6',
            strokeWeight: 3,
            strokeOpacity: 0.8,
            lineJoin: 'round'
        });
        polyline.setMap(map);
        map.setFitView(markers);

        window._replayProvider = 'amap';
        window._replayMap = map;
        window._replayMarkers = markers;
        window._replayPath = path;
        return;
    }

    renderReplayFallback(sorted, '地图 SDK 未加载。请在设置中保存地图 API Key；当前可使用列表回放。');
}

function replayMarkerHtml(index, active) {
    if (active) {
        return `<div style="background:var(--primary);padding:6px;border-radius:50%;box-shadow:0 2px 12px var(--glow);width:32px;height:32px;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:700;color:white">${index + 1}</div>`;
    }
    return `<div style="background:white;padding:4px;border-radius:50%;box-shadow:0 2px 8px rgba(0,0,0,0.3);width:24px;height:24px;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600;color:var(--primary)">${index + 1}</div>`;
}

function renderReplayFallback(sorted, message) {
    const el = document.getElementById('replay-map');
    if (!el) return;
    const safeEscape = typeof escapeHtml === 'function' ? escapeHtml : (s => s || '');
    el.innerHTML = `
        <div style="height:100%;display:flex;flex-direction:column;padding:16px;gap:12px;overflow:auto">
            <div style="font-size:12px;color:var(--text-muted);line-height:1.5">${message}</div>
            <div style="display:flex;flex-direction:column;gap:10px">
                ${sorted.map((r, i) => `
                    <div id="replay-step-${i}" style="display:grid;grid-template-columns:28px 1fr;gap:10px;align-items:flex-start">
                        <div style="display:flex;flex-direction:column;align-items:center">
                            <div data-replay-dot="${i}" style="width:28px;height:28px;border-radius:50%;background:var(--bg);border:1px solid var(--border);display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:var(--primary)">${i + 1}</div>
                            ${i < sorted.length - 1 ? '<div data-replay-line="' + i + '" style="width:2px;height:24px;background:var(--border);margin-top:4px"></div>' : ''}
                        </div>
                        <div>
                            <div style="font-size:13px;font-weight:600;color:var(--text)">${safeEscape(r.title || '未命名记录')}</div>
                            <div style="font-size:11px;color:var(--text-muted);margin-top:2px">${safeEscape(r.location || `GPS ${r.latitude}, ${r.longitude}`)} · ${safeEscape(r.date || '')}</div>
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

function updateReplayProgress(index) {
    const records = window._replayRecords || [];
    records.forEach((_, i) => {
        const dots = document.querySelectorAll(`[data-replay-dot="${i}"]`);
        const rows = document.querySelectorAll(`[data-replay-row="${i}"]`);
        const line = document.querySelector(`[data-replay-line="${i}"]`);
        dots.forEach(dot => {
            dot.style.background = i <= index ? 'var(--primary)' : 'var(--bg)';
            dot.style.color = i <= index ? 'white' : 'var(--primary)';
            dot.style.borderColor = i <= index ? 'var(--primary)' : 'var(--border)';
            dot.style.boxShadow = i === index ? '0 2px 12px var(--glow)' : 'none';
            dot.style.transform = i === index ? 'scale(1.12)' : 'scale(1)';
        });
        rows.forEach(row => {
            row.style.background = i === index ? 'var(--mode-bg)' : 'transparent';
            row.style.borderRadius = i === index ? '8px' : '0';
            row.style.paddingLeft = i === index ? '8px' : '0';
            row.style.paddingRight = i === index ? '8px' : '0';
        });
        if (line) line.style.background = i < index ? 'var(--primary)' : 'var(--border)';
    });
}

function startReplay() {
    const provider = window._replayProvider;
    const records = window._replayRecords || [];
    if (records.length < 2) return;

    let animatedLine = null;
    if (provider === 'amap' && window._replayMap) {
        animatedLine = new AMap.Polyline({
            strokeColor: '#FF2442',
            strokeWeight: 4,
            strokeOpacity: 1,
            lineJoin: 'round'
        });
        animatedLine.setMap(window._replayMap);
    }

    if (provider === 'baidu' && window._replayBaidu) {
        animatedLine = new BMap.Polyline([], {
            strokeColor: '#FF2442',
            strokeWeight: 4,
            strokeOpacity: 1
        });
        window._replayBaidu.map.addOverlay(animatedLine);
    }

    if (provider === 'bing' && window._replayBing) {
        animatedLine = new Microsoft.Maps.Polyline([], { strokeColor: '#FF2442', strokeThickness: 4 });
        window._replayBing.map.entities.push(animatedLine);
    }

    let index = 0;
    const animate = () => {
        if (index >= records.length) {
            if (typeof toast === 'function') toast('🛤️ 轨迹回放完成');
            return;
        }

        updateReplayProgress(index);

        if (provider === 'amap' && window._replayMap) {
            const path = window._replayPath;
            animatedLine.setPath(path.slice(0, index + 1));
            window._replayMap.setCenter(path[index]);
            window._replayMarkers.forEach((m, i) => m.setContent(replayMarkerHtml(i, i === index)));
        } else if (provider === 'baidu' && window._replayBaidu) {
            const { map, points } = window._replayBaidu;
            animatedLine.setPath(points.slice(0, index + 1));
            map.panTo(points[index]);
        } else if (provider === 'tencent' && window._replayTencent) {
            const { map, points } = window._replayTencent;
            map.setCenter(points[index]);
        } else if (provider === 'bing' && window._replayBing) {
            const { map, locations } = window._replayBing;
            animatedLine.setLocations(locations.slice(0, index + 1));
            map.setView({ center: locations[index] });
        }

        index++;
        setTimeout(animate, 800);
    };

    animate();
}

if (typeof window !== 'undefined') {
    window.initReplayMap = initReplayMap;
    window.replayMarkerHtml = replayMarkerHtml;
    window.renderReplayFallback = renderReplayFallback;
    window.updateReplayProgress = updateReplayProgress;
    window.startReplay = startReplay;
}
