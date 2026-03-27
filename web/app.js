const state = {
  config: {},
  datasetCache: {},
  globalPoints: [],
  selected: null,
  selectedCandidateIndex: 0,
  numericFields: []
};

const viewMeta = {
  overview: {
    title: 'Overview',
    subtitle: 'Start here for a guided summary before diving into detailed analysis.'
  },
  analytics: {
    title: 'Analytics',
    subtitle: 'Read calibrated charts and voltage sensitivity with clear, proportional scales.'
  },
  reports: {
    title: 'Reports',
    subtitle: 'Inspect detailed candidate and cross-SKU tables for decision support.'
  },
  configuration: {
    title: 'Configuration',
    subtitle: 'Understand the controls and how they affect outputs.'
  },
  help: {
    title: 'Help',
    subtitle: 'Quick interpretation notes for first-time users.'
  }
};

const summaryMetrics = [
  {
    label: 'ECC strategy',
    value: (row) => row?.code ?? '—',
    detail: (row) => (row?.scrub_s != null ? `Scrub interval ${formatNumber(row.scrub_s, 1)} s` : '')
  },
  {
    label: 'Failure rate (FIT)',
    value: (row) => formatScientific(row?.fit),
    detail: (row) => (row?.p95 != null ? `95th percentile ${formatNumber(row.p95, 3)}` : '')
  },
  {
    label: 'Carbon per GiB (kg)',
    value: (row) => formatNumber(row?.carbon_kg, 2),
    detail: (row) => (row?.p5 != null ? `5th percentile ${formatNumber(row.p5, 3)}` : '')
  },
  {
    label: 'Latency',
    value: (row) => (row?.latency_ns != null ? `${formatNumber(row.latency_ns, 2)} ns` : '—'),
    detail: (row) =>
      row?.esii != null && row?.nesii != null
        ? `ESII ${formatNumber(row.esii, 3)} · NESII ${formatNumber(row.nesii, 1)}%`
        : ''
  }
];

init();

async function init() {
  wireRouting();

  try {
    state.config = await fetchJSON('datasets.json');
    populateDatasetSelect();
    await loadGlobalPoints();
    populateMetricControls();

    const firstKey = Object.keys(state.config)[0];
    if (firstKey) {
      document.getElementById('dataset').value = firstKey;
      await loadDataset(firstKey);
    }
  } catch (error) {
    console.error('Failed to initialise dashboard', error);
    showError('summary', 'Unable to load datasets manifest.');
  }

  document.getElementById('dataset').addEventListener('change', async (event) => {
    state.selectedCandidateIndex = 0;
    await loadDataset(event.target.value);
  });

  document.getElementById('candidate').addEventListener('change', (event) => {
    state.selectedCandidateIndex = Number(event.target.value) || 0;
    renderCurrentCandidate();
    updateParetoTable();
  });

  document.getElementById('leader-metric').addEventListener('change', updateLeaderboard);
  document.getElementById('leader-dir').addEventListener('change', updateLeaderboard);
  document.getElementById('x-metric').addEventListener('change', updateScatter);
  document.getElementById('y-metric').addEventListener('change', updateScatter);

  document.getElementById('vdd-slider').addEventListener('input', (event) => {
    const sensitivity = state.datasetCache[state.selected]?.sensitivity;
    if (sensitivity) updateVoltageReadout(Number(event.target.value), sensitivity);
  });

  window.addEventListener('resize', () => updateScatter());
}

function wireRouting() {
  const applyRoute = () => {
    const route = (location.hash.replace('#/', '') || 'overview').toLowerCase();
    const view = viewMeta[route] ? route : 'overview';

    document.querySelectorAll('.view').forEach((el) => el.classList.toggle('is-active', el.dataset.view === view));
    document.querySelectorAll('.nav-links a').forEach((link) => link.classList.toggle('active', link.dataset.route === view));

    document.getElementById('page-title').textContent = viewMeta[view].title;
    document.getElementById('page-subtitle').textContent = viewMeta[view].subtitle;
  };

  if (!location.hash) location.hash = '#/overview';
  window.addEventListener('hashchange', applyRoute);
  applyRoute();
}

function populateDatasetSelect() {
  const select = document.getElementById('dataset');
  select.innerHTML = '';
  for (const [key, info] of Object.entries(state.config)) {
    const option = document.createElement('option');
    option.value = key;
    option.textContent = info.label;
    select.appendChild(option);
  }
}

async function loadGlobalPoints() {
  const points = [];

  for (const [key, info] of Object.entries(state.config)) {
    try {
      const rows = await d3.csv(info.pareto, d3.autoType);
      rows.forEach((row, index) => points.push({ key, label: info.label, row, index }));
      state.datasetCache[key] = state.datasetCache[key] || {};
      state.datasetCache[key].pareto = rows;
    } catch (error) {
      console.warn(`Unable to load pareto data for ${key}`, error);
    }
  }

  state.globalPoints = points;
  inferNumericFields();
}

function inferNumericFields() {
  const firstRow = state.globalPoints[0]?.row;
  if (!firstRow) {
    state.numericFields = [];
    return;
  }

  state.numericFields = Object.keys(firstRow).filter((field) =>
    state.globalPoints.some((point) => Number.isFinite(Number(point.row[field])))
  );
}

function populateMetricControls() {
  const fields = state.numericFields.length ? state.numericFields : ['carbon_kg', 'fit', 'latency_ns'];
  populateSelect('leader-metric', fields, 'fit');
  populateSelect('x-metric', fields, 'carbon_kg');
  populateSelect('y-metric', fields, 'fit');
}

function populateSelect(id, fields, fallback) {
  const select = document.getElementById(id);
  if (!select) return;
  select.innerHTML = '';

  fields.forEach((field) => {
    const option = document.createElement('option');
    option.value = field;
    option.textContent = humanizeField(field);
    select.appendChild(option);
  });

  if (fields.includes(fallback)) select.value = fallback;
}

async function loadDataset(key) {
  state.selected = key;
  const info = state.config[key];
  if (!info) return;

  const cache = state.datasetCache[key] || {};
  const tasks = [];

  if (!cache.pareto) tasks.push(d3.csv(info.pareto, d3.autoType).then((rows) => (cache.pareto = rows)));
  if (!cache.archetypes) tasks.push(fetchJSON(info.archetypes).then((json) => (cache.archetypes = json)));
  if (!cache.sensitivity) tasks.push(fetchJSON(info.sensitivity).then((json) => (cache.sensitivity = json)));

  if (tasks.length) {
    try {
      await Promise.all(tasks);
    } catch (error) {
      console.error(`Failed to load one or more artifacts for ${key}`, error);
    }
  }

  state.datasetCache[key] = cache;
  if (state.selectedCandidateIndex >= (cache.pareto?.length || 0)) state.selectedCandidateIndex = 0;

  renderCurrentCandidate();
  populateCandidateSelect(cache.pareto || []);
  updateParetoTable();
  updateFeasibleTable(cache.sensitivity);
  updateVoltageControls(cache.sensitivity);
  updateArchetypes(cache.archetypes);
  updateLeaderboard();
  updateScatter();
  updateOverviewBlurb();
}

function updateOverviewBlurb() {
  const row = state.datasetCache[state.selected]?.pareto?.[state.selectedCandidateIndex];
  const label = state.config[state.selected]?.label || 'selected dataset';
  const text = row
    ? `${label}: ${row.code ?? 'candidate'} currently selected with FIT ${formatScientific(row.fit)} and carbon ${formatNumber(row.carbon_kg, 2)} kg.`
    : `${label}: no candidate rows available yet.`;
  document.getElementById('overview-blurb').textContent = text;
}

function renderCurrentCandidate() {
  const row = state.datasetCache[state.selected]?.pareto?.[state.selectedCandidateIndex];
  if (row) renderSummary(row);
  else showError('summary', 'No Pareto data found.');
}

function populateCandidateSelect(rows) {
  const select = document.getElementById('candidate');
  select.innerHTML = '';

  if (!rows.length) {
    const option = document.createElement('option');
    option.value = '0';
    option.textContent = 'No candidates';
    select.appendChild(option);
    select.disabled = true;
    return;
  }

  select.disabled = false;
  rows.forEach((row, idx) => {
    const option = document.createElement('option');
    option.value = String(idx);
    option.textContent = `${row.code ?? 'candidate'} · FIT ${formatScientific(row.fit)} · Carbon ${formatNumber(row.carbon_kg, 2)}`;
    select.appendChild(option);
  });

  select.value = String(state.selectedCandidateIndex);
}

function updateParetoTable() {
  const tbody = document.querySelector('#pareto-table tbody');
  tbody.innerHTML = '';
  const rows = state.datasetCache[state.selected]?.pareto || [];

  if (!rows.length) return appendEmptyRow(tbody, 4, 'No candidate rows found.');

  rows.forEach((row, idx) => {
    const tr = document.createElement('tr');
    if (idx === state.selectedCandidateIndex) tr.classList.add('selected');
    tr.innerHTML = `
      <td>${row.code ?? '—'}</td>
      <td>${formatScientific(row.fit)}</td>
      <td>${formatNumber(row.carbon_kg, 2)}</td>
      <td>${formatNumber(row.latency_ns, 2)}</td>
    `;
    tr.addEventListener('click', () => {
      state.selectedCandidateIndex = idx;
      document.getElementById('candidate').value = String(idx);
      renderCurrentCandidate();
      updateParetoTable();
      updateOverviewBlurb();
      updateScatter();
    });
    tbody.appendChild(tr);
  });
}

function renderSummary(row) {
  const container = document.getElementById('summary');
  container.innerHTML = '';

  summaryMetrics.forEach((metric) => {
    const card = document.createElement('article');
    card.className = 'summary-card';
    card.innerHTML = `<span class="label">${metric.label}</span><span class="value">${metric.value(row)}</span>`;

    const detailText = metric.detail(row);
    if (detailText) {
      const detail = document.createElement('span');
      detail.className = 'detail';
      detail.textContent = detailText;
      card.appendChild(detail);
    }
    container.appendChild(card);
  });
}

function updateFeasibleTable(sensitivity) {
  const tbody = document.querySelector('#feasible tbody');
  tbody.innerHTML = '';

  if (!sensitivity || !Array.isArray(sensitivity.grid) || !sensitivity.grid.length) {
    return appendEmptyRow(tbody, 3, 'No sensitivity data available.');
  }

  const { grid, choices, feasible } = sensitivity;
  grid.forEach((voltage) => {
    const key = toKey(voltage);
    const row = document.createElement('tr');
    row.dataset.vdd = key;
    row.innerHTML = `
      <td>${formatNumber(voltage, 2)} V</td>
      <td>${choices?.[key] ?? '—'}</td>
      <td>${Array.isArray(feasible?.[key]) && feasible[key].length ? feasible[key].join(', ') : '—'}</td>
    `;
    tbody.appendChild(row);
  });
}

function updateVoltageControls(sensitivity) {
  const slider = document.getElementById('vdd-slider');
  const valueEl = document.getElementById('vdd-value');
  const recEl = document.getElementById('vdd-recommendation');

  if (!sensitivity || !Array.isArray(sensitivity.grid) || !sensitivity.grid.length) {
    slider.disabled = true;
    valueEl.textContent = '—';
    recEl.textContent = 'No recommendation available.';
    return;
  }

  const grid = sensitivity.grid;
  slider.disabled = false;
  slider.min = Math.min(...grid);
  slider.max = Math.max(...grid);
  slider.value = grid[0];

  if (grid.length > 1) {
    const deltas = [];
    for (let i = 1; i < grid.length; i += 1) deltas.push(Math.abs(grid[i] - grid[i - 1]));
    slider.step = Math.min(...deltas.filter((d) => d > 0));
  } else {
    slider.step = 0.01;
  }

  updateVoltageReadout(Number(slider.value), sensitivity);
}

function updateVoltageReadout(value, sensitivity) {
  const grid = sensitivity.grid || [];
  const choices = sensitivity.choices || {};
  if (!grid.length) return;

  const nearest = grid.reduce((best, candidate) =>
    Math.abs(candidate - value) < Math.abs(best - value) ? candidate : best
  );

  const key = toKey(nearest);
  const recommendation = choices[key];
  document.getElementById('vdd-value').textContent = `${formatNumber(nearest, 2)} V`;
  document.getElementById('vdd-recommendation').textContent = recommendation
    ? `${recommendation} recommended`
    : 'No preferred code at this voltage.';

  document.querySelectorAll('#feasible tbody tr').forEach((row) => row.classList.toggle('selected', row.dataset.vdd === key));
}

function updateArchetypes(archetypes) {
  const container = document.getElementById('archetypes');
  container.innerHTML = '';
  if (!archetypes) return appendInfo(container, 'No archetype classification data available.');

  const thresholds = archetypes.provenance?.thresholds || {};
  const counts = archetypes.counts || {};
  const exemplars = archetypes.exemplars || {};
  const categories = Object.keys(thresholds).length ? Object.keys(thresholds) : Object.keys(counts);
  if (!categories.length) return appendInfo(container, 'No archetype categories defined.');

  categories.forEach((category) => {
    const threshold = thresholds[category];
    const exemplar = exemplars[category];

    const card = document.createElement('article');
    card.className = 'archetype-card';
    card.innerHTML = `<h4>${category} · ${counts[category] ?? 0}</h4>`;

    if (threshold) {
      const p = document.createElement('p');
      p.textContent = `FIT ${formatRange(threshold.fit_lo, threshold.fit_hi)} · Latency ${formatRange(
        threshold.lat_lo,
        threshold.lat_hi
      )} · Carbon ${formatRange(threshold.carbon_lo, threshold.carbon_hi)}`;
      card.appendChild(p);
    }

    if (exemplar) {
      const p = document.createElement('p');
      p.textContent = `Representative ${exemplar.code} (${formatNumber(exemplar.carbon_kg, 2)} kg, FIT ${formatScientific(exemplar.fit)})`;
      card.appendChild(p);
    }

    container.appendChild(card);
  });
}

function updateLeaderboard() {
  const metric = document.getElementById('leader-metric').value;
  const direction = document.getElementById('leader-dir').value;
  const tbody = document.querySelector('#leaderboard tbody');
  tbody.innerHTML = '';

  const rows = state.globalPoints
    .filter((point) => Number.isFinite(Number(point.row[metric])))
    .sort((a, b) => {
      const av = Number(a.row[metric]);
      const bv = Number(b.row[metric]);
      return direction === 'desc' ? bv - av : av - bv;
    });

  if (!rows.length) return appendEmptyRow(tbody, 3, 'No comparable rows found.');

  rows.forEach((point) => {
    const tr = document.createElement('tr');
    if (point.key === state.selected && point.index === state.selectedCandidateIndex) tr.classList.add('selected');

    tr.innerHTML = `
      <td>${point.label}</td>
      <td>${point.row.code ?? '—'}</td>
      <td>${formatMetricValue(point.row[metric])}</td>
    `;

    tr.addEventListener('click', async () => {
      document.getElementById('dataset').value = point.key;
      state.selectedCandidateIndex = point.index;
      await loadDataset(point.key);
      document.getElementById('candidate').value = String(point.index);
    });

    tbody.appendChild(tr);
  });
}

function updateScatter() {
  const metricX = document.getElementById('x-metric').value;
  const metricY = document.getElementById('y-metric').value;
  const svg = d3.select('#comparison-chart');
  const node = svg.node();
  if (!node) return;

  const width = Math.max(680, node.getBoundingClientRect().width || 680);
  const height = Math.max(390, node.getBoundingClientRect().height || 390);
  const margin = { top: 22, right: 30, bottom: 64, left: 96 };

  svg.attr('viewBox', `0 0 ${width} ${height}`);
  svg.selectAll('*').remove();

  const points = state.globalPoints.filter(
    (point) => Number.isFinite(Number(point.row[metricX])) && Number.isFinite(Number(point.row[metricY]))
  );
  if (!points.length) return;

  const xValues = points.map((point) => Number(point.row[metricX]));
  const yValues = points.map((point) => Number(point.row[metricY]));

  const xMeta = buildScaleMeta(xValues, [margin.left, width - margin.right]);
  const yMeta = buildScaleMeta(yValues, [height - margin.bottom, margin.top]);

  const xAxis = d3.axisBottom(xMeta.scale).ticks(7).tickFormat(xMeta.tickFormat);
  const yAxis = d3.axisLeft(yMeta.scale).ticks(7).tickFormat(yMeta.tickFormat);

  svg.append('g').attr('class', 'axis').attr('transform', `translate(0, ${height - margin.bottom})`).call(xAxis);
  svg.append('g').attr('class', 'axis').attr('transform', `translate(${margin.left},0)`).call(yAxis);

  svg
    .append('text')
    .attr('x', (margin.left + width - margin.right) / 2)
    .attr('y', height - 18)
    .attr('text-anchor', 'middle')
    .attr('font-weight', 600)
    .text(`${humanizeField(metricX)} ${metricUnits(metricX)}`);

  svg
    .append('text')
    .attr('transform', `translate(24, ${(margin.top + height - margin.bottom) / 2}) rotate(-90)`)
    .attr('text-anchor', 'middle')
    .attr('font-weight', 600)
    .text(`${humanizeField(metricY)} ${metricUnits(metricY)}`);

  svg
    .append('g')
    .selectAll('circle')
    .data(points)
    .join('circle')
    .attr('cx', (d) => xMeta.scale(Number(d.row[metricX])))
    .attr('cy', (d) => yMeta.scale(Number(d.row[metricY])))
    .attr('r', (d) => (d.key === state.selected && d.index === state.selectedCandidateIndex ? 7.5 : 5.2))
    .attr('fill', (d) => (d.key === state.selected ? '#3767ff' : '#8fa0c3'))
    .attr('opacity', (d) => (d.key === state.selected ? 0.92 : 0.7))
    .attr('stroke', '#fff')
    .attr('stroke-width', (d) => (d.key === state.selected && d.index === state.selectedCandidateIndex ? 2 : 1))
    .on('click', async (_, d) => {
      document.getElementById('dataset').value = d.key;
      state.selectedCandidateIndex = d.index;
      await loadDataset(d.key);
      document.getElementById('candidate').value = String(d.index);
    })
    .append('title')
    .text(
      (d) =>
        `${d.label}\n${humanizeField(metricX)}: ${formatMetricValue(d.row[metricX])}\n${humanizeField(metricY)}: ${formatMetricValue(
          d.row[metricY]
        )}`
    );

  const modeNote = `Scale mode — X: ${xMeta.mode.toUpperCase()}, Y: ${yMeta.mode.toUpperCase()}. Domains padded to reduce clipping.`;
  document.getElementById('chart-scale-note').textContent = modeNote;
  document.getElementById('scatter-description').textContent = `Cross-dataset comparison of ${humanizeField(metricX)} vs ${humanizeField(metricY)}.`;
}

function buildScaleMeta(values, range) {
  const extent = d3.extent(values);
  if (!extent || extent[0] == null || extent[1] == null) {
    return { scale: d3.scaleLinear().domain([0, 1]).range(range), mode: 'linear', tickFormat: d3.format('.2~g') };
  }

  const [lo, hi] = paddedExtent(extent);
  const crossesZero = lo <= 0 && hi >= 0;
  const ratio = lo > 0 ? hi / Math.max(lo, Number.EPSILON) : Infinity;

  if (!crossesZero && ratio >= 1000) {
    return {
      scale: d3.scaleLog().domain([Math.max(lo, Number.EPSILON), hi]).range(range),
      mode: 'log',
      tickFormat: d3.format('.1~s')
    };
  }

  return {
    scale: d3.scaleLinear().domain([lo, hi]).nice(7).range(range),
    mode: 'linear',
    tickFormat: (v) => formatMetricValue(v)
  };
}

function paddedExtent([lo, hi]) {
  if (lo === hi) {
    const delta = lo === 0 ? 1 : Math.abs(lo) * 0.1;
    return [lo - delta, hi + delta];
  }
  const span = hi - lo;
  const pad = span * 0.12;
  return [lo - pad, hi + pad];
}

function appendEmptyRow(tbody, colSpan, message) {
  const tr = document.createElement('tr');
  const td = document.createElement('td');
  td.colSpan = colSpan;
  td.textContent = message;
  tr.appendChild(td);
  tbody.appendChild(tr);
}

function appendInfo(container, message) {
  const p = document.createElement('p');
  p.textContent = message;
  container.appendChild(p);
}

async function fetchJSON(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Failed to fetch ${url}: ${response.status}`);
  const text = await response.text();
  return JSON.parse(text.replace(/\bNaN\b/g, 'null'));
}

function showError(containerId, message) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = '';
  appendInfo(container, message);
}

function toKey(value) {
  return String(value);
}

function formatNumber(value, fractionDigits = 2) {
  if (!Number.isFinite(Number(value))) return '—';
  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits: fractionDigits,
    minimumFractionDigits: Math.min(2, fractionDigits)
  }).format(Number(value));
}

function formatScientific(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric) || numeric === 0) return numeric === 0 ? '0.00e+0' : '—';
  return numeric.toExponential(2);
}

function formatRange(lower, upper) {
  const lo = formatBound(lower);
  const hi = formatBound(upper);
  if (lo === '—' && hi === '—') return '—';
  if (hi === '∞') return `≥ ${lo}`;
  if (lo === '0' || lo === '0.0' || lo === '0.00') return `≤ ${hi}`;
  return `${lo} – ${hi}`;
}

function formatBound(value) {
  if (value == null) return '—';
  if (value === 'inf' || value === Infinity) return '∞';
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return String(value);
  if (Math.abs(numeric) >= 1_000 || (Math.abs(numeric) > 0 && Math.abs(numeric) < 0.01)) return numeric.toExponential(1);
  return formatNumber(numeric, 2);
}

function humanizeField(field) {
  return String(field)
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function metricUnits(field) {
  const units = {
    fit: '(FIT)',
    carbon_kg: '(kg)',
    latency_ns: '(ns)',
    scrub_s: '(s)',
    area_logic_mm2: '(mm²)',
    area_macro_mm2: '(mm²)'
  };
  return units[field] || '';
}

function formatMetricValue(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return value == null ? '—' : String(value);
  if (Math.abs(numeric) >= 1_000 || (Math.abs(numeric) > 0 && Math.abs(numeric) < 0.01)) return numeric.toExponential(2);
  return formatNumber(numeric, 3);
}
