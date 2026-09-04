import React from 'react';
import { classificationBadge, formatLabel } from '../utils';

function Dashboard({
  metrics,
  transactions,
  exceptions,
  onRunAudit,
  auditRunning,
  onSelectTx,
  cutoffDate,
  setCutoffDate,
  windowDays,
  setWindowDays,
  onSeedData,
  seedLoading,
  policies,
  langsmithStatus
}) {
  const stats = metrics?.throughput || {
    total_transactions: transactions.length || 0,
    processed: 0,
    ai_investigated: 0,
    auto_classified: 0
  };

  const accuracyRate = metrics?.accuracy?.accuracy_rate || 0;
  const resolvedCount = metrics?.exception_handling?.resolved || 0;
  
  // Categorize transactions for stats
  const beforeCount = transactions.filter(t => t.classification === 'BEFORE_CUTOFF').length;
  const afterCount = transactions.filter(t => t.classification === 'AFTER_CUTOFF').length;
  const misstatementCount = transactions.filter(t => t.classification === 'POTENTIAL_MISSTATEMENT').length;
  const unresolvedCount = exceptions.length;

  const totalCategorized = beforeCount + afterCount + misstatementCount + unresolvedCount;
  
  const getPercent = (count) => {
    if (totalCategorized === 0) return '0%';
    return `${(count / totalCategorized) * 100}%`;
  };

  // Get recent AI investigations
  const recentAi = transactions
    .filter(t => t.classification !== 'UNAUDITED' && t.classification !== 'BEFORE_CUTOFF' && t.classification !== 'AFTER_CUTOFF')
    .slice(0, 6);

  // Demo scenarios defined in README Section 33
  const demoCases = [
    {
      id: "TXN-A01",
      tag: "Case 1: Easy",
      badge: "before",
      desc: "Goods received Dec 28, Invoice Dec 29. Auto-cleared BEFORE_CUTOFF by deterministic rule."
    },
    {
      id: "TXN-C01",
      tag: "Case 2: Non-obvious",
      badge: "before",
      desc: "Invoiced Jan 03, paid Jan 15, but goods physically received Dec 29. Resolved BEFORE_CUTOFF."
    },
    {
      id: "TXN-F01",
      tag: "Case 3: Contradictory",
      badge: "misstatement",
      desc: "Internal GRN claims Dec 29, but carrier tracking proves Jan 03 delivery. POTENTIAL_MISSTATEMENT."
    },
    {
      id: "TXN-E01",
      tag: "Case 4: Unresolved",
      badge: "unresolved",
      desc: "PO and Invoice present, but proof of delivery completely missing. Escalated as UNRESOLVED."
    }
  ];

  return (
    <div>
      {/* Header Bar with Cut-Off Configuration */}
      <div className="header-bar" style={{ flexWrap: 'wrap', gap: 16 }}>
        <div className="header-title">
          <h1>Finance Control Center</h1>
          <p>Real-time Period-End Cut-Off Testing Dashboard</p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'var(--card-bg)', padding: '6px 12px', borderRadius: 8, border: '1px solid var(--border-color)' }}>
            <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Cutoff Date:</label>
            <input 
              type="date"
              className="search-input"
              style={{ padding: '4px 8px', fontSize: '0.85rem', width: 140, minWidth: 140 }}
              value={cutoffDate}
              onChange={(e) => setCutoffDate(e.target.value)}
            />
            <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginLeft: 8 }}>Window:</label>
            <select
              className="select-input"
              style={{ padding: '4px 8px', fontSize: '0.85rem' }}
              value={windowDays}
              onChange={(e) => setWindowDays(Number(e.target.value))}
            >
              <option value={7}>±7 days</option>
              <option value={14}>±14 days</option>
              <option value={30}>±30 days</option>
            </select>
          </div>

          <button 
            className="btn-primary" 
            style={{ background: '#334155', border: '1px solid var(--border-color)' }}
            onClick={onSeedData}
            disabled={seedLoading}
          >
            {seedLoading ? "Resetting..." : "Reload 75 Transactions"}
          </button>

          <button 
            className="btn-primary" 
            onClick={() => onRunAudit(cutoffDate ? `${cutoffDate} 23:59:59` : undefined, windowDays)}
            disabled={auditRunning}
          >
            {auditRunning ? "Auditing Ledgers..." : "Run Cut-Off Audit"}
          </button>
        </div>
      </div>

      {/* Observability Banner */}
      {langsmithStatus && (
        <div style={{ display: 'none', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(99, 102, 241, 0.08)', border: '1px solid rgba(99, 102, 241, 0.25)', padding: '8px 16px', borderRadius: 8, marginBottom: 20, fontSize: '0.85rem' }}>
          <div>
            <strong>Observability:</strong> LangSmith Tracing is{' '}
            <span style={{ color: langsmithStatus.tracing_enabled ? '#34d399' : '#94a3b8', fontWeight: 'bold' }}>
              {langsmithStatus.tracing_enabled ? 'Active' : 'Disabled'}
            </span>
            {' · '}Project: <code>{langsmithStatus.project}</code>
          </div>
          <span style={{ color: 'var(--text-secondary)' }}>
            {langsmithStatus.api_key_configured ? 'Traces recorded to LangSmith platform' : 'Set LANGSMITH_API_KEY in .env for live cloud traces'}
          </span>
        </div>
      )}

      {/* 6 Core Overview KPIs per README Section 26 */}
      <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}>
        <div className="kpi-card">
          <span className="kpi-title">Total Transactions</span>
          <span className="kpi-value">{stats.total_transactions}</span>
          <span className="kpi-desc">Cutoff Window: ±{windowDays} days</span>
        </div>
        
        <div className="kpi-card">
          <span className="kpi-title">AI Investigated</span>
          <span className="kpi-value">{stats.ai_investigated}</span>
          <span className="kpi-desc">LangGraph State Machine</span>
        </div>

        <div className="kpi-card">
          <span className="kpi-title">Auto-Classified</span>
          <span className="kpi-value">{stats.auto_classified}</span>
          <span className="kpi-desc">Deterministic Rules</span>
        </div>

        <div className="kpi-card">
          <span className="kpi-title">Resolved</span>
          <span className="kpi-value">{resolvedCount || (beforeCount + afterCount)}</span>
          <span className="kpi-desc">Before / After Cutoff</span>
        </div>

        <div className="kpi-card misstatement">
          <span className="kpi-title">Accrual Exceptions</span>
          <span className="kpi-value">{misstatementCount}</span>
          <span className="kpi-desc">Potential Misstatements</span>
        </div>

        <div className="kpi-card accuracy">
          <span className="kpi-title">Audit Accuracy</span>
          <span className="kpi-value">{(accuracyRate * 100).toFixed(1)}%</span>
          <span className="kpi-desc">Across held-out dataset</span>
        </div>
      </div>

      {/* Demo Story Quick Access (README Section 33) */}
      <div className="table-card" style={{ marginBottom: 24, padding: 18 }}>
        <div style={{ marginBottom: 12 }}>
          <h3 className="chart-title" style={{ margin: 0 }}>Canonical Cut-Off Scenarios (Demo)</h3>
          <p style={{ margin: '4px 0 0', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Inspect representative audit investigations demonstrating that the system does not force uncertain matches.
          </p>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 12 }}>
          {demoCases.map((c) => (
            <div 
              key={c.id} 
              onClick={() => onSelectTx(c.id)}
              style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-color)', borderRadius: 8, padding: 12, cursor: 'pointer', transition: 'border-color 0.2s' }}
              onMouseEnter={(e) => e.currentTarget.style.borderColor = 'var(--primary-color)'}
              onMouseLeave={(e) => e.currentTarget.style.borderColor = 'var(--border-color)'}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <strong>{c.id}</strong>
                <span className={`badge ${c.badge}`}>{c.tag}</span>
              </div>
              <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                {c.desc}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Charts Grid */}
      <div className="charts-grid">
        <div className="chart-card">
          <div className="chart-header">
            <h3 className="chart-title">Cut-Off Classifications</h3>
          </div>
          
          <div className="bar-chart-container">
            <div className="chart-bar-row">
              <span className="bar-label">Before Cutoff</span>
              <div className="bar-wrapper">
                <div className="bar-fill before" style={{ width: getPercent(beforeCount) }}></div>
              </div>
              <span className="bar-value">{beforeCount}</span>
            </div>

            <div className="chart-bar-row">
              <span className="bar-label">After Cutoff</span>
              <div className="bar-wrapper">
                <div className="bar-fill after" style={{ width: getPercent(afterCount) }}></div>
              </div>
              <span className="bar-value">{afterCount}</span>
            </div>

            <div className="chart-bar-row">
              <span className="bar-label">Misstatement</span>
              <div className="bar-wrapper">
                <div className="bar-fill misstatement" style={{ width: getPercent(misstatementCount) }}></div>
              </div>
              <span className="bar-value">{misstatementCount}</span>
            </div>

            <div className="chart-bar-row">
              <span className="bar-label">Unresolved (Escalated)</span>
              <div className="bar-wrapper">
                <div className="bar-fill unresolved" style={{ width: getPercent(unresolvedCount) }}></div>
              </div>
              <span className="bar-value">{unresolvedCount}</span>
            </div>
          </div>
        </div>

        <div className="chart-card">
          <div className="chart-header">
            <h3 className="chart-title">Audit Engine Efficiency</h3>
          </div>
          <div className="bar-chart-container" style={{ gap: '24px' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '0.9rem' }}>
                <span>Rules Engine Auto-Classification (Cost-Saving)</span>
                <strong>{stats.auto_classified} / {stats.total_transactions} ({stats.total_transactions > 0 ? ((stats.auto_classified / stats.total_transactions)*100).toFixed(0) : 0}%)</strong>
              </div>
              <div className="bar-wrapper" style={{ height: '12px' }}>
                <div className="bar-fill before" style={{ width: stats.total_transactions > 0 ? `${(stats.auto_classified / stats.total_transactions)*100}%` : '0%' }}></div>
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '0.9rem' }}>
                <span>AI LangGraph Reasoning Engine (Deep Auditing)</span>
                <strong>{stats.ai_investigated} / {stats.total_transactions} ({stats.total_transactions > 0 ? ((stats.ai_investigated / stats.total_transactions)*100).toFixed(0) : 0}%)</strong>
              </div>
              <div className="bar-wrapper" style={{ height: '12px' }}>
                <div className="bar-fill after" style={{ width: stats.total_transactions > 0 ? `${(stats.ai_investigated / stats.total_transactions)*100}%` : '0%' }}></div>
              </div>
            </div>
            
            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', background: 'rgba(255,255,255,0.03)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
              Deterministic rules classify obvious cases. LangGraph runs only on ambiguous, missing-evidence, or contradictory cases.
            </div>
          </div>
        </div>
      </div>

      {/* Exception table overview */}
      <div className="table-card">
        <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--border-color)' }}>
          <h3 className="chart-title" style={{ margin: 0 }}>Recent Exceptions Requiring Investigation</h3>
        </div>
        <table className="custom-table">
          <thead>
            <tr>
              <th>Transaction ID</th>
              <th>Type</th>
              <th>Amount</th>
              <th>Ledger Posting Date</th>
              <th>Classification</th>
              <th>Confidence</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {recentAi.map((tx) => (
              <tr key={tx.transaction_id} onClick={() => onSelectTx(tx.transaction_id)}>
                <td><strong>{tx.transaction_id}</strong></td>
                <td>{tx.transaction_type}</td>
                <td>{tx.currency} {tx.amount.toLocaleString()}</td>
                <td>{tx.posting_date.split('T')[0]}</td>
                <td>
                  <span className={`badge ${classificationBadge(tx.classification)}`}>
                    {formatLabel(tx.classification)}
                  </span>
                </td>
                <td>{(tx.confidence * 100).toFixed(0)}% <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>(score)</span></td>
                <td>
                  <button className="btn-primary" style={{ padding: '4px 10px', fontSize: '0.8rem', borderRadius: '4px' }}>
                    View Investigation
                  </button>
                </td>
              </tr>
            ))}
            {recentAi.length === 0 && (
              <tr>
                <td colSpan="7" style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '24px' }}>
                  No exceptions detected in the current run.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default Dashboard;
