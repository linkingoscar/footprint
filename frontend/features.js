/**
 * 足迹 - 新功能模块
 * Phase 1: 轨迹增强回放、城市点亮、数据导出
 * Phase 2: AI故事、分享海报、费用追踪、批量导入
 * Phase 3: 运动追踪、3D地球
 */

// ========== 工具函数 ==========
function featureFetch(url, options) {
    options = options || {};
    var headers = options.headers || {};
    if (typeof getAuthHeaders === 'function') {
        var authH = getAuthHeaders();
        for (var k in authH) { headers[k] = authH[k]; }
    }
    var fullUrl = url;
    if (typeof getApiBase === 'function') {
        var base = getApiBase();
        if (base && url.startsWith('/')) {
            fullUrl = base + url;
        }
    }
    options.headers = headers;
    return fetch(fullUrl, options);
}

function resolveAsset(url) {
    if (typeof resolveAssetUrl === 'function') return resolveAssetUrl(url);
    return url;
}

function downloadFile(content, filename, type) {
    var blob = new Blob([content], { type: type });
    downloadBlob(blob, filename);
}

function downloadBlob(blob, filename) {
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function wrapText(text, maxChars) {
    var lines = [];
    var current = '';
    for (var i = 0; i < text.length; i++) {
        current += text[i];
        if (current.length >= maxChars) {
            lines.push(current);
            current = '';
        }
    }
    if (current) lines.push(current);
    return lines;
}

function haversine(lat1, lon1, lat2, lon2) {
    var R = 6371e3;
    var toRad = function(x) { return x * Math.PI / 180; };
    var dLat = toRad(lat2 - lat1);
    var dLon = toRad(lon2 - lon1);
    var a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

// ========== 增强轨迹回放模块 ==========
var ReplayEnhanced = {
    playing: false,
    speed: 1,
    currentIndex: 0,
    timer: null,
    records: [],

    init: function(sorted) {
        this.records = sorted || [];
        this.currentIndex = 0;
        this.playing = false;
        if (this.timer) clearTimeout(this.timer);
    },

    play: function() {
        if (this.records.length < 2) return;
        this.playing = true;
        this.animate();
        this.updateControls();
    },

    pause: function() {
        this.playing = false;
        if (this.timer) clearTimeout(this.timer);
        this.updateControls();
    },

    toggle: function() {
        if (this.playing) this.pause();
        else this.play();
    },

    setSpeed: function(speed) {
        this.speed = speed;
        this.updateControls();
    },

    seekTo: function(index) {
        this.currentIndex = Math.max(0, Math.min(index, this.records.length - 1));
        this.updateMapPosition();
        this.updateProgress();
    },

    animate: function() {
        if (!this.playing || this.currentIndex >= this.records.length) {
            this.playing = false;
            this.updateControls();
            if (this.currentIndex >= this.records.length) {
                toast('🛤️ 轨迹回放完成');
            }
            return;
        }

        this.updateMapPosition();
        this.updateProgress();
        this.currentIndex++;

        var delay = Math.max(200, 1000 / this.speed);
        var self = this;
        this.timer = setTimeout(function() { self.animate(); }, delay);
    },

    updateMapPosition: function() {
        var r = this.records[this.currentIndex];
        if (!r) return;
        var provider = window._replayProvider;

        if (provider === 'amap' && window._replayMap) {
            window._replayMap.setCenter(new AMap.LngLat(r.longitude, r.latitude));
            window._replayMarkers.forEach(function(m, i) {
                m.setContent(replayMarkerHtml(i, i === this.currentIndex));
            }.bind(this));
            var animatedLine = window._replayAnimatedLine;
            if (animatedLine) {
                animatedLine.setPath(window._replayPath.slice(0, this.currentIndex + 1));
            }
        }
    },

    updateProgress: function() {
        updateReplayProgress(this.currentIndex);
        var progressEl = document.getElementById('replay-progress-fill');
        if (progressEl) {
            var pct = ((this.currentIndex + 1) / this.records.length * 100);
            progressEl.style.width = pct + '%';
        }
        var infoEl = document.getElementById('replay-step-info');
        if (infoEl) {
            var r = this.records[this.currentIndex];
            infoEl.innerHTML = '<div style="font-weight:600">' + (r.title || '未命名') + '</div>' +
                '<div style="font-size:12px;color:var(--text-muted)">' + (r.location || '') + ' · ' + (r.date || '') + '</div>';
        }
    },

    updateControls: function() {
        var btn = document.getElementById('replay-play-btn');
        if (btn) btn.textContent = this.playing ? '⏸️ 暂停' : '▶️ 播放';
    },

    renderControls: function() {
        var el = document.getElementById('replay-controls');
        if (!el) return;
        var self = this;
        el.innerHTML = '' +
            '<div style="display:flex;align-items:center;gap:12px;padding:12px;background:var(--bg-elevated);border-radius:12px;border:1px solid var(--border)">' +
            '  <button id="replay-play-btn" class="btn btn-primary btn-sm" onclick="ReplayEnhanced.toggle()">' + (this.playing ? '⏸️ 暂停' : '▶️ 播放') + '</button>' +
            '  <div style="flex:1">' +
            '    <div style="height:6px;background:var(--border);border-radius:3px;overflow:hidden;cursor:pointer" onclick="ReplayEnhanced.seekTo(Math.floor(event.offsetX/this.offsetWidth*' + this.records.length + '))">' +
            '      <div id="replay-progress-fill" style="height:100%;background:var(--gradient);width:0%;transition:width 0.2s"></div>' +
            '    </div>' +
            '    <div id="replay-step-info" style="margin-top:6px;font-size:12px;color:var(--text-muted)">点击播放开始回放</div>' +
            '  </div>' +
            '  <div style="display:flex;gap:4px">' +
            '    <button class="btn btn-ghost btn-sm" style="padding:4px 8px;font-size:11px' + (this.speed===0.5?';background:var(--primary);color:white':'') + '" onclick="ReplayEnhanced.setSpeed(0.5)">0.5x</button>' +
            '    <button class="btn btn-ghost btn-sm" style="padding:4px 8px;font-size:11px' + (this.speed===1?';background:var(--primary);color:white':'') + '" onclick="ReplayEnhanced.setSpeed(1)">1x</button>' +
            '    <button class="btn btn-ghost btn-sm" style="padding:4px 8px;font-size:11px' + (this.speed===2?';background:var(--primary);color:white':'') + '" onclick="ReplayEnhanced.setSpeed(2)">2x</button>' +
            '    <button class="btn btn-ghost btn-sm" style="padding:4px 8px;font-size:11px' + (this.speed===4?';background:var(--primary);color:white':'') + '" onclick="ReplayEnhanced.setSpeed(4)">4x</button>' +
            '  </div>' +
            '  <button class="btn btn-ghost btn-sm" onclick="ReplayEnhanced.exportVideo()" title="导出视频">🎬</button>' +
            '</div>';
    },

    exportVideo: function() {
        var records = this.records;
        if (!records.length) { toast('暂无记录'); return; }
        toast('🎬 正在生成视频，请等待...');

        var canvas = document.createElement('canvas');
        canvas.width = 1280;
        canvas.height = 720;
        var ctx = canvas.getContext('2d');

        var stream = canvas.captureStream(30);
        var mimeType = 'video/webm';
        if (MediaRecorder.isTypeSupported('video/webm;codecs=vp9')) {
            mimeType = 'video/webm;codecs=vp9';
        }
        var recorder = new MediaRecorder(stream, { mimeType: mimeType });
        var chunks = [];
        recorder.ondataavailable = function(e) { if (e.data.size > 0) chunks.push(e.data); };
        recorder.onstop = function() {
            var blob = new Blob(chunks, { type: mimeType });
            downloadBlob(blob, '足迹轨迹_' + new Date().toISOString().slice(0, 10) + '.webm');
            toast('✅ 视频已导出');
        };

        recorder.start();

        var lats = records.map(function(r) { return r.latitude; }).filter(Boolean);
        var lngs = records.map(function(r) { return r.longitude; }).filter(Boolean);
        if (!lats.length) { recorder.stop(); return; }
        var minLat = Math.min.apply(null, lats), maxLat = Math.max.apply(null, lats);
        var minLng = Math.min.apply(null, lngs), maxLng = Math.max.apply(null, lngs);
        var latR = (maxLat - minLat) || 0.01, lngR = (maxLng - minLng) || 0.01;

        var self = this;
        var i = 0;
        function drawNext() {
            if (i >= records.length) {
                setTimeout(function() { recorder.stop(); }, 2000);
                return;
            }
            self.drawFrame(ctx, canvas, records, i, minLat, maxLat, minLng, maxLng, latR, lngR, false);
            i++;
            setTimeout(drawNext, 800);
        }
        drawNext();
    },

    drawFrame: function(ctx, canvas, records, index, minLat, maxLat, minLng, maxLng, latR, lngR, completed) {
        var isDark = document.documentElement.dataset.theme === 'dark';
        var bg = isDark ? '#0F0F14' : '#F5F5F7';
        var textColor = isDark ? '#ffffff' : '#1D1D1F';
        var textSec = isDark ? 'rgba(255,255,255,0.7)' : 'rgba(0,0,0,0.6)';
        var textMuted = isDark ? 'rgba(255,255,255,0.4)' : 'rgba(0,0,0,0.4)';
        var primary = '#3B82F6';

        ctx.fillStyle = bg;
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        ctx.fillStyle = textColor;
        ctx.font = 'bold 28px Inter, sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText('🗺️ 足迹轨迹回放', 40, 50);

        var mapW = canvas.width * 0.62;
        var mapH = canvas.height - 140;
        var mapX = 40;
        var mapY = 80;
        var pad = 30;

        function toX(lng) { return mapX + ((lng - minLng) / lngR) * (mapW - pad * 2) + pad; }
        function toY(lat) { return mapY + mapH - ((lat - minLat) / latR) * (mapH - pad * 2) - pad; }

        // draw all path (dim)
        ctx.strokeStyle = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)';
        ctx.lineWidth = 2;
        ctx.setLineDash([6, 4]);
        ctx.beginPath();
        for (var j = 0; j < records.length; j++) {
            if (records[j].latitude && records[j].longitude) {
                var x = toX(records[j].longitude), y = toY(records[j].latitude);
                if (j === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
            }
        }
        ctx.stroke();
        ctx.setLineDash([]);

        // draw completed path
        ctx.strokeStyle = primary;
        ctx.lineWidth = 4;
        ctx.beginPath();
        for (var j = 0; j <= index; j++) {
            if (records[j].latitude && records[j].longitude) {
                var x = toX(records[j].longitude), y = toY(records[j].latitude);
                if (j === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
            }
        }
        ctx.stroke();

        // draw points
        for (var j = 0; j <= index; j++) {
            if (records[j].latitude && records[j].longitude) {
                var x = toX(records[j].longitude), y = toY(records[j].latitude);
                var isCurrent = j === index;
                ctx.beginPath();
                ctx.arc(x, y, isCurrent ? 14 : 6, 0, Math.PI * 2);
                ctx.fillStyle = isCurrent ? '#FF2442' : primary;
                ctx.fill();
                if (isCurrent) {
                    ctx.beginPath();
                    ctx.arc(x, y, 20, 0, Math.PI * 2);
                    ctx.fillStyle = 'rgba(255,36,66,0.2)';
                    ctx.fill();
                }
                ctx.fillStyle = 'white';
                ctx.font = 'bold ' + (isCurrent ? 12 : 9) + 'px Inter, sans-serif';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(String(j + 1), x, y);
            }
        }

        // sidebar
        var sx = canvas.width * 0.66;
        ctx.textAlign = 'left';
        ctx.textBaseline = 'alphabetic';
        ctx.fillStyle = textColor;
        ctx.font = 'bold 22px Inter, sans-serif';
        ctx.fillText('📍 ' + (index + 1) + ' / ' + records.length, sx, 100);

        var current = records[index] || {};
        ctx.font = '16px Inter, sans-serif';
        ctx.fillStyle = textSec;
        if (current.title) ctx.fillText(current.title, sx, 140);
        if (current.location) ctx.fillText('📍 ' + current.location, sx, 168);
        if (current.date) ctx.fillText('📅 ' + current.date, sx, 196);

        ctx.fillStyle = textColor;
        ctx.font = 'bold 16px Inter, sans-serif';
        ctx.fillText('📊 统计', sx, 250);
        ctx.font = '14px Inter, sans-serif';
        ctx.fillStyle = textSec;
        ctx.fillText('总点位: ' + records.length, sx, 278);
        ctx.fillText('已定位: ' + records.filter(function(r) { return r.latitude; }).length, sx, 302);

        // progress bar
        var barY = canvas.height - 60;
        ctx.fillStyle = isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)';
        ctx.fillRect(40, barY, canvas.width - 80, 8);
        ctx.fillStyle = primary;
        ctx.fillRect(40, barY, (canvas.width - 80) * ((index + 1) / records.length), 8);

        ctx.fillStyle = textMuted;
        ctx.font = '13px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(completed ? '✅ 回放完成' : '速度: ' + this.speed + 'x · 足迹 - 记录你的美好生活', canvas.width / 2, canvas.height - 20);
    }
};

// ========== 城市点亮模块 ==========
var CityModule = {
    cities: [],

    _extractFromLocal: function() {
        // 从本地记录中提取城市统计（与后端 /api/cities 逻辑一致）
        var records = [];
        try {
            // 优先使用全局 state.records（index.html 中的主数据）
            if (typeof state !== 'undefined' && state.records && state.records.length > 0) {
                records = state.records;
            } else {
                records = JSON.parse(localStorage.getItem('footprint_data') || '[]');
            }
        } catch (e) { records = []; }

        var cityMap = {};
        records.forEach(function(r) {
            var loc = r.location || '';
            if (!loc) return;
            var city = loc;
            var seps = ['市', '省', '区', '县', '镇'];
            for (var i = 0; i < seps.length; i++) {
                var idx = loc.indexOf(seps[i]);
                if (idx > 0) {
                    city = loc.substring(0, idx + 1);
                    break;
                }
            }
            // 进一步清洗：取「·」或「 」前的部分作为城市
            if (city.indexOf('·') > 0) city = city.split('·')[0].trim();
            if (city.indexOf(' ') > 0 && city.indexOf('·') < 0) city = city.split(' ')[0].trim();
            if (city) {
                cityMap[city] = (cityMap[city] || 0) + 1;
            }
        });

        var result = [];
        for (var k in cityMap) {
            result.push({ name: k, count: cityMap[k] });
        }
        result.sort(function(a, b) { return b.count - a.count; });
        return result;
    },

    load: function(callback) {
        var self = this;
        featureFetch('/api/cities').then(function(r) { return r.json(); }).then(function(data) {
            self.cities = data.cities || [];
            // 如果后端返回空但本地有数据，也用本地兜底
            if (self.cities.length === 0) {
                self.cities = self._extractFromLocal();
            }
            if (callback) callback();
        }).catch(function() {
            // 后端不可用，从本地记录提取城市数据
            self.cities = self._extractFromLocal();
            if (callback) callback();
        });
    },

    render: function() {
        var container = document.getElementById('modal-body-cities');
        if (!container) return;
        var totalCities = this.cities.length;

        if (totalCities === 0) {
            container.innerHTML = '' +
                '<div style="text-align:center;padding:40px 0">' +
                '  <div style="font-size:48px;margin-bottom:12px">🏙️</div>' +
                '  <div style="font-size:16px;font-weight:600;margin-bottom:8px">暂无城市数据</div>' +
                '  <div style="font-size:13px;color:var(--text-muted);line-height:1.6">' +
                '    添加足迹记录时填写「地点」字段（如"浙江杭州 · 西湖"），<br>系统将自动提取城市并生成排行榜。' +
                '  </div>' +
                '</div>';
            return;
        }

        container.innerHTML = '' +
            '<div style="text-align:center;padding:20px 0">' +
            '  <div style="font-size:48px;margin-bottom:8px">🏙️</div>' +
            '  <div style="font-size:42px;font-weight:800;background:var(--gradient);-webkit-background-clip:text;-webkit-text-fill-color:transparent">' + totalCities + '</div>' +
            '  <div style="font-size:14px;color:var(--text-muted)">已点亮城市</div>' +
            '</div>' +
            '<div style="display:flex;flex-direction:column;gap:8px;margin-top:16px">' +
            this.cities.map(function(c, i) {
                var medal = i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : '<span style="display:inline-block;width:24px;text-align:center;font-size:13px;font-weight:700;color:var(--text-muted)">' + (i + 1) + '</span>';
                return '<div style="display:flex;align-items:center;gap:12px;background:var(--bg-elevated);border:1px solid var(--border);border-radius:12px;padding:12px 16px">' +
                    '<div style="font-size:20px;min-width:28px;text-align:center">' + medal + '</div>' +
                    '<div style="flex:1;font-size:14px;font-weight:600">' + c.name + '</div>' +
                    '<div style="font-size:13px;color:var(--primary);font-weight:700">' + c.count + ' 次</div>' +
                    '</div>';
            }).join('') +
            '</div>' +
            '<div style="margin-top:20px;display:flex;gap:10px;justify-content:center">' +
            '  <button class="btn btn-primary" onclick="CityModule.generatePoster()">🖼️ 生成点亮海报</button>' +
            '  <button class="btn btn-ghost" onclick="CityModule.exportData()">📋 导出</button>' +
            '</div>';
    },

    generatePoster: function() {
        toast('🖼️ 正在生成海报...');
        var canvas = document.createElement('canvas');
        canvas.width = 1080;
        canvas.height = 1920;
        var ctx = canvas.getContext('2d');

        var grad = ctx.createLinearGradient(0, 0, 0, canvas.height);
        grad.addColorStop(0, '#0F0F14');
        grad.addColorStop(1, '#1a1a2e');
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        ctx.textAlign = 'center';
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 48px Inter, sans-serif';
        ctx.fillText('🏙️ 我的城市足迹', canvas.width / 2, 100);

        ctx.font = 'bold 80px Inter, sans-serif';
        ctx.fillStyle = '#3B82F6';
        ctx.fillText(String(this.cities.length), canvas.width / 2, 210);
        ctx.font = '24px Inter, sans-serif';
        ctx.fillStyle = 'rgba(255,255,255,0.7)';
        ctx.fillText('座城市', canvas.width / 2, 250);

        var cols = 3, cellW = 290, cellH = 110;
        var startX = (canvas.width - cols * cellW) / 2;
        var startY = 320;
        var self = this;

        this.cities.slice(0, 30).forEach(function(city, i) {
            var col = i % cols, row = Math.floor(i / cols);
            var x = startX + col * cellW + cellW / 2;
            var y = startY + row * cellH;

            ctx.fillStyle = 'rgba(255,255,255,0.06)';
            ctx.beginPath();
            ctx.roundRect(x - cellW / 2 + 10, y, cellW - 20, cellH - 10, 16);
            ctx.fill();

            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 18px Inter, sans-serif';
            ctx.fillText(city.name, x, y + 40);
            ctx.fillStyle = 'rgba(255,255,255,0.5)';
            ctx.font = '14px Inter, sans-serif';
            ctx.fillText(city.count + ' 次到访', x, y + 65);
        });

        ctx.fillStyle = 'rgba(255,255,255,0.3)';
        ctx.font = '18px Inter, sans-serif';
        ctx.fillText('足迹 - 记录你的美好生活', canvas.width / 2, canvas.height - 50);

        canvas.toBlob(function(blob) {
            downloadBlob(blob, '城市足迹_' + new Date().toISOString().slice(0, 10) + '.png');
            toast('✅ 海报已保存');
        });
    },

    exportData: function() {
        var csv = '城市,到访次数\n' + this.cities.map(function(c) { return c.name + ',' + c.count; }).join('\n');
        downloadFile(csv, '城市足迹.csv', 'text/csv');
        toast('✅ 已导出');
    }
};

// ========== 数据导出模块 ==========
var ExportModule = {
    render: function() {
        var container = document.getElementById('modal-body-export');
        if (!container) return;

        container.innerHTML = '' +
            '<div style="text-align:center;padding:20px 0">' +
            '  <div style="font-size:48px;margin-bottom:8px">📦</div>' +
            '  <div style="font-size:18px;font-weight:600">导出你的旅行数据</div>' +
            '  <div style="font-size:13px;color:var(--text-muted);margin-top:8px">支持多种格式，随时随地备份</div>' +
            '</div>' +
            '<div style="display:flex;flex-direction:column;gap:12px">' +
            '  <div class="list-item" style="cursor:pointer" onclick="ExportModule.exportGPX()">' +
            '    <div class="list-icon">🗺️</div><div class="list-content"><div class="list-title">GPX 格式</div><div class="list-desc">GPS轨迹，可导入Google Earth、两步路等</div></div><div class="list-action">→</div>' +
            '  </div>' +
            '  <div class="list-item" style="cursor:pointer" onclick="ExportModule.exportGeoJSON()">' +
            '    <div class="list-icon">🌍</div><div class="list-content"><div class="list-title">GeoJSON 格式</div><div class="list-desc">地理数据，可导入Mapbox、QGIS等</div></div><div class="list-action">→</div>' +
            '  </div>' +
            '  <div class="list-item" style="cursor:pointer" onclick="ExportModule.exportCSV()">' +
            '    <div class="list-icon">📊</div><div class="list-content"><div class="list-title">CSV 格式</div><div class="list-desc">表格格式，可用Excel打开编辑</div></div><div class="list-action">→</div>' +
            '  </div>' +
            '  <div class="list-item" style="cursor:pointer" onclick="ExportModule.exportJSON()">' +
            '    <div class="list-icon">💾</div><div class="list-content"><div class="list-title">JSON 完整备份</div><div class="list-desc">完整数据备份，可随时恢复</div></div><div class="list-action">→</div>' +
            '  </div>' +
            '</div>';
    },

    _getLocalRecords: function() {
        if (typeof state !== 'undefined' && state.records && state.records.length > 0) return state.records;
        return JSON.parse(localStorage.getItem('footprint_data') || '[]');
    },

    exportGPX: function() {
        featureFetch('/api/export/gpx').then(function(r) { return r.blob(); }).then(function(blob) {
            downloadBlob(blob, '足迹_' + new Date().toISOString().slice(0, 10) + '.gpx');
            toast('✅ GPX 已导出');
        }).catch(function() {
            // 本地生成 GPX
            var records = ExportModule._getLocalRecords();
            var gpx = '<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1" creator="Footprint">\n';
            records.forEach(function(r) {
                if (r.latitude && r.longitude) {
                    gpx += '  <wpt lat="' + r.latitude + '" lon="' + r.longitude + '">\n';
                    gpx += '    <name>' + (r.title || '').replace(/[<>&]/g, '') + '</name>\n';
                    if (r.description) gpx += '    <desc>' + r.description.replace(/[<>&]/g, '') + '</desc>\n';
                    if (r.date) gpx += '    <time>' + r.date + 'T00:00:00Z</time>\n';
                    gpx += '  </wpt>\n';
                }
            });
            gpx += '</gpx>';
            downloadFile(gpx, '足迹_' + new Date().toISOString().slice(0, 10) + '.gpx', 'application/gpx+xml');
            toast('✅ GPX 已导出（本地）');
        });
    },

    exportGeoJSON: function() {
        featureFetch('/api/export/geojson').then(function(r) { return r.blob(); }).then(function(blob) {
            downloadBlob(blob, '足迹_' + new Date().toISOString().slice(0, 10) + '.geojson');
            toast('✅ GeoJSON 已导出');
        }).catch(function() {
            var records = ExportModule._getLocalRecords();
            var geojson = {
                type: 'FeatureCollection',
                features: records.filter(function(r) { return r.latitude && r.longitude; }).map(function(r) {
                    return {
                        type: 'Feature',
                        geometry: { type: 'Point', coordinates: [r.longitude, r.latitude] },
                        properties: { title: r.title, location: r.location, date: r.date, mode: r.mode, rating: r.rating }
                    };
                })
            };
            downloadFile(JSON.stringify(geojson, null, 2), '足迹_' + new Date().toISOString().slice(0, 10) + '.geojson', 'application/geo+json');
            toast('✅ GeoJSON 已导出（本地）');
        });
    },

    exportCSV: function() {
        featureFetch('/api/export/csv').then(function(r) { return r.blob(); }).then(function(blob) {
            downloadBlob(blob, '足迹_' + new Date().toISOString().slice(0, 10) + '.csv');
            toast('✅ CSV 已导出');
        }).catch(function() {
            var records = ExportModule._getLocalRecords();
            var csv = '标题,地点,日期,模式,纬度,经度,评分,人均\n';
            records.forEach(function(r) {
                csv += '"' + (r.title || '') + '","' + (r.location || '') + '","' + (r.date || '') + '","' + (r.mode || '') + '",' +
                       (r.latitude || '') + ',' + (r.longitude || '') + ',' + (r.rating || '') + ',' + (r.price || '') + '\n';
            });
            downloadFile(csv, '足迹_' + new Date().toISOString().slice(0, 10) + '.csv', 'text/csv');
            toast('✅ CSV 已导出（本地）');
        });
    },

    exportJSON: function() {
        var data = { records: state.records, exported_at: new Date().toISOString(), version: '1.0' };
        downloadFile(JSON.stringify(data, null, 2), '足迹备份_' + new Date().toISOString().slice(0, 10) + '.json', 'application/json');
        toast('✅ JSON 已导出');
    }
};

// ========== AI 故事模块 ==========
var AIModule = {
    render: function() {
        var container = document.getElementById('modal-body-ai');
        if (!container) return;

        container.innerHTML = '' +
            '<div style="text-align:center;padding:20px 0">' +
            '  <div style="font-size:48px;margin-bottom:8px">✨</div>' +
            '  <div style="font-size:18px;font-weight:600">AI 旅行故事</div>' +
            '  <div style="font-size:13px;color:var(--text-muted);margin-top:8px">基于你的记录，生成旅行故事</div>' +
            '</div>' +
            '<div style="display:flex;gap:8px;margin-bottom:16px">' +
            '  <button class="btn btn-primary btn-sm" onclick="AIModule.generate(\'travel\')" style="flex:1">🗺️ 旅行</button>' +
            '  <button class="btn btn-ghost btn-sm" onclick="AIModule.generate(\'romantic\')" style="flex:1">💕 浪漫</button>' +
            '  <button class="btn btn-ghost btn-sm" onclick="AIModule.generate(\'foodie\')" style="flex:1">🍜 美食</button>' +
            '</div>' +
            '<div id="ai-story-result" style="background:var(--bg-elevated);border:1px solid var(--border);border-radius:12px;padding:16px;min-height:200px;white-space:pre-wrap;line-height:1.8;font-size:14px">选择风格后点击生成...</div>' +
            '<div style="margin-top:12px;display:flex;gap:8px">' +
            '  <button class="btn btn-ghost btn-sm" onclick="AIModule.copyStory()" style="flex:1">📋 复制</button>' +
            '  <button class="btn btn-ghost btn-sm" onclick="AIModule.downloadStory()" style="flex:1">💾 下载</button>' +
            '</div>';
    },

    generate: function(style) {
        var el = document.getElementById('ai-story-result');
        if (el) el.textContent = '正在生成...';

        featureFetch('/api/ai/story', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ style: style })
        }).then(function(r) { return r.json(); }).then(function(data) {
            if (el) el.textContent = data.story || '生成失败';
            toast('✅ 故事已生成');
        }).catch(function() {
            if (el) el.textContent = '生成失败，请重试';
        });
    },

    copyStory: function() {
        var el = document.getElementById('ai-story-result');
        if (el) {
            navigator.clipboard.writeText(el.textContent).then(function() {
                toast('✅ 已复制');
            });
        }
    },

    downloadStory: function() {
        var el = document.getElementById('ai-story-result');
        if (el) {
            downloadFile(el.textContent, '旅行故事_' + new Date().toISOString().slice(0, 10) + '.txt', 'text/plain');
            toast('✅ 已下载');
        }
    }
};

// ========== 分享海报模块 ==========
var ShareModule = {
    generateRecordPoster: function(recordId) {
        var record = state.records.find(function(r) { return r.id === recordId; });
        if (!record) return;
        toast('🖼️ 正在生成海报...');

        var canvas = document.createElement('canvas');
        canvas.width = 1080;
        canvas.height = 1920;
        var ctx = canvas.getContext('2d');

        var grad = ctx.createLinearGradient(0, 0, 0, canvas.height);
        grad.addColorStop(0, '#0F0F14');
        grad.addColorStop(0.5, '#1a1a2e');
        grad.addColorStop(1, '#16213e');
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        ctx.textAlign = 'center';
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 52px Inter, sans-serif';
        ctx.fillText(record.title || '未命名', canvas.width / 2, 160);

        ctx.fillStyle = 'rgba(255,255,255,0.7)';
        ctx.font = '26px Inter, sans-serif';
        if (record.location) ctx.fillText('📍 ' + record.location, canvas.width / 2, 220);
        if (record.date) ctx.fillText('📅 ' + record.date, canvas.width / 2, 258);

        if (record.description) {
            ctx.font = '22px Inter, sans-serif';
            ctx.fillStyle = 'rgba(255,255,255,0.6)';
            var lines = wrapText(record.description, 36);
            lines.slice(0, 6).forEach(function(line, i) {
                ctx.fillText(line, canvas.width / 2, 330 + i * 34);
            });
        }

        if (record.latitude && record.longitude) {
            ctx.fillStyle = 'rgba(59,130,246,0.08)';
            ctx.beginPath();
            ctx.arc(canvas.width / 2, 800, 180, 0, Math.PI * 2);
            ctx.fill();
            ctx.fillStyle = '#3B82F6';
            ctx.font = 'bold 28px Inter, sans-serif';
            ctx.fillText(record.latitude.toFixed(4) + '°N', canvas.width / 2, 790);
            ctx.fillText(record.longitude.toFixed(4) + '°E', canvas.width / 2, 825);
        }

        var imgCount = (record.images || []).length;
        ctx.fillStyle = 'rgba(255,255,255,0.8)';
        ctx.font = '22px Inter, sans-serif';
        ctx.fillText('📷 ' + imgCount + ' 张照片 · ⭐ ' + (record.rating || '未评分'), canvas.width / 2, 1080);

        var modeNames = { travel: '✈️ 旅行', food: '🍜 美食', love: '💕 情侣' };
        var modeColors = { travel: '#3B82F6', food: '#F59E0B', love: '#EC4899' };
        ctx.fillStyle = (modeColors[record.mode] || '#3B82F6') + '33';
        ctx.beginPath();
        ctx.roundRect(canvas.width / 2 - 70, canvas.height - 180, 140, 36, 18);
        ctx.fill();
        ctx.fillStyle = modeColors[record.mode] || '#3B82F6';
        ctx.font = 'bold 16px Inter, sans-serif';
        ctx.fillText(modeNames[record.mode] || '✈️ 旅行', canvas.width / 2, canvas.height - 157);

        ctx.fillStyle = 'rgba(255,255,255,0.3)';
        ctx.font = '16px Inter, sans-serif';
        ctx.fillText('足迹 - 记录你的美好生活', canvas.width / 2, canvas.height - 50);

        canvas.toBlob(function(blob) {
            downloadBlob(blob, '足迹_' + (record.title || '记录') + '.png');
            toast('✅ 海报已保存');
        });
    },

    generateSummary: function() {
        var records = state.records;
        if (!records.length) { toast('暂无记录'); return; }
        toast('📊 正在生成总结...');

        var canvas = document.createElement('canvas');
        canvas.width = 1080;
        canvas.height = 1920;
        var ctx = canvas.getContext('2d');

        ctx.fillStyle = '#0F0F14';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        ctx.textAlign = 'center';
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 44px Inter, sans-serif';
        ctx.fillText('🗺️ 我的旅行总结', canvas.width / 2, 90);

        ctx.fillStyle = '#3B82F6';
        ctx.font = 'bold 72px Inter, sans-serif';
        ctx.fillText(new Date().getFullYear().toString(), canvas.width / 2, 200);

        var stats = [
            { num: records.length, label: '记录', icon: '📝' },
            { num: records.filter(function(r) { return r.latitude; }).length, label: '定位', icon: '📍' },
            { num: records.reduce(function(s, r) { return s + (r.images || []).length; }, 0), label: '照片', icon: '📷' },
            { num: Object.keys(records.reduce(function(m, r) { m[r.mode] = 1; return m; }, {})).length, label: '模式', icon: '✨' }
        ];

        var cellSize = 190, gap = 30;
        var totalW = 2 * cellSize + gap;
        var startX = (canvas.width - totalW) / 2;
        var gridY = 280;

        stats.forEach(function(stat, i) {
            var col = i % 2, row = Math.floor(i / 2);
            var x = startX + col * (cellSize + gap);
            var y = gridY + row * (cellSize + gap);

            ctx.fillStyle = 'rgba(255,255,255,0.06)';
            ctx.beginPath();
            ctx.roundRect(x, y, cellSize, cellSize, 20);
            ctx.fill();

            ctx.fillStyle = '#ffffff';
            ctx.font = '36px Inter, sans-serif';
            ctx.fillText(stat.icon, x + cellSize / 2, y + 50);

            ctx.font = 'bold 44px Inter, sans-serif';
            ctx.fillStyle = '#3B82F6';
            ctx.fillText(String(stat.num), x + cellSize / 2, y + 110);

            ctx.font = '16px Inter, sans-serif';
            ctx.fillStyle = 'rgba(255,255,255,0.6)';
            ctx.fillText(stat.label, x + cellSize / 2, y + 142);
        });

        var recentY = 760;
        ctx.textAlign = 'left';
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 26px Inter, sans-serif';
        ctx.fillText('📋 最近记录', 60, recentY);

        records.slice(0, 8).forEach(function(r, i) {
            var y = recentY + 46 + i * 72;
            ctx.fillStyle = 'rgba(255,255,255,0.06)';
            ctx.beginPath();
            ctx.roundRect(60, y, canvas.width - 120, 58, 12);
            ctx.fill();

            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 18px Inter, sans-serif';
            ctx.fillText((i + 1) + '. ' + (r.title || '未命名'), 80, y + 26);

            ctx.fillStyle = 'rgba(255,255,255,0.5)';
            ctx.font = '14px Inter, sans-serif';
            ctx.fillText((r.location || '') + ' · ' + (r.date || ''), 80, y + 46);
        });

        ctx.textAlign = 'center';
        ctx.fillStyle = 'rgba(255,255,255,0.3)';
        ctx.font = '16px Inter, sans-serif';
        ctx.fillText('足迹 - 记录你的美好生活', canvas.width / 2, canvas.height - 40);

        canvas.toBlob(function(blob) {
            downloadBlob(blob, '旅行总结_' + new Date().toISOString().slice(0, 10) + '.png');
            toast('✅ 总结已生成');
        });
    }
};

// ========== 费用追踪模块 ==========
var ExpenseModule = {
    expenses: [],
    categories: ['交通', '住宿', '餐饮', '门票', '购物', '其他'],
    categoryIcons: { '交通': '🚗', '住宿': '🏨', '餐饮': '🍜', '门票': '🎫', '购物': '🛍️', '其他': '📦' },

    load: function(callback) {
        var self = this;
        featureFetch('/api/expenses').then(function(r) { return r.json(); }).then(function(data) {
            self.expenses = data || [];
            if (callback) callback();
        }).catch(function() {
            // 离线模式：从 localStorage 读取
            self.expenses = JSON.parse(localStorage.getItem('footprint_expenses') || '[]');
            if (callback) callback();
        });
    },

    _saveLocal: function() {
        localStorage.setItem('footprint_expenses', JSON.stringify(this.expenses));
    },

    add: function(data, callback) {
        var self = this;
        featureFetch('/api/expenses', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        }).then(function(r) { return r.json(); }).then(function(expense) {
            self.expenses.unshift(expense);
            self._saveLocal();
            if (callback) callback();
            toast('✅ 已添加');
        }).catch(function() {
            // 离线模式：本地生成记录
            data.id = 'exp_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8);
            data.date = data.date || new Date().toISOString().slice(0, 10);
            self.expenses.unshift(data);
            self._saveLocal();
            if (callback) callback();
            toast('✅ 已添加（本地）');
        });
    },

    remove: function(id) {
        var self = this;
        featureFetch('/api/expenses/' + id, { method: 'DELETE' }).then(function() {
            self.expenses = self.expenses.filter(function(e) { return e.id !== id; });
            self._saveLocal();
            self.render();
            toast('已删除');
        }).catch(function() {
            self.expenses = self.expenses.filter(function(e) { return e.id !== id; });
            self._saveLocal();
            self.render();
            toast('已删除（本地）');
        });
    },

    addFromForm: function() {
        var amount = parseFloat(document.getElementById('expense-amount').value);
        var category = document.getElementById('expense-category').value;
        var desc = document.getElementById('expense-desc').value.trim();
        if (!amount || isNaN(amount)) { toast('请输入金额'); return; }

        this.add({
            amount: amount,
            category: category,
            description: desc,
            date: new Date().toISOString().slice(0, 10),
            currency: 'CNY',
            mode: state.mode
        });
        document.getElementById('expense-amount').value = '';
        document.getElementById('expense-desc').value = '';
        var self = this;
        setTimeout(function() { self.render(); }, 300);
    },

    render: function() {
        var container = document.getElementById('modal-body-expenses');
        if (!container) return;
        var self = this;

        var total = this.expenses.reduce(function(s, e) { return s + (e.amount || 0); }, 0);
        var byCategory = {};
        this.expenses.forEach(function(e) {
            byCategory[e.category] = (byCategory[e.category] || 0) + (e.amount || 0);
        });

        container.innerHTML = '' +
            '<div style="text-align:center;padding:16px 0">' +
            '  <div style="font-size:36px;font-weight:800;background:var(--gradient);-webkit-background-clip:text;-webkit-text-fill-color:transparent">¥' + total.toFixed(2) + '</div>' +
            '  <div style="font-size:13px;color:var(--text-muted)">总费用</div>' +
            '</div>' +
            '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:16px">' +
            Object.keys(byCategory).map(function(cat) {
                return '<div class="stat-card"><div style="font-size:20px">' + (self.categoryIcons[cat] || '📦') + '</div>' +
                    '<div style="font-size:16px;font-weight:700;color:var(--primary);margin-top:4px">¥' + byCategory[cat].toFixed(0) + '</div>' +
                    '<div style="font-size:11px;color:var(--text-muted)">' + cat + '</div></div>';
            }).join('') +
            '</div>' +
            '<div style="background:var(--bg-elevated);border:1px solid var(--border);border-radius:12px;padding:12px;margin-bottom:16px">' +
            '  <div style="font-size:13px;font-weight:500;margin-bottom:8px">➕ 添加费用</div>' +
            '  <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">' +
            '    <input type="number" class="form-input" id="expense-amount" placeholder="金额">' +
            '    <select class="form-select" id="expense-category">' +
            this.categories.map(function(c) { return '<option value="' + c + '">' + (self.categoryIcons[c] || '') + ' ' + c + '</option>'; }).join('') +
            '    </select>' +
            '  </div>' +
            '  <input type="text" class="form-input" id="expense-desc" placeholder="备注" style="margin-top:8px">' +
            '  <button class="btn btn-primary btn-sm" style="margin-top:8px;width:100%" onclick="ExpenseModule.addFromForm()">添加</button>' +
            '</div>' +
            '<div style="display:flex;flex-direction:column;gap:8px;max-height:300px;overflow-y:auto">' +
            (this.expenses.length === 0 ? '<div style="text-align:center;padding:20px;color:var(--text-muted)">暂无费用记录</div>' :
            this.expenses.map(function(e) {
                return '<div class="list-item">' +
                    '<div class="list-icon">' + (self.categoryIcons[e.category] || '📦') + '</div>' +
                    '<div class="list-content"><div class="list-title">' + (e.description || e.category) + '</div>' +
                    '<div class="list-desc">' + e.category + ' · ' + (e.date || '') + '</div></div>' +
                    '<div style="font-size:15px;font-weight:600;color:var(--primary)">¥' + (e.amount || 0).toFixed(2) + '</div>' +
                    '<div class="list-action" onclick="ExpenseModule.remove(\'' + e.id + '\')">✕</div></div>';
            }).join('')) +
            '</div>';
    }
};

// ========== 运动追踪模块 ==========
var ExerciseModule = {
    tracking: false,
    positions: [],
    startTime: null,
    distance: 0,
    _watchId: null,
    _timer: null,

    start: function() {
        if (this.tracking) return;
        this.tracking = true;
        this.positions = [];
        this.startTime = Date.now();
        this.distance = 0;

        var self = this;
        this._timer = setInterval(function() { self.update(); }, 1000);

        if ('geolocation' in navigator) {
            this._watchId = navigator.geolocation.watchPosition(
                function(pos) {
                    var p = { lat: pos.coords.latitude, lng: pos.coords.longitude, time: Date.now() };
                    if (self.positions.length > 0) {
                        var prev = self.positions[self.positions.length - 1];
                        self.distance += haversine(prev.lat, prev.lng, p.lat, p.lng);
                    }
                    self.positions.push(p);
                },
                function(err) { console.error('GPS error:', err); },
                { enableHighAccuracy: true, maximumAge: 0, timeout: 10000 }
            );
        }

        toast('🏃 运动追踪已开始');
        this.render();
    },

    stop: function() {
        this.tracking = false;
        if (this._timer) clearInterval(this._timer);
        if (this._watchId) navigator.geolocation.clearWatch(this._watchId);

        if (this.positions.length >= 2) {
            this.saveAsRecord();
        }
        toast('⏹️ 运动追踪已停止');
        this.render();
    },

    saveAsRecord: function() {
        var duration = Date.now() - this.startTime;
        var mins = Math.floor(duration / 60000);
        var km = (this.distance / 1000).toFixed(2);

        var data = {
            mode: 'travel',
            title: '🏃 运动记录 ' + new Date().toLocaleDateString('zh-CN'),
            description: '距离: ' + km + 'km · 时长: ' + mins + '分钟 · 点位: ' + this.positions.length,
            latitude: this.positions[0].lat,
            longitude: this.positions[0].lng,
            date: new Date().toISOString().slice(0, 10),
            images: [],
            metadata: {
                exercise: true,
                positions: this.positions.slice(0, 500),
                distance: this.distance,
                duration: duration
            }
        };

        featureFetch('/api/records', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        }).then(function(r) {
            if (r.ok) {
                toast('✅ 运动记录已保存');
                if (typeof loadRecords === 'function') loadRecords();
            }
        });
    },

    update: function() {
        if (!this.tracking) return;
        var elapsed = Date.now() - this.startTime;
        var mins = Math.floor(elapsed / 60000);
        var secs = Math.floor((elapsed % 60000) / 1000);
        var km = (this.distance / 1000).toFixed(2);

        var el = document.getElementById('exercise-stats');
        if (el) {
            el.innerHTML = '' +
                '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px">' +
                '  <div class="stat-card"><div style="font-size:24px">⏱️</div><div style="font-size:20px;font-weight:700">' + mins + ':' + String(secs).padStart(2, '0') + '</div><div style="font-size:11px;color:var(--text-muted)">时长</div></div>' +
                '  <div class="stat-card"><div style="font-size:24px">📏</div><div style="font-size:20px;font-weight:700">' + km + '</div><div style="font-size:11px;color:var(--text-muted)">公里</div></div>' +
                '  <div class="stat-card"><div style="font-size:24px">📍</div><div style="font-size:20px;font-weight:700">' + this.positions.length + '</div><div style="font-size:11px;color:var(--text-muted)">点位</div></div>' +
                '</div>';
        }
    },

    render: function() {
        var container = document.getElementById('modal-body-exercise');
        if (!container) return;

        container.innerHTML = '' +
            '<div style="text-align:center;padding:20px 0">' +
            '  <div style="font-size:64px;margin-bottom:8px">' + (this.tracking ? '🏃' : '⏹️') + '</div>' +
            '  <div style="font-size:18px;font-weight:600">' + (this.tracking ? '追踪中...' : '运动追踪') + '</div>' +
            '  <div style="font-size:13px;color:var(--text-muted);margin-top:8px">' + (this.tracking ? '实时记录你的运动轨迹' : '点击开始记录跑步、骑行等运动') + '</div>' +
            '</div>' +
            '<div id="exercise-stats"></div>' +
            '<div style="display:flex;gap:12px;justify-content:center;margin-top:20px">' +
            (this.tracking
                ? '<button class="btn btn-danger" onclick="ExerciseModule.stop()">⏹️ 停止</button>'
                : '<button class="btn btn-primary" onclick="ExerciseModule.start()">🏃 开始追踪</button>') +
            '</div>';
    }
};

// ========== 3D 地球模块 ==========
var GlobeModule = {
    render: function() {
        var container = document.getElementById('modal-body-globe');
        if (!container) return;

        var located = state.records.filter(function(r) { return r.latitude && r.longitude; });
        if (!located.length) {
            container.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-muted)">暂无定位记录</div>';
            return;
        }

        container.innerHTML = '' +
            '<div id="globe-container" style="width:100%;height:500px;background:#0F0F14;border-radius:12px;overflow:hidden;position:relative">' +
            '  <canvas id="globe-canvas" width="600" height="500"></canvas>' +
            '</div>' +
            '<div style="text-align:center;margin-top:12px;font-size:12px;color:var(--text-muted)">🖱️ 拖拽旋转 · ' + located.length + ' 个足迹点</div>';

        var self = this;
        setTimeout(function() { self.drawGlobe(located); }, 100);
    },

    drawGlobe: function(records) {
        var canvas = document.getElementById('globe-canvas');
        if (!canvas) return;
        var ctx = canvas.getContext('2d');
        var W = canvas.width, H = canvas.height;
        var cx = W / 2, cy = H / 2;
        var R = Math.min(W, H) / 2 - 40;

        var rotX = 0.3, rotY = -1.5;
        var dragging = false, lastX, lastY;

        canvas.addEventListener('mousedown', function(e) { dragging = true; lastX = e.clientX; lastY = e.clientY; });
        canvas.addEventListener('mousemove', function(e) {
            if (!dragging) return;
            rotY += (e.clientX - lastX) * 0.01;
            rotX += (e.clientY - lastY) * 0.01;
            rotX = Math.max(-Math.PI / 2, Math.min(Math.PI / 2, rotX));
            lastX = e.clientX; lastY = e.clientY;
            draw();
        });
        canvas.addEventListener('mouseup', function() { dragging = false; });
        canvas.addEventListener('mouseleave', function() { dragging = false; });

        function project(lat, lng) {
            var phi = (90 - lat) * Math.PI / 180;
            var theta = (lng + 180) * Math.PI / 180 + rotY;
            var x = R * Math.sin(phi) * Math.cos(theta);
            var y = -R * Math.cos(phi) * Math.cos(rotX) + R * Math.sin(phi) * Math.sin(theta) * Math.sin(rotX);
            var z = R * Math.cos(phi) * Math.sin(theta) * Math.cos(rotX) + R * Math.sin(phi) * Math.sin(theta) * Math.cos(rotX);
            return { x: cx + x, y: cy + y, z: z };
        }

        function draw() {
            ctx.clearRect(0, 0, W, H);

            var grad = ctx.createRadialGradient(cx - R * 0.3, cy - R * 0.3, 0, cx, cy, R);
            grad.addColorStop(0, '#1a3a5c');
            grad.addColorStop(1, '#0a1628');
            ctx.beginPath();
            ctx.arc(cx, cy, R, 0, Math.PI * 2);
            ctx.fillStyle = grad;
            ctx.fill();

            ctx.strokeStyle = 'rgba(100,150,255,0.08)';
            ctx.lineWidth = 0.5;
            for (var lat = -80; lat <= 80; lat += 20) {
                ctx.beginPath();
                for (var lng = -180; lng <= 180; lng += 5) {
                    var p = project(lat, lng);
                    if (lng === -180) ctx.moveTo(p.x, p.y); else ctx.lineTo(p.x, p.y);
                }
                ctx.stroke();
            }
            for (var lng = -180; lng < 180; lng += 30) {
                ctx.beginPath();
                for (var lat = -90; lat <= 90; lat += 5) {
                    var p = project(lat, lng);
                    if (lat === -90) ctx.moveTo(p.x, p.y); else ctx.lineTo(p.x, p.y);
                }
                ctx.stroke();
            }

            var points3d = records.map(function(r) {
                var pp = project(r.latitude, r.longitude);
                return { r: r, p: pp };
            }).filter(function(item) { return item.p.z > 0; });

            points3d.sort(function(a, b) { return a.p.z - b.p.z; });

            points3d.forEach(function(item) {
                var size = 4 + (item.p.z / R) * 6;
                var alpha = 0.3 + (item.p.z / R) * 0.7;

                ctx.beginPath();
                ctx.arc(item.p.x, item.p.y, size, 0, Math.PI * 2);
                ctx.fillStyle = 'rgba(59,130,246,' + alpha + ')';
                ctx.fill();

                ctx.beginPath();
                ctx.arc(item.p.x, item.p.y, size + 4, 0, Math.PI * 2);
                ctx.fillStyle = 'rgba(59,130,246,' + (alpha * 0.3) + ')';
                ctx.fill();
            });

            ctx.beginPath();
            ctx.arc(cx, cy, R, 0, Math.PI * 2);
            ctx.strokeStyle = 'rgba(59,130,246,0.3)';
            ctx.lineWidth = 2;
            ctx.stroke();
        }

        var autoRotate = true;
        canvas.addEventListener('mousedown', function() { autoRotate = false; });

        function animate() {
            if (autoRotate) rotY += 0.003;
            draw();
            requestAnimationFrame(animate);
        }
        animate();
    }
};

// ========== 导入模块 ==========
var ImportModule = {
    importFromFile: function(file) {
        var reader = new FileReader();
        reader.onload = function(e) {
            try {
                var data = JSON.parse(e.target.result);
                var records = Array.isArray(data) ? data : (data.records || []);
                if (!records.length) { toast('未找到记录'); return; }

                featureFetch('/api/records/import', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ records: records, replace: false })
                }).then(function(r) { return r.json(); }).then(function(result) {
                    toast('✅ 导入 ' + (result.count || 0) + ' 条记录');
                    if (typeof loadRecords === 'function') loadRecords();
                });
            } catch (err) {
                toast('❌ 文件格式错误');
            }
        };
        reader.readAsText(file);
    }
};
