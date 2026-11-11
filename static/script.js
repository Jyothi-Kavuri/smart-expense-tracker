
// READ CHART DATA FROM FLASK

const chartDataElement = document.getElementById("chart-data");

if (chartDataElement && typeof Chart !== "undefined") {

    const chartData = JSON.parse(chartDataElement.textContent);


    // PIE CHART - CATEGORY WISE EXPENSES

    const pieCanvas = document.getElementById("categoryChart");

    if (pieCanvas) {

        new Chart(pieCanvas, {

            type: "doughnut",

            data: {
                labels: chartData.categories,

                datasets: [{
                    data: chartData.categoryAmounts,
                    backgroundColor: [
                        "#3986e5",
                        "#f06b83",
                        "#f5ad45",
                        "#40bca7",
                        "#9876dc",
                        "#65b6d9",
                        "#e5c44c",
                        "#9ba6b5"
                    ],
                    borderWidth: 2,
                    borderColor: "#ffffff"
                }]
            },

            options: {
                responsive: true,
                maintainAspectRatio: false,

                plugins: {
                    legend: {
                        position: "bottom"
                    },

                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.label + ": ₹" +
                                    Number(context.raw).toFixed(2);
                            }
                        }
                    }
                }
            }

        });

    }


    // BAR CHART - DAILY EXPENSES

    const barCanvas = document.getElementById("dailyChart");

    if (barCanvas) {

        new Chart(barCanvas, {

            type: "bar",

            data: {
                labels: chartData.dates,

                datasets: [{
                    label: "Daily Expenses (₹)",
                    data: chartData.dailyAmounts,
                    backgroundColor: "#62a8e8",
                    borderRadius: 5,
                    barThickness: 18
                }]
            },

            options: {
                responsive: true,
                maintainAspectRatio: false,

                plugins: {
                    legend: {
                        display: false
                    }
                },

                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return "₹" + value;
                            }
                        }
                    },

                    x: {
                        ticks: {
                            maxRotation: 45,
                            minRotation: 30
                        }
                    }
                }
            }

        });

    }

}


// DELETE CONFIRMATION

function confirmDelete() {

    return confirm(
        "Are you sure you want to delete this expense?"
    );

}
