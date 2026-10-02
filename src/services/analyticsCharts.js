import Chart from "chart.js/auto";

let charts = [];

function clearCharts() {
  charts.forEach(chart => chart.destroy());
  charts = [];
}

export function renderAnalyticsCharts(data) {
  clearCharts();

  if (!data.has_data) return;

  const labels = data.timeline.map(item =>
    new Date(
      item.date + "T00:00:00"
    ).toLocaleDateString(
      undefined,
      {
        month: "short",
        day: "numeric"
      }
    )
  );

  const moneyCanvas =
    document.querySelector("#moneyChart");

  if (moneyCanvas) {
    charts.push(
      new Chart(moneyCanvas, {
        type: "line",

        data: {
          labels,

          datasets: [
            {
              label: "Revenue",
              data: data.timeline.map(
                item => item.revenue
              ),
              tension: 0.35,
              fill: false
            },
            {
              label: "Spend",
              data: data.timeline.map(
                item => item.spend
              ),
              tension: 0.35,
              fill: false
            }
          ]
        },

        options: {
          responsive: true,
          maintainAspectRatio: false,

          interaction: {
            intersect: false,
            mode: "index"
          },

          plugins: {
            legend: {
              position: "bottom"
            }
          }
        }
      })
    );
  }

  const funnelCanvas =
    document.querySelector("#funnelChart");

  if (funnelCanvas) {
    charts.push(
      new Chart(funnelCanvas, {
        type: "line",

        data: {
          labels,

          datasets: [
            {
              label: "Leads",
              data: data.timeline.map(
                item => item.leads
              ),
              tension: 0.35
            },
            {
              label: "Conversions",
              data: data.timeline.map(
                item => item.conversions
              ),
              tension: 0.35
            }
          ]
        },

        options: {
          responsive: true,
          maintainAspectRatio: false,

          plugins: {
            legend: {
              position: "bottom"
            }
          }
        }
      })
    );
  }

  const platformCanvas =
    document.querySelector(
      "#platformChart"
    );

  if (
    platformCanvas &&
    data.platforms.length
  ) {
    charts.push(
      new Chart(platformCanvas, {
        type: "doughnut",

        data: {
          labels:
            data.platforms.map(
              item => item.provider
            ),

          datasets: [
            {
              data:
                data.platforms.map(
                  item => item.revenue
                )
            }
          ]
        },

        options: {
          responsive: true,
          maintainAspectRatio: false,

          plugins: {
            legend: {
              position: "bottom"
            }
          }
        }
      })
    );
  }
}
