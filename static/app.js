let map;
const SVGNS = 'http://www.w3.org/2000/svg';

function riskClass(level) { return `risk risk-${level.toLowerCase()}`; }
function fmt(n, digits = 0) { return Number(n).toLocaleString(undefined, { maximumFractionDigits: digits }); }
function el(tag, attrs = {}, html) {
  const e = document.createElementNS(SVGNS, tag);
  Object.entries(attrs).forEach(([k, v]) => e.setAttribute(k, v));
  if (html !== undefined) e.innerHTML = html;
  return e;
}
function timeLabel(isoTime) {
  const hour = parseInt(isoTime.split('T')[1].slice(0, 2), 10);
  const h12 = ((hour + 11) % 12) + 1;
  return `${String(hour).padStart(2, '0')}:00`;
}
function niceDate(iso) {
  const [datePart, timePart] = iso.split('T');
  const [y, m, d] = datePart.split('-').map(Number);
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return `${months[m - 1]} ${d}, ${y} · ${timePart.slice(0, 5)} local`;
}
function tempColor(temp, min, max) {
  const t = max === min ? 0.5 : Math.max(0, Math.min(1, (temp - min) / (max - min)));
  const hue = 48 - t * 48;
  return `hsl(${hue} 95% 55%)`;
}
function niceMax(v, step) { return Math.ceil(v / step) * step; }

// Catmull-Rom -> cubic bezier smoothing for line charts.
function smoothPath(points) {
  if (points.length < 3) return 'M' + points.map(p => p.join(',')).join('L');
  let d = `M${points[0][0]},${points[0][1]}`;
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[i === 0 ? i : i - 1];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[i + 2 >= points.length ? i + 1 : i + 2];
    const cp1x = p1[0] + (p2[0] - p0[0]) / 6;
    const cp1y = p1[1] + (p2[1] - p0[1]) / 6;
    const cp2x = p2[0] - (p3[0] - p1[0]) / 6;
    const cp2y = p2[1] - (p3[1] - p1[1]) / 6;
    d += ` C${cp1x},${cp1y} ${cp2x},${cp2y} ${p2[0]},${p2[1]}`;
  }
  return d;
}

/* ---------------------------------------------------------------------
   Metrics
--------------------------------------------------------------------- */
function renderMetrics(headline) {
  const cards = [
    ['Installed capacity', `${fmt(headline.installed_kw)} kW`, headline.installedSub, 'var(--amber)'],
    ['Usable at peak heat', `${fmt(headline.usable_kw)} kW`, headline.usableSub, 'var(--cyan)'],
    ['Capacity lost to heat', `${headline.loss_pct}%`, headline.lossSub, 'var(--red)'],
    ['Assets high / critical', `${headline.hot_assets} / ${headline.total_assets}`, headline.riskSub, 'var(--orange)'],
  ];
  document.getElementById('metrics').innerHTML = cards.map(m => `
    <div class="panel metric">
      <div class="label">${m[0]}</div>
      <div class="value" style="color:${m[3]}">${m[1]}</div>
      <div class="sub" style="color:${m[3]}"><span class="sub-dot"></span><span style="color:var(--muted)">${m[2]}</span></div>
    </div>
  `).join('');
}

function computeHeadline(frames, fallbackSummary, fallbackChargerCount) {
  if (!frames || !frames.length) {
    const s = fallbackSummary;
    return {
      installed_kw: s.installed_kw, usable_kw: s.usable_kw, loss_pct: s.capacity_loss_percent,
      hot_assets: s.high_or_critical_assets, total_assets: fallbackChargerCount,
      installedSub: 'Public charger nameplate', usableSub: 'Current snapshot',
      lossSub: 'Current snapshot', riskSub: 'Current snapshot',
    };
  }
  let peak = frames[0];
  frames.forEach(f => { if (f.summary.capacity_loss_percent > peak.summary.capacity_loss_percent) peak = f; });
  const hourLbl = timeLabel(peak.analysis_time);
  return {
    installed_kw: peak.summary.installed_kw,
    usable_kw: peak.summary.usable_kw,
    loss_pct: peak.summary.capacity_loss_percent,
    hot_assets: peak.summary.high_or_critical_assets,
    total_assets: peak.chargers.length,
    installedSub: `${peak.chargers.length} DC fast chargers · 2 sites`,
    usableSub: `@ ${hourLbl} · of ${fmt(peak.summary.installed_kw)} kW installed`,
    lossSub: `@ ${hourLbl} · ${fmt(peak.summary.capacity_at_risk_kw)} kW at risk`,
    riskSub: `of fleet, worst hour ${hourLbl}`,
  };
}

/* ---------------------------------------------------------------------
   Chart 1 — usable capacity across the day (line + shaded risk band)
--------------------------------------------------------------------- */
function renderCapacityChart(frames) {
  const host = document.getElementById('capacityChart');
  const legend = document.getElementById('capacityLegend');
  if (!frames || frames.length < 2) {
    host.innerHTML = '<div class="muted">Not enough hourly data points yet — run the Heat Event Replay fetch to unlock this chart.</div>';
    legend.innerHTML = '';
    return;
  }
  const W = 920, H = 300, ML = 58, MR = 18, MT = 18, MB = 34;
  const plotW = W - ML - MR, plotH = H - MT - MB;
  const installed = frames[0].summary.installed_kw;
  const yMax = niceMax(installed * 1.08, 200);
  const yMin = 0;
  const x = i => ML + (i / (frames.length - 1)) * plotW;
  const y = v => MT + plotH - ((v - yMin) / (yMax - yMin)) * plotH;

  const svg = el('svg', { viewBox: `0 0 ${W} ${H}` });
  const defs = el('defs', {}, `
    <linearGradient id="usableFill" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="var(--cyan)" stop-opacity=".32"/>
      <stop offset="100%" stop-color="var(--cyan)" stop-opacity="0"/>
    </linearGradient>`);
  svg.appendChild(defs);

  // gridlines + y labels
  const ticks = 5;
  for (let t = 0; t <= ticks; t++) {
    const v = yMin + (t / ticks) * (yMax - yMin);
    const yy = y(v);
    svg.appendChild(el('line', { x1: ML, x2: W - MR, y1: yy, y2: yy, class: 'grid-line' }));
    svg.appendChild(el('text', { x: ML - 10, y: yy + 3, class: 'axis-label', 'text-anchor': 'end' }, fmt(v)));
  }
  svg.appendChild(el('line', { x1: ML, x2: ML, y1: MT, y2: H - MB, class: 'axis-line' }));
  svg.appendChild(el('line', { x1: ML, x2: W - MR, y1: H - MB, y2: H - MB, class: 'axis-line' }));

  // x labels
  frames.forEach((f, i) => {
    svg.appendChild(el('text', { x: x(i), y: H - MB + 18, class: 'axis-label', 'text-anchor': 'middle' }, timeLabel(f.analysis_time)));
  });

  // installed dashed line
  const instY = y(installed);
  svg.appendChild(el('line', { x1: ML, x2: W - MR, y1: instY, y2: instY, stroke: 'var(--amber)', 'stroke-width': 2, 'stroke-dasharray': '6,5' }));

  // shaded risk band between installed line and usable curve
  const usablePts = frames.map((f, i) => [x(i), y(f.summary.usable_kw)]);
  const bandTop = frames.map((_, i) => [x(i), instY]);
  const bandPath = `M${bandTop.map(p => p.join(',')).join('L')} L${usablePts.slice().reverse().map(p => p.join(',')).join('L')} Z`;
  svg.appendChild(el('path', { d: bandPath, fill: 'var(--red)', opacity: '.10' }));

  // usable area + line
  const areaPath = `${smoothPath(usablePts)} L${x(frames.length - 1)},${H - MB} L${x(0)},${H - MB} Z`;
  svg.appendChild(el('path', { d: areaPath, fill: 'url(#usableFill)' }));
  svg.appendChild(el('path', { d: smoothPath(usablePts), fill: 'none', stroke: 'var(--cyan)', 'stroke-width': 2.6 }));

  usablePts.forEach((p, i) => {
    const c = el('circle', { cx: p[0], cy: p[1], r: 4, fill: 'var(--cyan)', stroke: 'var(--bg)', 'stroke-width': 1.5 });
    c.appendChild(el('title', {}, `${timeLabel(frames[i].analysis_time)} · usable ${fmt(frames[i].summary.usable_kw)} kW (-${frames[i].summary.capacity_loss_percent}%)`));
    svg.appendChild(c);
  });

  host.innerHTML = '';
  host.appendChild(svg);

  legend.innerHTML = `
    <span class="lg-item" style="color:var(--amber)"><span class="lg-swatch dashed"></span>Installed (${fmt(installed)} kW)</span>
    <span class="lg-item" style="color:var(--cyan)"><span class="lg-swatch"></span>Usable (heat-adjusted)</span>
    <span class="lg-item" style="color:var(--red)"><span class="lg-swatch area"></span>Capacity at risk</span>
  `;
}

/* ---------------------------------------------------------------------
   Chart 2 — ambient temperature bars vs derating onset
--------------------------------------------------------------------- */
function siteAverage(frame, field) {
  const bySite = {};
  frame.chargers.forEach(c => { (bySite[c.site_name] = bySite[c.site_name] || []).push(c); });
  const vals = Object.values(bySite).map(list => {
    const nums = list.map(c => c[field]).filter(v => v !== null && v !== undefined);
    return nums.length ? nums.reduce((a, b) => a + b, 0) / nums.length : null;
  }).filter(v => v !== null);
  return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
}
function frameWorstRisk(frame) {
  const order = ['LOW', 'MODERATE', 'HIGH', 'CRITICAL'];
  return frame.chargers.reduce((worst, c) => order.indexOf(c.risk_level) > order.indexOf(worst) ? c.risk_level : worst, 'LOW');
}

function renderTempChart(frames) {
  const host = document.getElementById('tempChart');
  if (!frames || frames.length < 2) { host.innerHTML = '<div class="muted">Needs hourly replay data.</div>'; return; }
  const W = 460, H = 260, ML = 40, MR = 10, MT = 14, MB = 30;
  const plotW = W - ML - MR, plotH = H - MT - MB;
  const ONSET = 25; // reference-model derating onset, see app/services/thermal.py
  const temps = frames.map(f => siteAverage(f, 'temperature_c'));
  const yMax = niceMax(Math.max(...temps, ONSET) + 4, 5);
  const yMin = 0;
  const x = i => ML + (i + 0.5) / frames.length * plotW;
  const bw = (plotW / frames.length) * 0.52;
  const y = v => MT + plotH - (v / (yMax - yMin)) * plotH;

  const svg = el('svg', { viewBox: `0 0 ${W} ${H}` });
  [0, 0.25, 0.5, 0.75, 1].forEach(t => {
    const v = yMin + t * (yMax - yMin);
    const yy = y(v);
    svg.appendChild(el('line', { x1: ML, x2: W - MR, y1: yy, y2: yy, class: 'grid-line' }));
    svg.appendChild(el('text', { x: ML - 8, y: yy + 3, class: 'axis-label', 'text-anchor': 'end' }, Math.round(v)));
  });
  svg.appendChild(el('line', { x1: ML, x2: ML, y1: MT, y2: H - MB, class: 'axis-line' }));
  svg.appendChild(el('line', { x1: ML, x2: W - MR, y1: H - MB, y2: H - MB, class: 'axis-line' }));

  // derating onset threshold
  const oy = y(ONSET);
  svg.appendChild(el('line', { x1: ML, x2: W - MR, y1: oy, y2: oy, stroke: 'var(--muted)', 'stroke-width': 1.4, 'stroke-dasharray': '4,4' }));
  svg.appendChild(el('text', { x: W - MR, y: oy - 5, class: 'threshold-label', 'text-anchor': 'end' }, `Derating onset ${ONSET}°C`));

  frames.forEach((f, i) => {
    const v = temps[i];
    const risk = frameWorstRisk(f);
    const color = risk === 'CRITICAL' ? 'var(--red)' : (risk === 'HIGH' ? 'var(--purple)' : 'var(--green)');
    const barX = x(i) - bw / 2;
    const barY = y(v);
    const rect = el('rect', { x: barX, y: barY, width: bw, height: (H - MB) - barY, rx: 3, fill: color, opacity: risk === 'CRITICAL' ? '0.92' : '0.85' });
    rect.appendChild(el('title', {}, `${timeLabel(f.analysis_time)} · ${v.toFixed(1)}°C avg · worst risk ${risk}`));
    svg.appendChild(rect);
    svg.appendChild(el('text', { x: x(i), y: H - MB + 16, class: 'axis-label', 'text-anchor': 'middle' }, timeLabel(f.analysis_time)));
  });

  host.innerHTML = '';
  host.appendChild(svg);
}

/* ---------------------------------------------------------------------
   Chart 3 — solar irradiance (area) vs ambient heat (line), dual axis
--------------------------------------------------------------------- */
function renderSolarChart(frames) {
  const host = document.getElementById('solarChart');
  if (!frames || frames.length < 2) { host.innerHTML = '<div class="muted">Needs hourly replay data.</div>'; return; }
  const W = 460, H = 260, ML = 40, MR = 38, MT = 16, MB = 30;
  const plotW = W - ML - MR, plotH = H - MT - MB;
  const ghi = frames.map(f => siteAverage(f, 'solar_ghi'));
  const temps = frames.map(f => siteAverage(f, 'temperature_c'));
  const ghiMax = niceMax(Math.max(...ghi) * 1.12, 100);
  const tMin = Math.floor(Math.min(...temps) - 1);
  const tMax = Math.ceil(Math.max(...temps) + 1);
  const x = i => ML + (i / (frames.length - 1)) * plotW;
  const yG = v => MT + plotH - (v / ghiMax) * plotH;
  const yT = v => MT + plotH - ((v - tMin) / (tMax - tMin || 1)) * plotH;

  const svg = el('svg', { viewBox: `0 0 ${W} ${H}` });
  const defs = el('defs', {}, `
    <linearGradient id="ghiFill" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="var(--green)" stop-opacity=".4"/>
      <stop offset="100%" stop-color="var(--green)" stop-opacity="0"/>
    </linearGradient>`);
  svg.appendChild(defs);

  [0, 0.5, 1].forEach(t => {
    const v = t * ghiMax;
    const yy = yG(v);
    svg.appendChild(el('line', { x1: ML, x2: W - MR, y1: yy, y2: yy, class: 'grid-line' }));
    svg.appendChild(el('text', { x: ML - 8, y: yy + 3, class: 'axis-label', 'text-anchor': 'end' }, Math.round(v)));
  });
  svg.appendChild(el('text', { x: W - MR + 6, y: yT(tMax) + 3, class: 'axis-label' }, `${tMax}°`));
  svg.appendChild(el('text', { x: W - MR + 6, y: yT(tMin) + 3, class: 'axis-label' }, `${tMin}°`));
  svg.appendChild(el('line', { x1: ML, x2: ML, y1: MT, y2: H - MB, class: 'axis-line' }));
  svg.appendChild(el('line', { x1: ML, x2: W - MR, y1: H - MB, y2: H - MB, class: 'axis-line' }));
  frames.forEach((f, i) => svg.appendChild(el('text', { x: x(i), y: H - MB + 16, class: 'axis-label', 'text-anchor': 'middle' }, timeLabel(f.analysis_time))));

  const ghiPts = frames.map((f, i) => [x(i), yG(ghi[i])]);
  const areaPath = `${smoothPath(ghiPts)} L${x(frames.length - 1)},${H - MB} L${x(0)},${H - MB} Z`;
  svg.appendChild(el('path', { d: areaPath, fill: 'url(#ghiFill)' }));
  svg.appendChild(el('path', { d: smoothPath(ghiPts), fill: 'none', stroke: 'var(--green)', 'stroke-width': 2.2 }));

  const tempPts = frames.map((f, i) => [x(i), yT(temps[i])]);
  svg.appendChild(el('path', { d: smoothPath(tempPts), fill: 'none', stroke: 'var(--amber)', 'stroke-width': 2.2 }));
  tempPts.forEach((p, i) => {
    const c = el('circle', { cx: p[0], cy: p[1], r: 3.2, fill: 'var(--amber)' });
    c.appendChild(el('title', {}, `${timeLabel(frames[i].analysis_time)} · ${temps[i].toFixed(1)}°C · GHI ${fmt(ghi[i])} W/m²`));
    svg.appendChild(c);
  });

  // static callout on the peak-irradiance hour, echoing a live tooltip
  let peakI = 0; ghi.forEach((v, i) => { if (v > ghi[peakI]) peakI = i; });
  const px = ghiPts[peakI][0], py = ghiPts[peakI][1];
  const boxW = 118, boxH = 40;
  let bx = px - boxW / 2; bx = Math.max(ML, Math.min(W - MR - boxW, bx));
  let by = Math.max(MT, py - boxH - 12);
  const tt = el('g', { class: 'chart-tooltip' });
  tt.appendChild(el('rect', { x: bx, y: by, width: boxW, height: boxH, rx: 8 }));
  tt.appendChild(el('text', { x: bx + 9, y: by + 15, 'font-size': '10', 'font-weight': '800' }, timeLabel(frames[peakI].analysis_time)));
  tt.appendChild(el('text', { x: bx + 9, y: by + 28, 'font-size': '9.5', class: 'tt-muted' }, `GHI ${fmt(ghi[peakI])} W/m² · ${temps[peakI].toFixed(1)}°C`));
  svg.appendChild(tt);

  host.innerHTML = '';
  host.appendChild(svg);

  host.parentElement.querySelectorAll('.chart-legend').forEach(n => n.remove());
}

/* ---------------------------------------------------------------------
   Map
--------------------------------------------------------------------- */
function renderMap(data) {
  if (map) map.remove();
  map = L.map('map', { zoomControl: true });
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19, attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);

  const temps = data.heatmap.features.map(f => Number(f.properties.average_temperature)).filter(Number.isFinite);
  const min = Math.min(...temps), max = Math.max(...temps);
  document.getElementById('tempRange').textContent = `${min.toFixed(1)}°C – ${max.toFixed(1)}°C`;
  if (data.pilot) {
    document.getElementById('mapSub').textContent = `${data.pilot.name} · ${data.pilot.city}, ${data.pilot.state}`;
  }

  const layer = L.geoJSON(data.heatmap, {
    style: f => ({
      color: tempColor(Number(f.properties.average_temperature), min, max),
      fillColor: tempColor(Number(f.properties.average_temperature), min, max),
      fillOpacity: .42, weight: .7, opacity: .55
    }),
    onEachFeature: (f, l) => l.bindTooltip(`Tile ${f.properties.tile_id ?? ''} · ${Number(f.properties.average_temperature).toFixed(2)}°C`)
  }).addTo(map);
  map.fitBounds(layer.getBounds(), { padding: [12, 12] });

  const bySite = {};
  data.chargers.forEach(c => { if (!bySite[c.site_id]) bySite[c.site_id] = []; bySite[c.site_id].push(c); });
  const siteLatLng = {};
  Object.entries(bySite).forEach(([siteId, items]) => {
    const c = items[0];
    siteLatLng[siteId] = [c.latitude, c.longitude];
    const installed = items.reduce((a, x) => a + x.rated_kw, 0);
    const usable = items.reduce((a, x) => a + x.usable_kw, 0);
    const risk = items.reduce((a, x) => a + x.capacity_at_risk_kw, 0);
    const worst = items.sort((a, b) => b.capacity_loss_percent - a.capacity_loss_percent)[0];
    const marker = L.circleMarker([c.latitude, c.longitude], {
      radius: 10, color: '#ffffff', weight: 2, fillColor: worst.risk_level === 'CRITICAL' ? '#ff5b6a' : '#f5b942', fillOpacity: .95
    }).addTo(map);
    marker.bindPopup(`
      <b>${c.site_name}</b><br>${c.network}<br><br>
      ${items.length} modeled charger assets<br>
      Temperature: <b>${c.temperature_c.toFixed(2)}°C</b><br>
      Installed: <b>${fmt(installed)} kW</b><br>
      Usable: <b>${fmt(usable)} kW</b><br>
      At risk: <b>${fmt(risk)} kW</b><br><br>
      <small>Capacity values are model estimates.</small>
    `);
  });

  const rebalance = (data.actions || []).find(a => a.action_type === 'rebalance_flexible_demand');
  if (rebalance && siteLatLng[rebalance.site_id] && siteLatLng[rebalance.destination_site_id]) {
    const from = siteLatLng[rebalance.site_id];
    const to = siteLatLng[rebalance.destination_site_id];
    const flow = L.polyline([from, to], {
      color: '#4fb9ff', weight: 4, opacity: 0.9, dashArray: '1,10', className: 'flow-line'
    }).addTo(map);
    const mid = [(from[0] + to[0]) / 2, (from[1] + to[1]) / 2];
    L.marker(mid, {
      icon: L.divIcon({ className: 'flow-label', html: `<div>&#8594; ${fmt(rebalance.redirect_kw)} kW recommended rebalance</div>`, iconSize: [1, 1] })
    }).addTo(map);
    flow.bindTooltip(`Agent recommendation: shift ${fmt(rebalance.redirect_kw)} kW toward lower-risk headroom`);
  }
}

/* ---------------------------------------------------------------------
   Actions / table / trace / notes
--------------------------------------------------------------------- */
function actionIcon(type) {
  if (type.includes('rebalance')) return '<path d="M4 12h16M14 6l6 6-6 6"/>';
  if (type.includes('defer') || type.includes('shed') || type.includes('demand')) return '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>';
  return '<path d="M13 2 4 14h6l-1 8 9-12h-6z" fill="currentColor" stroke="none"/>';
}

function renderActions(actions) {
  document.getElementById('actions').innerHTML = actions.map(a => `
    <div class="action">
      <div class="ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">${actionIcon(a.action_type)}</svg></div>
      <div class="body">
        <div class="top"><span class="name">${a.title}</span><span class="priority">P${a.priority}</span></div>
        <p>${a.rationale}</p>
        <span class="tag">${a.action_type.replaceAll('_', ' ')}</span>
      </div>
    </div>
  `).join('');
}

function renderTable(chargers) {
  document.getElementById('chargerTable').innerHTML = chargers.map(c => `
    <tr>
      <td><b>${c.charger_name}</b><div class="micro">${c.network}</div></td>
      <td>${c.site_name}</td>
      <td>${c.temperature_c.toFixed(2)}°C</td>
      <td>${fmt(c.rated_kw)} kW</td>
      <td>${fmt(c.usable_kw)} kW</td>
      <td>${fmt(c.capacity_at_risk_kw)} kW</td>
      <td>${c.capacity_loss_percent}%</td>
      <td><span class="${riskClass(c.risk_level)}">${c.risk_level}</span></td>
    </tr>
  `).join('');
}

function renderTrace(trace) {
  document.getElementById('trace').innerHTML = trace.map((t, i) => `
    <div class="trace-step"><b>${i + 1}. ${t.tool}</b><div>${t.summary}</div></div>
  `).join('');
}

/* ---------------------------------------------------------------------
   Frame render (metrics/map/actions/table/trace update per selected hour;
   the three charts are computed once from the full replay set).
--------------------------------------------------------------------- */
let allFrames = null;

function renderFrame(data) {
  const live = data.data_mode !== 'simulated_demo';
  const badge = document.getElementById('modeBadge');
  badge.textContent = live ? 'FORTYGUARD DATA' : 'SIMULATED DEV MODE';
  badge.className = `badge ${live ? 'badge-live' : 'badge-demo'}`;
  document.getElementById('footDot').className = `foot-dot ${live ? '' : 'demo'}`;
  document.getElementById('footLabel').textContent = live ? 'Live FortyGuard data' : 'Simulated dev mode';
  document.getElementById('analysisTime').textContent = data.analysis_time ? `Snapshot: ${niceDate(data.analysis_time)}` : '';
  const w = document.getElementById('warning');
  if (data.data_warning) { w.classList.remove('hidden'); w.textContent = data.data_warning; }
  else { w.classList.add('hidden'); }

  renderMetrics(computeHeadline(allFrames, data.summary, data.chargers.length));
  if (data.heatmap) renderMap(data); // replay frames may omit the (large) heatmap and reuse the map already painted
  renderActions(data.actions);
  renderTable(data.chargers);
  renderTrace(data.agent_trace);
  document.getElementById('agentExplanation').textContent = data.agent_explanation;
  document.getElementById('agentMode').textContent = `Explanation mode: ${data.agent_explanation_mode}`;
  document.getElementById('modelNotes').innerHTML = `
    <p><b>Thermal model:</b> ${data.model.label}</p>
    <p>${data.model.disclaimer}</p>
    <p><b>Temperature:</b> ${data.provenance.temperature}</p>
    <p><b>Charger locations:</b> ${data.provenance.charger_locations}</p>
    <p><b>Agent:</b> ${data.provenance.agent_actions}</p>
  `;
}

let replayTimer = null;

function initReplay(frames) {
  allFrames = frames;
  renderCapacityChart(frames);
  renderTempChart(frames);
  renderSolarChart(frames);

  const panel = document.getElementById('replaySection');
  const tabsEl = document.getElementById('replayTabs');
  const playBtn = document.getElementById('replayPlay');
  panel.classList.remove('hidden');

  let active = 0;
  let worstLoss = -1;
  frames.forEach((f, i) => { if (f.summary.capacity_loss_percent > worstLoss) { worstLoss = f.summary.capacity_loss_percent; active = i; } });

  function show(i) {
    active = i;
    renderFrame(frames[i]);
    [...tabsEl.children].forEach((el, idx) => el.classList.toggle('active', idx === i));
  }

  tabsEl.innerHTML = frames.map((f, i) => `
    <div class="tab ${frameWorstRisk(f) === 'CRITICAL' ? 'risk-hot' : ''}" data-i="${i}">
      ${timeLabel(f.analysis_time)}
      <span class="tab-sub">${fmt(f.summary.usable_kw)} kW usable</span>
    </div>
  `).join('');
  [...tabsEl.children].forEach((el, i) => el.addEventListener('click', () => { stopAutoplay(); show(i); }));

  function stopAutoplay() {
    if (replayTimer) { clearInterval(replayTimer); replayTimer = null; }
    playBtn.classList.remove('playing');
    playBtn.innerHTML = '&#9654; Auto-play';
  }

  playBtn.addEventListener('click', () => {
    if (replayTimer) { stopAutoplay(); return; }
    playBtn.classList.add('playing');
    playBtn.innerHTML = '&#10074;&#10074; Pause';
    replayTimer = setInterval(() => show((active + 1) % frames.length), 1500);
  });

  show(Math.max(active, 0));
}

/* ---------------------------------------------------------------------
   Ask ThermoCharge
--------------------------------------------------------------------- */
const ASK_SUGGESTIONS = [
  'Which site needs attention first?',
  'How much revenue is at risk?',
  'Should we rebalance demand?',
  'What is our usable capacity right now?',
];

function initAsk() {
  const chipsEl = document.getElementById('askChips');
  const form = document.getElementById('askForm');
  const input = document.getElementById('askInput');
  const answerEl = document.getElementById('askAnswer');

  chipsEl.innerHTML = ASK_SUGGESTIONS.map(q => `<button type="button" class="chip">${q}</button>`).join('');
  chipsEl.querySelectorAll('.chip').forEach(btn => {
    btn.addEventListener('click', () => { input.value = btn.textContent; askQuestion(btn.textContent); });
  });

  async function askQuestion(question) {
    answerEl.classList.remove('hidden');
    answerEl.innerHTML = `<div class="ask-q">${question}</div><div class="ask-loading">Thinking through the current network state…</div>`;

    if (window.__PRELOADED_DASHBOARD__) {
      const d = window.__PRELOADED_DASHBOARD__;
      answerEl.innerHTML = `
        <div class="ask-q">${question}</div>
        <div class="ask-a">${d.agent_explanation}</div>
        <div class="micro" style="margin-top:8px;">Static design preview — the live /api/ask agent runs on the deployed backend.</div>
      `;
      return;
    }
    try {
      const res = await fetch('/api/ask', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question })
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      answerEl.innerHTML = `
        <div class="ask-q">${data.question}</div>
        <div class="ask-a">${data.answer}</div>
        <div class="micro" style="margin-top:8px;">Grounded on: ${data.grounded_on.join(', ')} · mode: ${data.mode}</div>
      `;
    } catch (err) {
      answerEl.innerHTML = `<div class="ask-q">${question}</div><div class="ask-a">Could not reach the agent: ${err.message}</div>`;
    }
  }

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const q = input.value.trim();
    if (q) askQuestion(q);
  });
}

function initSidebarNav() {
  document.querySelectorAll('.nav-item[data-target]').forEach(item => {
    item.addEventListener('click', () => {
      const target = document.getElementById(item.dataset.target);
      if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
      item.classList.add('active');
    });
  });
}

/* ---------------------------------------------------------------------
   Boot
--------------------------------------------------------------------- */
async function init() {
  initAsk();
  initSidebarNav();

  let data = window.__PRELOADED_DASHBOARD__;
  if (!data) {
    const res = await fetch('/api/dashboard');
    if (!res.ok) throw new Error(await res.text());
    data = await res.json();
  }
  renderFrame(data);

  let replay = window.__PRELOADED_REPLAY__;
  if (!replay) {
    try {
      const replayRes = await fetch('/api/replay');
      if (replayRes.ok) replay = await replayRes.json();
    } catch (e) { /* replay not available yet — single-snapshot view stands alone */ }
  }
  if (replay && replay.frames && replay.frames.length > 1) initReplay(replay.frames);
}

init().catch(err => {
  console.error(err);
  document.body.insertAdjacentHTML('afterbegin', `<div class="warning">Dashboard failed to load: ${err.message}</div>`);
});
