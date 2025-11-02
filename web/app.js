const state = {
  config: {},
  datasetCache: {},
  globalPoints: [],
  selected: null
};

const summaryMetrics = [
  {
    label: 'ECC strategy',
    value: (row) => row?.code ?? '—',
    detail: (row) =>
      row?.scrub_s != null
        ? `Scrub interval ${formatNumber(row.scrub_s, 1)} s`
        : ''
  },
  {
    label: 'Failure rate (FIT)',
    value: (row) => formatScientific(row?.fit),
    detail: (row) =>
      row?.p95 != null ? `95th percentile ${formatNumber(row.p95, 3)}` : ''
  },
  {
    label: 'Carbon per GiB (kg)',
    value: (row) => formatNumber(row?.carbon_kg, 2),
    detail: (row) =>
      row?.p5 != null ? `5th percentile ${formatNumber(row.p5, 3)}` : ''
  },
  {
    label: 'Latency',
    value: (row) =>
      row?.latency_ns != null
        ? `${formatNumber(row.latency_ns, 2)} ns`
        : '—',
    detail: (row) =>
      row?.esii != null && row?.nesii != null
        ? `ESII ${formatNumber(row.esii, 3)} · NESII ${formatNumber(row.nesii, 1)}%`
        : ''
  },
  {
    label: 'Area footprint',
    value: (row) =>
      row?.area_logic_mm2 != null && row?.area_macro_mm2 != null
        ? `${formatNumber(row.area_logic_mm2, 2)} + ${formatNumber(
            row.area_macro_mm2,
            2
          )} mm²`
        : '—',
    detail: () => 'Logic + macro area'
  },
  {
    label: 'Energy per scrub',
    value: (row) => `${formatScientific(row?.e_scrub_kwh)} kWh`,
    detail: (row) =>
      row?.e_leak_kwh != null
        ? `Leakage ${formatScientific(row.e_leak_kwh)} kWh`
        : ''
  }
];

init();

async function init() {
  try {
    state.config = await fetchJSON('datasets.json');
    populateDatasetSelect();
    await loadGlobalPoints();

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
    await loadDataset(event.target.value);
  });

  document.getElementById('vdd-slider').addEventListener('input', (event) => {
    const sensitivity = state.datasetCache[state.selected]?.sensitivity;
    if (sensitivity) {
      updateVoltageReadout(Number(event.target.value), sensitivity);
    }
  });
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
  const entries = Object.entries(state.config);
  const points = [];
  for (const [key, info] of entries) {
    try {
      const rows = await d3.csv(info.pareto, d3.autoType);
      if (rows.length) {
        const row = rows[0];
        points.push({ key, label: info.label, row });
        state.datasetCache[key] = state.datasetCache[key] || {};
        state.datasetCache[key].pareto = rows;
      }
    } catch (error) {
      console.warn(`Unable to load pareto data for ${key}`, error);
    }
  }
  state.globalPoints = points;
  updateScatter();
}

async function loadDataset(key) {
  state.selected = key;
  const info = state.config[key];
  if (!info) {
    return;
  }

  const cache = state.datasetCache[key] || {};
  const tasks = [];

  if (!cache.pareto) {
    tasks.push(
      d3
        .csv(info.pareto, d3.autoType)
        .then((rows) => {
          cache.pareto = rows;
        })
        .catch((error) => {
          console.error(`Failed to load pareto for ${key}`, error);
          cache.pareto = [];
        })
    );
  }

  if (!cache.archetypes) {
    tasks.push(
      fetchJSON(info.archetypes)
        .then((json) => {
          cache.archetypes = json;
        })
        .catch((error) => {
          console.error(`Failed to load archetypes for ${key}`, error);
          cache.archetypes = null;
        })
    );
  }

  if (!cache.sensitivity) {
    tasks.push(
      fetchJSON(info.sensitivity)
        .then((json) => {
          cache.sensitivity = json;
        })
        .catch((error) => {
          console.error(`Failed to load sensitivity for ${key}`, error);
          cache.sensitivity = null;
        })
    );
  }

  if (tasks.length) {
    await Promise.all(tasks);
  }

  state.datasetCache[key] = cache;

  const row = cache.pareto?.[0];
  if (row) {
    renderSummary(row);
  } else {
    showError('summary', 'No Pareto data found.');
  }

  updateFeasibleTable(cache.sensitivity);
  updateVoltageControls(cache.sensitivity);
  updateArchetypes(cache.archetypes);
  updateScatter();
}

function renderSummary(row) {
  const container = document.getElementById('summary');
  container.innerHTML = '';

  summaryMetrics.forEach((metric) => {
    const card = document.createElement('article');
    card.className = 'summary-card';

    const label = document.createElement('span');
    label.className = 'label';
    label.textContent = metric.label;

    const value = document.createElement('span');
    value.className = 'value';
    value.textContent = metric.value(row);

    card.appendChild(label);
    card.appendChild(value);

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
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    cell.colSpan = 3;
    cell.textContent = 'No sensitivity data available.';
    row.appendChild(cell);
    tbody.appendChild(row);
    return;
  }

  const { grid, choices, feasible } = sensitivity;
  grid.forEach((voltage) => {
    const key = toKey(voltage);
    const row = document.createElement('tr');
    row.dataset.vdd = key;

    const vCell = document.createElement('td');
    vCell.textContent = `${formatNumber(voltage, 2)} V`;

    const cCell = document.createElement('td');
    cCell.textContent = choices?.[key] ?? '—';

    const fCell = document.createElement('td');
    const options = feasible?.[key] ?? [];
    fCell.textContent = Array.isArray(options) && options.length ? options.join(', ') : '—';

    row.appendChild(vCell);
    row.appendChild(cCell);
    row.appendChild(fCell);
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

  slider.disabled = false;
  const grid = sensitivity.grid;
  slider.min = Math.min(...grid);
  slider.max = Math.max(...grid);
  slider.value = grid[0];

  let step = 0.01;
  if (grid.length > 1) {
    const deltas = [];
    for (let i = 1; i < grid.length; i += 1) {
      deltas.push(Math.abs(grid[i] - grid[i - 1]));
    }
    const minDelta = Math.min(...deltas.filter((d) => d > 0));
    if (Number.isFinite(minDelta) && minDelta > 0) {
      step = minDelta;
    }
  }
  slider.step = step;

  updateVoltageReadout(Number(slider.value), sensitivity);
}

function updateVoltageReadout(value, sensitivity) {
  const grid = sensitivity.grid || [];
  const choices = sensitivity.choices || {};

  if (!grid.length) {
    return;
  }

  const nearest = grid.reduce((best, candidate) =>
    Math.abs(candidate - value) < Math.abs(best - value) ? candidate : best
  );

  const key = toKey(nearest);
  const recommendation = choices[key];

  document.getElementById('vdd-value').textContent = `${formatNumber(nearest, 2)} V`;
  document.getElementById('vdd-recommendation').textContent = recommendation
    ? `${recommendation} recommended`
    : 'No preferred code at this voltage.';

  document.querySelectorAll('#feasible tbody tr').forEach((row) => {
    if (row.dataset.vdd === key) {
      row.classList.add('selected');
    } else {
      row.classList.remove('selected');
    }
  });
}

function updateArchetypes(archetypes) {
  const container = document.getElementById('archetypes');
  container.innerHTML = '';

  if (!archetypes) {
    const message = document.createElement('p');
    message.textContent = 'No archetype classification data available.';
    message.className = 'detail';
    container.appendChild(message);
    return;
  }

  const thresholds = archetypes.provenance?.thresholds || {};
  const counts = archetypes.counts || {};
  const exemplars = archetypes.exemplars || {};

  const categories = Object.keys(thresholds).length
    ? Object.keys(thresholds)
    : Object.keys(counts);

  if (!categories.length) {
    const message = document.createElement('p');
    message.textContent = 'No archetype categories defined.';
    message.className = 'detail';
    container.appendChild(message);
    return;
  }

  categories.forEach((category) => {
    const card = document.createElement('article');
    card.className = 'archetype-card';

    const heading = document.createElement('h3');
    const count = counts[category] ?? 0;
    heading.textContent = `${category} · ${count}`;
    card.appendChild(heading);

    const threshold = thresholds[category];
    if (threshold) {
      const range = document.createElement('p');
      range.textContent =
        `FIT ${formatRange(threshold.fit_lo, threshold.fit_hi)} · ` +
        `Latency ${formatRange(threshold.lat_lo, threshold.lat_hi)} · ` +
        `Carbon ${formatRange(threshold.carbon_lo, threshold.carbon_hi)}`;
      card.appendChild(range);
    }

    const exemplar = exemplars[category];
    if (exemplar) {
      const detail = document.createElement('p');
      detail.textContent =
        `Representative ${exemplar.code} (${formatNumber(
          exemplar.carbon_kg,
          2
        )} kg, FIT ${formatScientific(exemplar.fit)})`;
      card.appendChild(detail);
    }

    container.appendChild(card);
  });
}

function updateScatter() {
  const svg = d3.select('#comparison-chart');
  const node = svg.node();
  if (!node) {
    return;
  }

  const width = node.getBoundingClientRect().width || 640;
  const height = node.getBoundingClientRect().height || 320;
  const margin = { top: 16, right: 24, bottom: 48, left: 90 };

  svg.attr('viewBox', `0 0 ${width} ${height}`);
  svg.selectAll('*').remove();

  const points = state.globalPoints.filter((point) => point.row);
  if (!points.length) {
    return;
  }

  if (state.selected && state.datasetCache[state.selected]?.pareto?.[0]) {
    const current = points.find((point) => point.key === state.selected);
    if (current) {
      current.row = state.datasetCache[state.selected].pareto[0];
    }
  }

  const xValues = points.map((point) => point.row.carbon_kg).filter(isFinite);
  const yValues = points.map((point) => point.row.fit).filter((value) => value > 0);

  if (!xValues.length || !yValues.length) {
    return;
  }

  const xExtent = d3.extent(xValues);
  const yExtent = d3.extent(yValues);

  const xScale = d3
    .scaleLinear()
    .domain([Math.max(0, xExtent[0] * 0.9), xExtent[1] * 1.1])
    .range([margin.left, width - margin.right]);

  const yDomainMin = yExtent[0] === yExtent[1] ? yExtent[0] / 10 : yExtent[0];
  const yDomainMax = yExtent[0] === yExtent[1] ? yExtent[1] * 10 : yExtent[1];

  const yScale = d3
    .scaleLog()
    .domain([yDomainMin, yDomainMax])
    .range([height - margin.bottom, margin.top]);

  const xAxis = (g) =>
    g
      .attr('transform', `translate(0, ${height - margin.bottom})`)
      .call(d3.axisBottom(xScale).ticks(6))
      .call((axis) =>
        axis
          .append('text')
          .attr('x', width - margin.right)
          .attr('y', 36)
          .attr('fill', 'currentColor')
          .attr('text-anchor', 'end')
          .attr('font-weight', '600')
          .text('Carbon footprint (kg/GiB)')
      );

  const yAxis = (g) =>
    g
      .attr('transform', `translate(${margin.left}, 0)`)
      .call(d3.axisLeft(yScale).ticks(6, '.1e'))
      .call((axis) =>
        axis
          .append('text')
          .attr('x', -margin.left + 16)
          .attr('y', margin.top)
          .attr('fill', 'currentColor')
          .attr('text-anchor', 'start')
          .attr('font-weight', '600')
          .text('Failure rate (FIT)')
      );

  svg.append('g').attr('class', 'axis axis-x').call(xAxis);
  svg.append('g').attr('class', 'axis axis-y').call(yAxis);

  const pointGroup = svg.append('g').attr('class', 'points');

  const formatter = d3.format('.2e');

  pointGroup
    .selectAll('circle')
    .data(points)
    .join('circle')
    .attr('cx', (d) => xScale(d.row.carbon_kg))
    .attr('cy', (d) => yScale(Math.max(d.row.fit, yDomainMin)))
    .attr('r', (d) => (d.key === state.selected ? 9 : 6))
    .attr('fill', (d) => (d.key === state.selected ? 'var(--accent)' : 'rgba(148, 163, 184, 0.65)'))
    .attr('stroke', 'rgba(255, 255, 255, 0.85)')
    .attr('stroke-width', (d) => (d.key === state.selected ? 2.2 : 1.2))
    .append('title')
    .text((d) =>
      `${d.label}\nCarbon: ${formatNumber(d.row.carbon_kg, 2)} kg/GiB\nFIT: ${formatter(
        d.row.fit
      )}`
    );
}

async function fetchJSON(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch ${url}: ${response.status}`);
  }
  const text = await response.text();
  const cleaned = text.replace(/\bNaN\b/g, 'null');
  return JSON.parse(cleaned);
}

function showError(containerId, message) {
  const container = document.getElementById(containerId);
  if (!container) {
    return;
  }
  container.innerHTML = '';
  const error = document.createElement('p');
  error.textContent = message;
  error.className = 'detail';
  container.appendChild(error);
}

function toKey(value) {
  return typeof value === 'number' ? value.toFixed(1) : String(value);
}

function formatNumber(value, fractionDigits = 2) {
  if (!Number.isFinite(Number(value))) {
    return '—';
  }
  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits: fractionDigits,
    minimumFractionDigits: Math.min(2, fractionDigits)
  }).format(Number(value));
}

function formatScientific(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric) || numeric === 0) {
    return numeric === 0 ? '0.00e+0' : '—';
  }
  return numeric.toExponential(2);
}

function formatRange(lower, upper) {
  const lo = formatBound(lower);
  const hi = formatBound(upper);
  if (lo === '—' && hi === '—') {
    return '—';
  }
  if (hi === '∞') {
    return `≥ ${lo}`;
  }
  if (lo === '0' || lo === '0.0' || lo === '0.00') {
    return `≤ ${hi}`;
  }
  return `${lo} – ${hi}`;
}

function formatBound(value) {
  if (value == null) {
    return '—';
  }
  if (value === 'inf' || value === Infinity) {
    return '∞';
  }
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return String(value);
  }
  if (Math.abs(numeric) >= 1_000 || Math.abs(numeric) < 0.01) {
    return numeric.toExponential(1);
  }
  return formatNumber(numeric, 2);
}
