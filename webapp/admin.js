// admin.js - Admin Reports Dashboard

// State
let currentPage = 1;
let totalReports = 0;
let allReports = [];

// Format functions
const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-GB', { month: '2-digit', day: '2-digit', year: '2-digit' });
};

const formatTime = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
};

const formatUSD = (val) => {
    if (val === null || val === undefined) return '$0.00';
    const sign = val >= 0 ? '+' : '';
    return `${sign}$${val.toFixed(2)}`;
};

const getReasonBadge = (code) => {
    switch(code) {
        case 'ANALYSIS_ERROR': return 'badge-error';
        case 'DATA_ERROR': return 'badge-data';
        case 'BUG': return 'badge-bug';
        case 'OTHER': return 'badge-other';
        default: return 'badge-other';
    }
};

const getResultClass = (code) => {
    switch(code) {
        case 'WIN': return 'result-win';
        case 'LOSS': return 'result-loss';
        case 'MISSED': return 'result-miss';
        default: return '';
    }
};

const getResultEmoji = (code) => {
    switch(code) {
        case 'WIN': return '✅';
        case 'LOSS': return '❌';
        case 'MISSED': return '⏩';
        default: return '-';
    }
};

// Load reports from API
async function loadReports(page = 1) {
    try {
        const limit = document.getElementById('limit-select').value || 50;
        const sort = document.getElementById('sort-select').value || 'reported_at';
        
        const params = new URLSearchParams({
            page,
            limit,
            sort
        });

        const response = await fetch(`/api/reports?${params}`);
        if (!response.ok) throw new Error('Failed to fetch reports');
        
        const data = await response.json();
        
        if (data.status !== 'success') {
            throw new Error(data.message || 'Failed to load reports');
        }

        allReports = data.reports || [];
        totalReports = data.pagination.total;
        currentPage = page;

        renderReports();
        updatePagination(data.pagination);
        updateStats();
    } catch (error) {
        console.error('Error loading reports:', error);
        document.getElementById('reports-tbody').innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                <p>Error: ${error.message}</p>
            </div>
        `;
    }
}

// Render reports table
function renderReports() {
    const tbody = document.getElementById('reports-tbody');
    
    if (!allReports || allReports.length === 0) {
        tbody.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📭</div>
                <p>No reports yet</p>
            </div>
        `;
        return;
    }

    tbody.innerHTML = allReports.map(report => {
        const resultEmoji = getResultEmoji(report.trade_result);
        const resultClass = getResultClass(report.trade_result);
        const badgeClass = getReasonBadge(report.reason_code);
        
        return `
            <div class="table-row">
                <div class="report-id">#${report.id}</div>
                <div class="trade-id">#${report.trade_id}</div>
                <div class="trade-date">${formatDate(report.trade_date)}</div>
                <div class="trade-result ${resultClass}">${resultEmoji} ${report.trade_result}</div>
                <div>
                    <span class="badge ${badgeClass}">${report.reason_label}</span>
                </div>
                <div class="details-text" title="${report.details || 'No details'}">${report.details || '(no details)'}</div>
                <div>
                    <button class="action-btn" onclick="showDetailModal(${report.id})">View</button>
                </div>
            </div>
        `;
    }).join('');
}

// Update pagination controls
function updatePagination(pagination) {
    const pageInfo = document.getElementById('page-info');
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    
    pageInfo.innerText = `Page ${pagination.page} of ${pagination.pages}`;
    prevBtn.disabled = !pagination.has_prev;
    nextBtn.disabled = !pagination.has_next;
}

// Pagination handlers
function prevPage() {
    if (currentPage > 1) loadReports(currentPage - 1);
}

function nextPage() {
    loadReports(currentPage + 1);
}

// Update statistics
function updateStats() {
    let analysisErrors = 0;
    let dataErrors = 0;
    let bugReports = 0;

    // If we have all reports loaded, count them
    if (allReports.length > 0) {
        allReports.forEach(report => {
            if (report.reason_code === 'ANALYSIS_ERROR') analysisErrors++;
            else if (report.reason_code === 'DATA_ERROR') dataErrors++;
            else if (report.reason_code === 'BUG') bugReports++;
        });
    }

    document.getElementById('total-reports').innerText = totalReports;
    document.getElementById('analysis-errors').innerText = analysisErrors;
    document.getElementById('data-errors').innerText = dataErrors;
    document.getElementById('bug-reports').innerText = bugReports;
}

// Show detail modal
function showDetailModal(reportId) {
    const report = allReports.find(r => r.id === reportId);
    if (!report) return;

    const resultEmoji = getResultEmoji(report.trade_result);
    const resultClass = getResultClass(report.trade_result);

    document.getElementById('modal-report-id').innerText = `#${report.id}`;
    document.getElementById('modal-trade-id').innerText = `#${report.trade_id}`;
    document.getElementById('modal-trade-date').innerText = `${formatDate(report.trade_date)} ${formatTime(report.trade_date)}`;
    document.getElementById('modal-trade-result').innerHTML = `<span class="${resultClass}">${resultEmoji} ${report.trade_result}</span>`;
    document.getElementById('modal-rr-pnl').innerText = `RR: ${report.rr || '-'} | PnL: ${formatUSD(report.pnl_usd)}`;
    document.getElementById('modal-reason').innerText = report.reason_label;
    document.getElementById('modal-reported-at').innerText = `${formatDate(report.reported_at)} ${formatTime(report.reported_at)}`;
    document.getElementById('modal-details').innerText = report.details || '(No additional details provided)';

    document.getElementById('detail-modal').classList.add('active');
}

// Close detail modal
function closeDetailModal() {
    document.getElementById('detail-modal').classList.remove('active');
}

// Close modal on overlay click
document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('detail-modal');
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeDetailModal();
            }
        });
    }

    // Auto-load reports
    loadReports(1);
});
