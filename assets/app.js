const fmtUSD = n => '$' + Number(n || 0).toLocaleString('en-US', { maximumFractionDigits: 0 });
const fmtNum = n => Number(n || 0).toLocaleString('en-US', { maximumFractionDigits: 0 });

let DATA = null;
let roiChart = null;
let puChart = null;
let currentTopHcp = [];

async function loadData() {
  const res = await fetch('data/data.json');
  DATA = await res.json();
  document.getElementById('lastUpdated').textContent =
    `데이터 기준: Part D 처방의 ${fmtNum(DATA.meta.partDPrescriberCount)}명 · Open Payments 지급대상 ${fmtNum(DATA.meta.openPaymentsRecipientCount)}명 · 매칭 ${fmtNum(DATA.meta.matchedNpiCount)}명`;
  render('ALL');
}

function productLabel(key) {
  return { ALL: '전체', ENTRESTO: 'Entresto', COSENTYX: 'Cosentyx', LUCENTIS: 'Lucentis' }[key];
}

function renderKpis(key) {
  const grid = document.getElementById('kpiGrid');
  grid.innerHTML = '';
  let cards = [];

  if (key === 'ALL') {
    cards = [
      { label: '총 처방액 (3개 제품군 합산)', value: fmtUSD(DATA.meta.overallTotalRxCost), sub: 'Entresto + Cosentyx + Lucentis' },
      { label: '총 지급액 (Novartis 전체 24개 제품)', value: fmtUSD(DATA.meta.overallTotalPaymentAllProducts), sub: '2022년 Open Payments 기준' },
      { label: '처방-지급 매칭 의사 수', value: `${fmtNum(DATA.meta.matchedNpiCount)}명`, sub: `전체 처방의 ${fmtNum(DATA.meta.partDPrescriberCount)}명 중 ${(DATA.meta.matchedNpiCount / DATA.meta.partDPrescriberCount * 100).toFixed(1)}%`, cls: 'accent' },
    ];
  } else {
    const p = DATA.products.find(p => p.product === key);
    cards = [
      { label: `${p.display} 총 처방액`, value: fmtUSD(p.rxCost), sub: `처방건수 ${fmtNum(p.rxClaims)}건 · 처방의 ${fmtNum(p.rxPrescribers)}명` },
      { label: `${p.display} 총 지급액`, value: fmtUSD(p.paymentAmount), sub: p.hasPaymentData ? `지급건수 ${fmtNum(p.paymentRecords)}건 · 대상 ${fmtNum(p.paymentRecipients)}명` : '매칭되는 지급 데이터 없음', cls: p.hasPaymentData ? '' : 'warn' },
      { label: `${p.display} ROI (처방액/지급액)`, value: p.roi ? `${fmtNum(p.roi)}x` : 'N/A', sub: p.roi ? '지급 $1당 처방 매출 배수' : '지급 데이터 부재로 산출 불가', cls: 'accent' },
    ];
  }

  for (const c of cards) {
    const el = document.createElement('div');
    el.className = 'kpi-card' + (c.cls ? ' ' + c.cls : '');
    el.innerHTML = `<div class="label">${c.label}</div><div class="value">${c.value}</div><div class="sub">${c.sub}</div>`;
    grid.appendChild(el);
  }
}

function renderRoiChart() {
  const ctx = document.getElementById('roiChart');
  const labels = DATA.products.map(p => p.display);
  const values = DATA.products.map(p => p.roi || 0);
  if (roiChart) roiChart.destroy();
  roiChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'ROI (처방액 ÷ 지급액, 배수)',
        data: values,
        backgroundColor: DATA.products.map(p => p.hasPaymentData ? '#0a5cd8' : '#c9d2db'),
        borderRadius: 6,
      }],
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const p = DATA.products[ctx.dataIndex];
              return p.hasPaymentData ? `ROI ${fmtNum(p.roi)}x (처방액 ${fmtUSD(p.rxCost)} / 지급액 ${fmtUSD(p.paymentAmount)})` : '지급 데이터 없음 - ROI 산출 불가';
            }
          }
        }
      },
      scales: { x: { title: { display: true, text: 'ROI (배수)' } } }
    }
  });
}

function renderPaidUnpaid(key) {
  const pu = DATA.paidVsUnpaid[key];
  const ctx = document.getElementById('paidUnpaidChart');
  if (puChart) puChart.destroy();
  puChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['평균 처방액 ($)', '평균 처방건수'],
      datasets: [
        { label: `지급 받음 (n=${pu.paid.n})`, data: [pu.paid.avgCost, pu.paid.avgClaims], backgroundColor: '#00a887', borderRadius: 6 },
        { label: `지급 없음 (n=${pu.unpaid.n})`, data: [pu.unpaid.avgCost, pu.unpaid.avgClaims], backgroundColor: '#c9d2db', borderRadius: 6 },
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: 'bottom' } },
      scales: { y: { beginAtZero: true } }
    }
  });

  const desc = document.getElementById('paidUnpaidDesc');
  desc.textContent = key === 'ALL'
    ? 'Novartis 제품 전반에 대한 지급 여부 기준 비교입니다. 상관관계이며 인과관계를 의미하지 않습니다.'
    : `${productLabel(key)} 지급 여부 기준 비교입니다. 상관관계이며 인과관계를 의미하지 않습니다.`;

  const cardsEl = document.getElementById('puCards');
  cardsEl.innerHTML = `
    <div class="pu-card paid">
      <h3>지급 받음 (n=${fmtNum(pu.paid.n)}명)</h3>
      <div class="pu-row"><span>평균 처방액</span><b>${fmtUSD(pu.paid.avgCost)}</b></div>
      <div class="pu-row"><span>평균 처방건수</span><b>${fmtNum(pu.paid.avgClaims)}건</b></div>
      <div class="pu-row"><span>그룹 총 처방액</span><b>${fmtUSD(pu.paid.totalCost)}</b></div>
    </div>
    <div class="pu-card unpaid">
      <h3>지급 없음 (n=${fmtNum(pu.unpaid.n)}명)</h3>
      <div class="pu-row"><span>평균 처방액</span><b>${fmtUSD(pu.unpaid.avgCost)}</b></div>
      <div class="pu-row"><span>평균 처방건수</span><b>${fmtNum(pu.unpaid.avgClaims)}건</b></div>
      <div class="pu-row"><span>그룹 총 처방액</span><b>${fmtUSD(pu.unpaid.totalCost)}</b></div>
    </div>
  `;
}

function renderHcpTable(key, filterText) {
  currentTopHcp = DATA.topHcp[key];
  const tbody = document.getElementById('hcpTableBody');
  tbody.innerHTML = '';
  const q = (filterText || '').trim().toLowerCase();
  let rank = 0;
  currentTopHcp.forEach((row) => {
    if (q && !(row.name.toLowerCase().includes(q) || row.city.toLowerCase().includes(q))) return;
    rank++;
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${rank}</td>
      <td>${row.name || '-'}</td>
      <td>${row.city || '-'}</td>
      <td>${row.specialty || '-'}</td>
      <td class="num">${fmtUSD(row.rxCost)}</td>
      <td class="num">${fmtNum(row.rxClaims)}</td>
      <td class="num">${row.paymentAmount ? fmtUSD(row.paymentAmount) : '-'}</td>
      <td>${row.matched ? '<span class="badge yes">매칭</span>' : '<span class="badge no">미매칭</span>'}</td>
    `;
    tbody.appendChild(tr);
  });
}

function render(key) {
  renderKpis(key);
  renderRoiChart();
  renderPaidUnpaid(key);
  renderHcpTable(key, document.getElementById('hcpSearch').value);
}

document.getElementById('productFilter').addEventListener('change', (e) => render(e.target.value));
document.getElementById('hcpSearch').addEventListener('input', (e) => {
  const key = document.getElementById('productFilter').value;
  renderHcpTable(key, e.target.value);
});

loadData();
