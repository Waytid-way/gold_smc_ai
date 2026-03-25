// history.js - Trade History Page Logic
let tg = window.Telegram.WebApp;
tg.ready();
tg.expand();
tg.setHeaderColor('secondary_bg_color');

// State
let currentPage = 1;
let currentFilters = {
    result: '',
    start_date: '',
    end_date: ''
};

// Format functions
const formatUSD = (val) => {
    if (val === null || val === undefined) return "$0.00";
    const sign = val >= 0 ? "+" : "";
    return `${sign}$${val.toFixed(2)}`;
};

const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-GB', { month: '2-digit', day: '2-digit' });
};

const formatTime = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
};

const getResultEmoji = (code) => {
    switch(code) {
        case 'WIN': return '✅';
        case 'LOSS': return '❌';
        case 'MISSED': return '⏩';
        default: return '-';
    }
};

// API call to fetch history
async function fetchHistory(page = 1) {
    try {
        const params = new URLSearchParams();
        params.append('page', page);
        params.append('limit', 20);
        
        if (currentFilters.result) params.append('result', currentFilters.result);
        if (currentFilters.start_date) params.append('start_date', currentFilters.start_date);
        if (currentFilters.end_date) params.append('end_date', currentFilters.end_date);
        
        const response = await fetch(`/api/trades/history?${params.toString()}`);
        const data = await response.json();
        
        if (data.status !== 'success') {
            alert('Error loading history');
            return;
        }
        
        renderTable(data.data);
        updatePagination(data.pagination);
        currentPage = page;
    } catch (error) {
        console.error('Error fetching history:', error);
        document.getElementById('trades-tbody').innerHTML = 
            '<tr><td colspan="5" style="color: var(--loss-color); text-align: center;">Failed to load trade history</td></tr>';
    }
}

// Render table rows
function renderTable(trades) {
    const tbody = document.getElementById('trades-tbody');
    
    if (!trades || trades.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 20px;">No trades found</td></tr>';
        return;
    }
    
    tbody.innerHTML = trades.map(trade => {
        const pnlClass = trade.pnl_usd >= 0 ? 'pnl-positive' : 'pnl-negative';
        return `
            <tr class="trade-row">
                <td class="col-date">
                    <div class="date-display">${formatDate(trade.recorded_at)}</div>
                    <div class="time-display">${formatTime(trade.recorded_at)}</div>
                </td>
                <td class="col-result">${getResultEmoji(trade.code)} ${trade.label_th || trade.code}</td>
                <td class="col-rr">${trade.rr || '-'}</td>
                <td class="col-pnl ${pnlClass}">${formatUSD(trade.pnl_usd)}</td>
                <td class="col-action">
                    <button class="action-btn" onclick="showAIModal(${trade.id})" title="View AI Analysis">🤖</button>
                    <button class="flag-btn" onclick="openReportModal(${trade.id})" title="Report Issue">🚩</button>
                </td>
            </tr>
        `;
    }).join('');
}

// Update pagination controls
function updatePagination(pagination) {
    const pageInfo = document.getElementById('page-info');
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    
    pageInfo.innerText = `Page ${pagination.page} of ${pagination.total_pages}`;
    prevBtn.disabled = !pagination.has_prev;
    nextBtn.disabled = !pagination.has_next;
}

// Pagination handlers
function prevPage() {
    if (currentPage > 1) {
        fetchHistory(currentPage - 1);
    }
}

function nextPage() {
    fetchHistory(currentPage + 1);
}

// Filter handlers
function applyFilters() {
    currentFilters.result = document.getElementById('filter-result').value;
    currentFilters.start_date = document.getElementById('filter-start-date').value;
    currentFilters.end_date = document.getElementById('filter-end-date').value;
    
    currentPage = 1;
    fetchHistory(1);
}

function resetFilters() {
    document.getElementById('filter-result').value = '';
    document.getElementById('filter-start-date').value = '';
    document.getElementById('filter-end-date').value = '';
    
    currentFilters = { result: '', start_date: '', end_date: '' };
    currentPage = 1;
    fetchHistory(1);
}

// Navigation
function goToDashboard() {
    // Close modal if open
    const overlay = document.getElementById('modal-overlay');
    if (overlay) overlay.classList.remove('active');
    
    // Navigate to index.html
    window.location.href = '/';
}

// Modal functions (same as index.html)
async function showAIModal(tradeId) {
    try {
        const response = await fetch(`/api/trade/${tradeId}`);
        const data = await response.json();
        
        if (data.status !== 'success') {
            alert('Error loading analysis');
            return;
        }
        
        const trade = data.trade;
        
        document.getElementById('modal-result').innerText = trade.result_label || trade.result_code;
        document.getElementById('modal-rr').innerText = trade.rr || '-';
        document.getElementById('modal-pnl').innerText = formatUSD(trade.pnl_usd);
        document.getElementById('modal-date').innerText = trade.recorded_at || '-';
        document.getElementById('modal-analysis').innerText = trade.ai_analysis || 'No analysis available';
        
        const overlay = document.getElementById('modal-overlay');
        overlay.classList.add('active');
    } catch (error) {
        console.error('Error fetching trade detail:', error);
        alert('Failed to load analysis');
    }
}

function closeAIModal() {
    const overlay = document.getElementById('modal-overlay');
    overlay.classList.remove('active');
}

// Close modal when clicking outside
document.addEventListener('DOMContentLoaded', () => {
    const overlay = document.getElementById('modal-overlay');
    if (overlay) {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                closeAIModal();
            }
        });
    }
    
    // Report modal overlay click handler
    const reportOverlay = document.getElementById('report-overlay');
    if (reportOverlay) {
        reportOverlay.addEventListener('click', (e) => {
            if (e.target === reportOverlay) {
                closeReportModal();
            }
        });
    }
    
    // Load initial data
    fetchHistory(1);
});

// Report Modal Functions
let currentReportTradeId = null;

function openReportModal(tradeId) {
    currentReportTradeId = tradeId;
    document.getElementById('report-trade-id').innerText = `#${tradeId}`;
    document.getElementById('report-reason').value = '';
    document.getElementById('report-details').value = '';
    
    const overlay = document.getElementById('report-overlay');
    overlay.classList.add('active');
}

function closeReportModal() {
    const overlay = document.getElementById('report-overlay');
    overlay.classList.remove('active');
    currentReportTradeId = null;
}

async function submitReport() {
    if (!currentReportTradeId) {
        alert('Error: No trade selected');
        return;
    }
    
    const reason = document.getElementById('report-reason').value;
    if (!reason) {
        alert('Please select a reason');
        return;
    }
    
    const details = document.getElementById('report-details').value;
    
    try {
        const response = await fetch(`/api/trade/${currentReportTradeId}/report`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                reason: reason,
                details: details
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            alert('✅ Report submitted successfully!');
            closeReportModal();
        } else {
            alert('❌ ' + (data.message || 'Failed to submit report'));
        }
    } catch (error) {
        console.error('Error submitting report:', error);
        alert('Failed to submit report');
    }
}
