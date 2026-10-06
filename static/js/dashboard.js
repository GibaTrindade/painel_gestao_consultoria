(function () {
    function getSeries(canvas) {
        const sourceId = canvas.dataset.sourceId;
        const node = sourceId ? document.getElementById(sourceId) : null;
        if (!node) {
            return [];
        }
        try {
            return JSON.parse(node.textContent);
        } catch (error) {
            return [];
        }
    }

    function getLineDefinitions(canvas) {
        try {
            return JSON.parse(canvas.dataset.lines || "[]");
        } catch (error) {
            return [];
        }
    }

    function getJsonData(id) {
        const node = document.getElementById(id);
        if (!node) {
            return [];
        }
        try {
            return JSON.parse(node.textContent);
        } catch (error) {
            return [];
        }
    }

    function gradientFor(chart, color) {
        const { ctx, chartArea } = chart;
        if (!chartArea) {
            return color;
        }
        const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
        gradient.addColorStop(0, color);
        gradient.addColorStop(1, "rgba(255,255,255,0.02)");
        return gradient;
    }

    function buildDatasets(chart, series, definitions) {
        return definitions.map((definition) => ({
            label: definition.label,
            data: series.map((item) => Number(item[definition.key] || 0)),
            tension: 0.42,
            borderWidth: 3,
            borderColor: definition.color,
            backgroundColor: gradientFor(chart, definition.color),
            fill: false,
            pointRadius: 4,
            pointHoverRadius: 6,
            pointBorderWidth: 2,
            pointBackgroundColor: "#ffffff",
            pointBorderColor: definition.color,
            pointHoverBackgroundColor: definition.color,
            pointHoverBorderColor: "#ffffff",
        }));
    }

    function createChart(canvas) {
        if (typeof window.Chart === "undefined") {
            return;
        }
        const series = getSeries(canvas);
        const definitions = getLineDefinitions(canvas);
        if (!series.length || !definitions.length) {
            return;
        }

        const labels = series.map((item) => item.label);
        new Chart(canvas, {
            type: canvas.dataset.chartType || "line",
            data: {
                labels,
                datasets: [],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: "index",
                    intersect: false,
                },
                layout: {
                    padding: {
                        top: 10,
                        right: 10,
                        bottom: 6,
                        left: 6,
                    },
                },
                animation: {
                    duration: 0,
                    easing: "easeOutQuart",
                },
                plugins: {
                    legend: {
                        display: false,
                    },
                    tooltip: {
                        backgroundColor: "rgba(7, 11, 24, 0.96)",
                        borderColor: "rgba(105, 177, 255, 0.34)",
                        borderWidth: 1,
                        padding: 12,
                        displayColors: true,
                        titleColor: "#d9ecff",
                        bodyColor: "#f7fbff",
                        cornerRadius: 14,
                        titleFont: {
                            family: "Segoe UI",
                            size: 12,
                            weight: "600",
                        },
                        bodyFont: {
                            family: "Segoe UI",
                            size: 11,
                        },
                        callbacks: {
                            label(context) {
                                return `${context.dataset.label}: ${Number(context.parsed.y).toFixed(1)}%`;
                            },
                        },
                    },
                },
                scales: {
                    x: {
                        ticks: {
                            color: "#52657a",
                            font: {
                                family: "Segoe UI",
                                size: 11,
                            },
                        },
                        grid: {
                            color: "#e4eaf0",
                            drawBorder: false,
                        },
                        border: {
                            display: false,
                        },
                    },
                    y: {
                        min: 0,
                        suggestedMax: 100,
                        ticks: {
                            stepSize: 20,
                            color: "#52657a",
                            callback(value) {
                                return `${value}%`;
                            },
                            font: {
                                family: "Segoe UI",
                                size: 11,
                            },
                        },
                        grid: {
                            color: "rgba(116, 168, 255, 0.12)",
                            drawBorder: false,
                        },
                        border: {
                            display: false,
                        },
                    },
                },
            },
            plugins: [
                {
                    id: "hydrateDatasets",
                    beforeInit(chart) {
                        chart.data.datasets = buildDatasets(chart, series, definitions);
                    },
                },
            ],
        });
    }

    document.querySelectorAll("[data-line-chart]").forEach(createChart);

    function createBarChart(canvas) {
        if (typeof window.Chart === "undefined") {
            return;
        }
        const series = getSeries(canvas);
        if (!series.length) {
            return;
        }

        new Chart(canvas, {
            type: "bar",
            data: {
                labels: series.map((item) => item.label),
                datasets: [
                    {
                        label: canvas.dataset.chartTitle || "Valores",
                        data: series.map((item) => Number(item.valor || 0)),
                        borderRadius: 12,
                        borderSkipped: false,
                        backgroundColor: canvas.dataset.barColor || "#39D5FF",
                        maxBarThickness: 42,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 0,
                    easing: "easeOutQuart",
                },
                plugins: {
                    legend: {
                        display: false,
                    },
                    tooltip: {
                        backgroundColor: "rgba(7, 11, 24, 0.96)",
                        borderColor: "rgba(105, 177, 255, 0.34)",
                        borderWidth: 1,
                        padding: 12,
                        titleColor: "#d9ecff",
                        bodyColor: "#f7fbff",
                        cornerRadius: 14,
                        titleFont: {
                            family: "Segoe UI",
                            size: 12,
                            weight: "600",
                        },
                        bodyFont: {
                            family: "Segoe UI",
                            size: 11,
                        },
                    },
                },
                scales: {
                    x: {
                        ticks: {
                            color: "#52657a",
                            font: {
                                family: "Segoe UI",
                                size: 11,
                            },
                        },
                        grid: {
                            display: false,
                        },
                        border: {
                            display: false,
                        },
                    },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0,
                            color: "#52657a",
                            font: {
                                family: "Segoe UI",
                                size: 11,
                            },
                        },
                        grid: {
                            color: "rgba(116, 168, 255, 0.12)",
                            drawBorder: false,
                        },
                        border: {
                            display: false,
                        },
                    },
                },
            },
        });
    }

    document.querySelectorAll("[data-bar-chart]").forEach(createBarChart);

    function createRadarChart(canvas) {
        if (typeof window.Chart === "undefined") {
            return;
        }
        const series = getSeries(canvas);
        if (!series.length) {
            return;
        }

        const maxRadarValue = Math.max(
            10,
            ...series.flatMap((item) => [
                Number(item.abaixo_meta || 0),
                Number(item.pendencias || 0),
                Number(item.justificadas || 0),
                Number(item.atingimento_medio || 0),
            ]),
        );
        const radarStep = maxRadarValue <= 25 ? 5 : maxRadarValue <= 50 ? 10 : 20;
        const radarMax = Math.ceil(maxRadarValue / radarStep) * radarStep;

        new Chart(canvas, {
            type: "radar",
            data: {
                labels: ["Nao atingimentos", "Pendencias", "Justificadas", "Atingimento medio"],
                datasets: series.map((item) => ({
                    label: item.label,
                    data: [
                        Number(item.abaixo_meta || 0),
                        Number(item.pendencias || 0),
                        Number(item.justificadas || 0),
                        Number(item.atingimento_medio || 0),
                    ],
                    borderColor: item.color || "#39D5FF",
                    backgroundColor: `${item.color || "#39D5FF"}22`,
                    pointBackgroundColor: item.color || "#39D5FF",
                    pointBorderColor: "#ffffff",
                    pointHoverBackgroundColor: "#ffffff",
                    pointHoverBorderColor: item.color || "#39D5FF",
                    borderWidth: 2,
                })),
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 0,
                    easing: "easeOutQuart",
                },
                plugins: {
                    legend: {
                        display: false,
                    },
                    tooltip: {
                        backgroundColor: "rgba(7, 11, 24, 0.96)",
                        borderColor: "rgba(105, 177, 255, 0.34)",
                        borderWidth: 1,
                        padding: 12,
                        titleColor: "#d9ecff",
                        bodyColor: "#f7fbff",
                        cornerRadius: 14,
                        titleFont: {
                            family: "Segoe UI",
                            size: 12,
                            weight: "600",
                        },
                        bodyFont: {
                            family: "Segoe UI",
                            size: 11,
                        },
                    },
                },
                scales: {
                    r: {
                        beginAtZero: true,
                        suggestedMax: radarMax,
                        angleLines: {
                            color: "rgba(116, 168, 255, 0.16)",
                        },
                        grid: {
                            color: "rgba(116, 168, 255, 0.14)",
                        },
                        pointLabels: {
                            color: "#52657a",
                            font: {
                                family: "Segoe UI",
                                size: 11,
                            },
                        },
                        ticks: {
                            stepSize: radarStep,
                            color: "#52657a",
                            backdropColor: "transparent",
                            font: {
                                family: "Segoe UI",
                                size: 10,
                            },
                        },
                    },
                },
            },
        });
    }

    document.querySelectorAll("[data-radar-chart]").forEach(createRadarChart);

    function createGauge(container) {
        const rawPercent = Math.max(0, Number(container.dataset.percent || 0));
        const percent = Math.min(rawPercent, 100);
        const color = container.dataset.color || "#7CFFB2";
        container.innerHTML = `
            <svg viewBox="0 0 200 120" class="gauge-svg" aria-hidden="true">
                <defs>
                    <filter id="gauge-glow-${Math.round(percent * 10)}" x="-100%" y="-100%" width="300%" height="300%">
                        <feGaussianBlur stdDeviation="5" result="blur"></feGaussianBlur>
                        <feMerge>
                            <feMergeNode in="blur"></feMergeNode>
                            <feMergeNode in="SourceGraphic"></feMergeNode>
                        </feMerge>
                    </filter>
                </defs>
                <path
                    d="M 22 100 A 78 78 0 0 1 178 100"
                    class="gauge-track"
                ></path>
                <path
                    d="M 22 100 A 78 78 0 0 1 178 100"
                    class="gauge-progress"
                    style="stroke:${color}; filter:url(#gauge-glow-${Math.round(percent * 10)})"
                ></path>
                <circle cx="22" cy="100" r="4" fill="rgba(255,255,255,0.22)"></circle>
                <circle cx="178" cy="100" r="4" fill="rgba(255,255,255,0.22)"></circle>
            </svg>
        `;

        const progressPath = container.querySelector(".gauge-progress");
        if (progressPath) {
            const totalLength = progressPath.getTotalLength();
            const visibleLength = (totalLength * percent) / 100;
            progressPath.setAttribute("stroke-dasharray", `${visibleLength} ${totalLength}`);
            progressPath.setAttribute("stroke-dashoffset", "0");
        }
    }

    document.querySelectorAll("[data-gauge-chart]").forEach(createGauge);

    const monthInput = document.querySelector("[data-dashboard-month-input]");
    const monthSwitcher = document.querySelector("[data-month-switcher]");
    if (monthInput && monthSwitcher) {
        monthSwitcher.querySelectorAll("[data-month-target]").forEach((button) => {
            button.addEventListener("click", () => {
                monthInput.value = button.dataset.monthTarget;
                monthInput.form.submit();
            });
        });
    }

    const workerModal = document.querySelector("[data-worker-modal]");
    const workerModalTitle = document.querySelector("[data-worker-modal-title]");
    const workerModalSubtitle = document.querySelector("[data-worker-modal-subtitle]");
    const workerModalSummary = document.querySelector("[data-worker-modal-summary]");
    const workerModalBody = document.querySelector("[data-worker-modal-body]");
    const workerData = getJsonData("dashboard-profissionais-modal-data");

    const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[char]));
    const number = value => Number(value).toLocaleString('pt-BR', {maximumFractionDigits: 2});

    function closeWorkerModal() {
        if (workerModal) {
            workerModal.hidden = true;
        }
    }

    function openWorkerModal(workerId) {
        if (!workerModal) {
            return;
        }
        const worker = workerData.find((item) => String(item.id) === String(workerId));
        if (!worker) {
            return;
        }

        workerModalTitle.textContent = `Tarefas de ${worker.nome}`;
        workerModalSubtitle.textContent = `${worker.equipe} · ${worker.competencia} · ${worker.indicador}`;
        workerModalSummary.innerHTML = `
            <span class="summary-chip">${worker.tarefas_total_count} tarefas no indicador</span>
            <span class="summary-chip">${worker.tarefas_ativas_count} metas ainda não atingidas no mês</span>
            <span class="summary-chip">${worker.tarefas_concluidas_count} metas atingidas no mês</span>
            <span class="summary-chip">Equipe: ${escapeHTML(worker.equipe)}</span>
        `;

        if (!worker.tarefas.length) {
            workerModalBody.innerHTML = '<div class="empty-state-inline">Nenhuma tarefa encontrada para este profissional no indicador atual.</div>';
        } else {
            workerModalBody.innerHTML = worker.tarefas
                .map((tarefa) => {
                    const atingida = tarefa.meta > 0 && tarefa.realizado >= tarefa.meta;
                    const statusClass = atingida ? "success" : worker.periodo_fechado ? "warning" : "info";
                    const status = atingida ? "Meta do mês atingida" : worker.periodo_fechado ? "Mês encerrado abaixo da meta" : "Meta do mês em andamento";

                    return `
                        <article class="task-card">
                            <div class="task-card-header">
                                <div>
                                    <strong>${escapeHTML(tarefa.titulo)}</strong>
                                    <p>${escapeHTML(tarefa.unidade)}</p>
                                </div>
                                <span class="tag ${statusClass}">${status}</span>
                            </div>
                            <div class="task-card-metrics">
                                <span>Meta do mês: <strong>${number(tarefa.meta)}</strong></span>
                                <span>Realizado em ${escapeHTML(worker.competencia)}: <strong>${number(tarefa.realizado)}</strong></span>
                                <span>Falta para a meta: <strong>${number(Math.max(0, tarefa.meta - tarefa.realizado))}</strong></span><span>Prazo da tarefa: ${escapeHTML(tarefa.prazo)}</span>
                            </div>
                        </article>
                    `;
                })
                .join("");
        }

        workerModal.hidden = false;
    }

    document.querySelectorAll("[data-open-worker-modal]").forEach((button) => {
        button.addEventListener("click", () => openWorkerModal(button.dataset.funcionarioId));
    });

    document.querySelectorAll("[data-close-worker-modal]").forEach((button) => {
        button.addEventListener("click", closeWorkerModal);
    });

    if (workerModal) {
        workerModal.addEventListener("click", (event) => {
            if (event.target === workerModal) {
                closeWorkerModal();
            }
        });
    }
})();
