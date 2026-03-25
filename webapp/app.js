// app.js - Telegram Mini App Logic
let tg = window.Telegram.WebApp;

// Tell Telegram that the web app is ready
tg.ready();

// Expand the app to take maximum height
tg.expand();
tg.setHeaderColor('secondary_bg_color');

// Format currency
const formatUSD = (val) => {
    if (val === null || val === undefined) return "$0.00";
    const sign = val >= 0 ? "+" : "";
    return `${sign}$${val.toFixed(2)}`;
};

// ──────── Modal Functions ────────
async function showAIModal(tradeId) {
    try {
        const response = await fetch(`/api/trade/${tradeId}`);
        const data = await response.json();
        
        if (data.status !== 'success') {
            alert('Error loading analysis');
            return;
        }
        
        const trade = data.trade;
        
        // Populate modal content
        document.getElementById('modal-result').innerText = trade.result_label || trade.result_code;
        document.getElementById('modal-rr').innerText = trade.rr || '-';
        document.getElementById('modal-pnl').innerText = formatUSD(trade.pnl_usd);
        document.getElementById('modal-date').innerText = trade.recorded_at || '-';
        document.getElementById('modal-analysis').innerText = trade.ai_analysis || 'No analysis available';
        
        // Show modal
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

// Close modal when clicking outside (on the overlay background)
document.addEventListener('DOMContentLoaded', () => {
    const overlay = document.getElementById('modal-overlay');
    if (overlay) {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                closeAIModal();
            }
        });
    }
});

async function fetchStatsAndRender() {
    try {
        // Fetch data from our Python Flask local server API endpoint.
        // We use relative path so that ngrok tunnel routes it correctly.
        const response = await fetch('/api/trades');
        const data = await response.json();
        
        // 1. Update Overview Stats
        document.getElementById('val-total-pnl').innerText = formatUSD(data.stats.pnl_total);
        document.getElementById('val-total-pnl').style.color = data.stats.pnl_total >= 0 ? 'var(--win-color)' : 'var(--loss-color)';
        
        document.getElementById('val-win-rate').innerText = `${data.stats.win_rate}%`;
        document.getElementById('val-total-trades').innerText = data.stats.total;

        // 2. Render Calendar Grid exact for current month
        const grid = document.getElementById('calendar-grid');
        grid.innerHTML = ''; // Clear loading
        
        // Setup Date info for current month
        const today = new Date();
        const year = today.getFullYear();
        const month = today.getMonth(); // 0-11
        const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
        
        // Update Header Title gracefully (if element exists)
        const titleEl = document.getElementById('month-title');
        if (titleEl) {
            titleEl.innerText = `Trading Journal - ${monthNames[month]} ${year}`;
        }
        
        // Group trades by date (yyyy-mm-dd) ONLY for the current month
        const tradesByDate = {};
        data.history.forEach(trade => {
            const dateParts = trade.recorded_at.split(' ')[0].split('-');
            const tradeYear = parseInt(dateParts[0], 10);
            const tradeMonth = parseInt(dateParts[1], 10) - 1; // 0-indexed
            const tradeDay = parseInt(dateParts[2], 10);
            
            // Only aggregate if it matches the current viewed month
            if (tradeYear === year && tradeMonth === month) {
                if (!tradesByDate[tradeDay]) {
                    tradesByDate[tradeDay] = [];
                }
                tradesByDate[tradeDay].push(trade);
            }
        });

        const daysInMonth = new Date(year, month + 1, 0).getDate();
        let firstDayIndex = new Date(year, month, 1).getDay(); // 0-6 (Sun-Sat)
        if (firstDayIndex === 0) firstDayIndex = 7; // Convert Sun(0) -> 7 to make Mon=1

        // Render padding empty cells for days before the 1st
        for (let i = 1; i < firstDayIndex; i++) {
            const emptyCell = document.createElement('div');
            emptyCell.className = 'day-cell empty';
            emptyCell.style.border = "none";
            emptyCell.style.background = "transparent";
            grid.appendChild(emptyCell);
        }

        // Render actual days
        for (let i = 1; i <= daysInMonth; i++) {
            const cell = document.createElement('div');
            cell.className = 'day-cell';
            
            const dateSpan = document.createElement('span');
            dateSpan.className = 'day-date';
            dateSpan.innerText = i;
            cell.appendChild(dateSpan);
            
            const pnlSpan = document.createElement('span');
            pnlSpan.className = 'day-pnl';

            const dayTrades = tradesByDate[i];
            
            if (dayTrades && dayTrades.length > 0) {
                let dayPnl = 0.0;
                let dayIsWin = false;
                let dayIsLoss = false;
                
                dayTrades.forEach(t => {
                    if (t.code === 'WIN') {
                        dayIsWin = true;
                        dayPnl += t.pnl_usd || 0;
                    } else if (t.code === 'LOSS') {
                        dayIsLoss = true;
                        dayPnl += t.pnl_usd || 0;
                    }
                });
                
                if (dayPnl > 0 || (dayIsWin && dayPnl === 0)) {
                    cell.classList.add('win');
                    pnlSpan.innerText = `+${dayPnl.toFixed(0)}`;
                } else if (dayPnl < 0 || dayIsLoss) {
                    cell.classList.add('loss');
                    pnlSpan.innerText = `${dayPnl.toFixed(0)}`;
                } else {
                    cell.classList.add('miss');
                    pnlSpan.innerText = '-';
                }
                
                cell.appendChild(pnlSpan);
            } else {
                pnlSpan.innerText = '';
                cell.appendChild(pnlSpan);
            }
            
            grid.appendChild(cell);
        }
        
    } catch (error) {
        console.error("Error fetching data:", error);
        document.getElementById('calendar-grid').innerHTML = '<p style="color:var(--loss-color)">Failed to load data. Ensure web_server is running.</p>';
    }
}

// Simple Tooltip Logic
const tooltip = document.getElementById('tooltip');
function showTooltip(event, text) {
    tooltip.innerText = text;
    tooltip.style.left = event.pageX + 10 + 'px';
    tooltip.style.top = event.pageY + 10 + 'px';
    tooltip.classList.remove('hidden');
    
    // Hide after 2 seconds
    setTimeout(() => {
        tooltip.classList.add('hidden');
    }, 2000);
}

// Init
fetchStatsAndRender();
