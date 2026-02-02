const { createApp } = Vue

createApp({
    data() {
        return {
            loading: true,
            tables: [],
            selectedTables: [],
            auditStatus: 'idle', // idle, running, completed, error
            auditMessage: 'Ready to start.',
            progress: 0,
            logs: [],
            reports: [],
            showReportModal: false,
            activeReport: null
        }
    },
    computed: {
        progressWidth() {
            return `${this.progress}%`
        },
        statusClass() {
            const map = {
                'idle': 'bg-gray-100 text-gray-800',
                'running': 'bg-blue-100 text-blue-800',
                'completed': 'bg-green-100 text-green-800',
                'error': 'bg-red-100 text-red-800'
            }
            return map[this.auditStatus] || 'bg-gray-100'
        }
    },
    mounted() {
        this.fetchConfig()
        this.fetchReports()
        this.connectStream()
    },
    methods: {
        async fetchConfig() {
            try {
                const res = await axios.get('/api/config')
                this.tables = res.data.tables
                // Select all by default
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
        connectStream() {
            const eventSource = new EventSource('/api/stream')
            eventSource.onmessage = (event) => {
                const data = JSON.parse(event.data)

                // Only update if state changed significantly to avoid jitter
                this.auditStatus = data.status
                this.auditMessage = data.message
                this.progress = data.progress
                this.logs = data.logs || []

                if (data.status === 'completed' && this.auditStatus !== 'completed') {
                    // Refresh reports list when done
                    this.fetchReports()
                }
            }
        },
        async startAudit() {
            if (this.selectedTables.length === 0) {
                alert("Please select at least one table.")
                return
            }
            this.auditStatus = 'running'
            this.progress = 0
            this.logs = []

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
            // In a full SPA, we might load content here.
            // For now, we just redirect or open new tab.
            window.open(`/outputs/${report.id}/Audit_Report.html`, '_blank')
        },
        selectAll() {
            this.selectedTables = [...this.tables]
        },
        deselectAll() {
            this.selectedTables = []
        }
    }
}).mount('#app')
