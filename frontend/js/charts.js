let climateChart = null;

/**
 * CSS değişkenlerinden güncel tema rengini okur.
 */
function getThemeColor(variableName, fallbackColor) {
    const value = getComputedStyle(document.documentElement)
        .getPropertyValue(variableName)
        .trim();

    return value || fallbackColor;
}

/**
 * YYYY-MM değerini Türkçe ay adına dönüştürür.
 */
function formatMonth(monthValue) {
    if (!monthValue) {
        return "Bilinmeyen";
    }

    const date = new Date(`${monthValue}-01T00:00:00`);

    if (Number.isNaN(date.getTime())) {
        return monthValue;
    }

    return new Intl.DateTimeFormat("tr-TR", {
        month: "short",
        year: "numeric",
    }).format(date);
}

/**
 * Önceki grafik örneğini bellekten kaldırır.
 */
export function clearClimateChart() {
    if (climateChart) {
        climateChart.destroy();
        climateChart = null;
    }
}

/**
 * Aylık sıcaklık ve yağış verilerini aynı grafik üzerinde gösterir.
 */
export function renderClimateChart(monthlyClimate) {
    clearClimateChart();

    if (!Array.isArray(monthlyClimate) || monthlyClimate.length === 0) {
        return;
    }

    if (!window.Chart) {
        throw new Error("Chart.js kütüphanesi yüklenemedi.");
    }

    const canvas = document.getElementById("climate-chart");

    if (!canvas) {
        throw new Error("İklim grafiği alanı bulunamadı.");
    }

    const primaryColor = getThemeColor(
        "--color-primary",
        "#176b4d",
    );

    const infoColor = getThemeColor(
        "--color-info",
        "#2f6fa3",
    );

    const labels = monthlyClimate.map((item) =>
        formatMonth(item.month),
    );

    const temperatures = monthlyClimate.map(
        (item) => item.average_temperature_c ?? null,
    );

    const precipitation = monthlyClimate.map(
        (item) => item.precipitation_mm ?? null,
    );

    climateChart = new window.Chart(canvas, {
        data: {
            labels,
            datasets: [
                {
                    type: "line",
                    label: "Ortalama sıcaklık (°C)",
                    data: temperatures,
                    yAxisID: "temperature",
                    borderColor: primaryColor,
                    backgroundColor: "rgba(23, 107, 77, 0.12)",
                    borderWidth: 3,
                    pointRadius: 3,
                    pointHoverRadius: 6,
                    tension: 0.35,
                    fill: true,
                    spanGaps: true,
                },
                {
                    type: "bar",
                    label: "Toplam yağış (mm)",
                    data: precipitation,
                    yAxisID: "precipitation",
                    backgroundColor: "rgba(47, 111, 163, 0.34)",
                    borderColor: infoColor,
                    borderWidth: 1,
                    borderRadius: 6,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: "index",
                intersect: false,
            },
            plugins: {
                legend: {
                    position: "bottom",
                    labels: {
                        usePointStyle: true,
                        boxWidth: 8,
                        padding: 18,
                    },
                },
                tooltip: {
                    callbacks: {
                        label(context) {
                            const unit =
                                context.dataset.yAxisID === "temperature"
                                    ? "°C"
                                    : "mm";

                            return `${context.dataset.label}: ${context.formattedValue} ${unit}`;
                        },
                    },
                },
            },
            scales: {
                temperature: {
                    type: "linear",
                    position: "left",
                    title: {
                        display: true,
                        text: "Sıcaklık (°C)",
                    },
                    grid: {
                        color: "rgba(104, 117, 110, 0.1)",
                    },
                },
                precipitation: {
                    type: "linear",
                    position: "right",
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: "Yağış (mm)",
                    },
                    grid: {
                        drawOnChartArea: false,
                    },
                },
                x: {
                    grid: {
                        display: false,
                    },
                },
            },
        },
    });
}