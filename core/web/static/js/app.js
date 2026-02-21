const { createApp } = Vue

createApp({
    data() {
        return {
            // Wizard state
            wizardStep: 0, // 0: Upload, 1: Select Scope, 2: Progress, 3: Results
            wizardSteps: ['Upload Files', 'Select Scope', 'Audit Progress', 'Results'],

            // Upload state
            configFile: null,
            dataFiles: [],
            configDragOver: false,
            dataDragOver: false,
            uploading: false,

            // Audit state
            loading: true,
            tables: [],
            selectedTables: [],
            auditStatus: 'idle', // idle, running, completed, error
            auditMessage: 'Ready to start.',
            progress: 0,
            logs: [],
            reports: [],

            // Results state
            resultsSummary: { pass: 0, warn: 0, fail: 0, error: 0, total: 0 },
            resultsDetails: [],
            resultsChart: null,
        }
    },
    computed: {
        progressWidth() {
            return `${this.progress}%`
        },
    },
    mounted() {
        this.fetchConfig()
        this.fetchReports()
        this.connectStream()
    },
    methods: {
        // ── Config & Reports ──────────────────────────────────
        async fetchConfig() {
            try {
                const res = await axios.get('/api/config')
                this.tables = res.data.tables
                this.selectedTables = [...this.tables]
                this.loading = false
            } catch (e) {
                console.error("Failed to load config", e)
                this.auditMessage = "Error loading configuration."
            }
        },
        async fetchReports() {
            try {
                const res = await axios.get('/api/reports')
                this.reports = res.data.reports
            } catch (e) {
                console.error("Failed to load reports", e)
            }
        },

        // ── SSE Live Stream ──────────────────────────────────
        connectStream() {
            const eventSource = new EventSource('/api/stream')
            eventSource.onmessage = (event) => {
                const data = JSON.parse(event.data)

                const prevStatus = this.auditStatus
                this.auditStatus = data.status
                this.auditMessage = data.message
                this.progress = data.progress
                this.logs = data.logs || []

                // Auto-switch to progress view when audit starts
                if (data.status === 'running' && this.wizardStep !== 2) {
                    this.wizardStep = 2
                }

                // Refresh reports on completion and navigate to results
                if (data.status === 'completed' && prevStatus !== 'completed') {
                    this.fetchReports()
                    this.fetchResults()
                }
            }
        },

        // ── File Upload ──────────────────────────────────────
        handleConfigDrop(event) {
            this.configDragOver = false
            const files = event.dataTransfer.files
            if (files.length > 0) {
                const file = files[0]
                if (file.name.endsWith('.yml') || file.name.endsWith('.yaml')) {
                    this.configFile = file
                } else {
                    alert('Please drop a .yml or .yaml configuration file.')
                }
            }
        },
        handleConfigSelect(event) {
            if (event.target.files.length > 0) {
                this.configFile = event.target.files[0]
            }
        },
        handleDataDrop(event) {
            this.dataDragOver = false
            const files = Array.from(event.dataTransfer.files).filter(f => f.name.endsWith('.csv'))
            if (files.length > 0) {
                this.dataFiles = [...this.dataFiles, ...files]
            } else {
                alert('Please drop .csv data files.')
            }
        },
        handleDataSelect(event) {
            if (event.target.files.length > 0) {
                this.dataFiles = [...this.dataFiles, ...Array.from(event.target.files)]
            }
        },
        async uploadFiles() {
            if (!this.configFile) return

            this.uploading = true
            const formData = new FormData()
            formData.append('config', this.configFile)
            this.dataFiles.forEach(f => formData.append('data_files', f))

            try {
                const res = await axios.post('/api/upload', formData, {
                    headers: { 'Content-Type': 'multipart/form-data' }
                })
                // Reload config after upload
                await this.fetchConfig()
                this.wizardStep = 1
            } catch (e) {
                console.error("Upload failed", e)
                alert("File upload failed. Please try again.")
            } finally {
                this.uploading = false
            }
        },
        skipUpload() {
            this.wizardStep = 1
        },
        formatSize(bytes) {
            if (bytes < 1024) return bytes + ' B'
            if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
            return (bytes / 1048576).toFixed(1) + ' MB'
        },

        // ── Audit Actions ────────────────────────────────────
        async startAudit() {
            if (this.selectedTables.length === 0) {
                alert("Please select at least one table.")
                return
            }
            this.auditStatus = 'running'
            this.progress = 0
            this.logs = []
            this.wizardStep = 2

            try {
                await axios.post('/api/audit/start', {
                    tables: this.selectedTables
                })
            } catch (e) {
                console.error("Failed to start audit", e)
                this.auditStatus = 'error'
                this.auditMessage = "Failed to trigger audit."
            }
        },
        viewReport(report) {
            window.open(`/outputs/${report.id}/Audit_Report.html`, '_blank')
        },
        selectAll() {
            this.selectedTables = [...this.tables]
        },
        deselectAll() {
            this.selectedTables = []
        },
        resetWizard() {
            this.wizardStep = 0
            this.configFile = null
            this.dataFiles = []
            this.auditStatus = 'idle'
            this.progress = 0
            this.logs = []
            this.auditMessage = 'Ready to start.'
        },
        async fetchResults() {
            try {
                const res = await axios.get('/api/audit/results')
                this.resultsSummary = res.data.summary
                this.resultsDetails = res.data.details
                this.wizardStep = 3
                this.$nextTick(() => this.renderResultsChart())
            } catch (e) {
                console.error('Failed to fetch results', e)
            }
        },
        renderResultsChart() {
            const canvas = document.getElementById('resultsChart')
            if (!canvas) return

            // Destroy old chart if it exists
            if (this.resultsChart) {
                this.resultsChart.destroy()
            }

            const s = this.resultsSummary
            this.resultsChart = new Chart(canvas, {
                type: 'doughnut',
                data: {
                    labels: ['Pass', 'Warn', 'Fail', 'Error'],
                    datasets: [{
                        data: [s.pass, s.warn, s.fail, s.error],
                        backgroundColor: [
                            '#10b981', // emerald-500
                            '#f59e0b', // amber-500
                            '#ef4444', // red-500
                            '#64748b', // slate-500
                        ],
                        borderColor: 'transparent',
                        borderWidth: 0,
                        hoverOffset: 8,
                    }],
                },
                options: {
                    responsive: true,
                    cutout: '65%',
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: 'rgba(15, 23, 42, 0.9)',
                            titleColor: '#f1f5f9',
                            bodyColor: '#cbd5e1',
                            borderColor: 'rgba(148, 163, 184, 0.2)',
                            borderWidth: 1,
                            cornerRadius: 8,
                            padding: 12,
                        },
                    },
                },
            })
        },
    }
}).mount('#app')
