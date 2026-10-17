import Chart from 'chart.js/auto';
import { formatNumber, formatMoney, providerName } from './analyticsFormatting.js';

let charts = [];
export function clearAnalyticsCharts() {
  charts.forEach(chart => chart.destroy());
  charts = [];
}

function applyChartTheme(chart) {
  const shell = document.querySelector('.app-shell');
  if (!shell) return;
  const styles = getComputedStyle(shell);
  const token = name => styles.getPropertyValue(name).trim();
  chart.stop();
  const light = document.documentElement.dataset.mfTheme === 'light';
  const palette = light ? ['#268f7c','#477bd5','#9470c4','#b38b46','#528d9e'] : ['#80dfc7','#84aaff','#bca1e9','#e4bc7b','#89b7c6'];
  chart.options.color = token('--mf-muted');
  chart.options.plugins.legend.labels.color = token('--mf-muted');
  Object.assign(chart.options.plugins.tooltip, {
    backgroundColor:token('--mf-surface'), titleColor:token('--mf-text'),bodyColor:token('--mf-muted'),
    borderColor:token('--mf-border'),borderWidth:1,padding:12,
  });
  chart.data.datasets.forEach((dataset,index) => {
    dataset.borderColor = chart.config.type === 'doughnut' ? token('--mf-surface') : palette[index%palette.length];
    dataset.backgroundColor = chart.config.type === 'doughnut' ? palette : palette[index%palette.length];
    dataset.pointBackgroundColor = palette[index%palette.length];
  });
  if (chart.config.type !== 'doughnut') Object.values(chart.options.scales).forEach(axis => {
    axis.ticks.color = token('--mf-muted');
    axis.grid.color = token('--mf-border');
    axis.border.color = token('--mf-border');
    axis.title.color = token('--mf-muted');
  });
  chart.update('none');
}

document.addEventListener('marketflow:appearancechange', () => {
  charts = charts.filter(chart => {
    if (!chart.canvas?.isConnected) { chart.destroy(); return false; }
    applyChartTheme(chart);
    return true;
  });
});

export function renderAnalyticsCharts(data, mode = 'money') {
  clearAnalyticsCharts();
  if (!data.has_data) return;
  const money = mode === 'money';
  const fields = money ? [['revenue','Revenue'],['spend','Ad spend']] : mode === 'traffic'
    ? [['impressions','Impressions'],['clicks','Clicks']]
    : [['leads','Leads'],['conversions','Conversions'],['message_leads','Message leads']];
  const canvas = document.querySelector('#moneyChart');
  if (canvas) charts.push(new Chart(canvas, {
    type:'line',
    data:{labels:data.timeline.map(item => new Date(item.date+'T00:00:00Z').toLocaleDateString(undefined,{month:'short',day:'numeric',timeZone:'UTC'})),
      datasets:fields.map(([key,label],index) => ({label,
        data:data.timeline.map(item => item.has_data === false ? null : item[key]),
        yAxisID:mode === 'traffic' && index === 1 ? 'clicks' : 'y',
        tension:.15,spanGaps:false,borderWidth:2,pointRadius:data.period.days>90?0:2,pointHoverRadius:5,
        borderDash:index===1?[5,4]:[],
      }))},
    options:{responsive:true,maintainAspectRatio:false,animation:false,
      interaction:{mode:'index',intersect:false},
      plugins:{legend:{position:'bottom',labels:{usePointStyle:true,boxWidth:8,boxHeight:8,padding:20,font:{size:11}}},
        tooltip:{callbacks:{label:context => `${context.dataset.label}: ${money?formatMoney(context.parsed.y,data.currency):formatNumber(context.parsed.y)}`}}},
      scales:{x:{grid:{display:false},ticks:{maxTicksLimit:8,maxRotation:0,font:{size:10}},border:{display:false},title:{display:false}},
        y:{beginAtZero:true,ticks:{maxTicksLimit:5,font:{size:10}},border:{display:false},title:{display:true,text:money?(data.currency||'Amount'):fields[0][1],font:{size:10}}},
        ...(mode==='traffic'?{clicks:{position:'right',beginAtZero:true,grid:{drawOnChartArea:false},border:{display:false},title:{display:true,text:'Clicks',font:{size:10}},ticks:{maxTicksLimit:5,font:{size:10}}}}:{})},
    },
  }));
  const platformCanvas = document.querySelector('#platformChart');
  if (platformCanvas) charts.push(new Chart(platformCanvas, {
    type:'doughnut',data:{labels:data.platforms.map(item=>providerName(item.provider)),datasets:[{data:data.platforms.map(item=>item.spend),borderWidth:4,hoverOffset:5}]},
    options:{responsive:true,maintainAspectRatio:false,cutout:'78%',animation:false,
      plugins:{legend:{display:false,labels:{}},tooltip:{callbacks:{label:context=>formatMoney(context.parsed,data.currency)}}}},
  }));
  charts.forEach(applyChartTheme);
}
