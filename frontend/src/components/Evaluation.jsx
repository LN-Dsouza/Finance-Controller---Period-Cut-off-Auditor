import React from 'react';
import { classificationBadge, formatLabel } from '../utils';

function Evaluation({ metrics, onRunAudit, auditRunning, cutoffDate, windowDays, langsmithStatus }) {
  const throughput = metrics?.throughput || {};
  const accuracy = metrics?.accuracy || {};
  const exceptions = metrics?.exception_handling || {};
  const safety = metrics?.safety || {};
  const details = metrics?.details || [];

  const displayCutoff = metrics?.cutoff_date ? metrics.cutoff_date.split(' ')[0] : cutoffDate;
  const displayWindow = metrics?.window_days !== undefined ? metrics.window_days : windowDays;

  return (
    <div>
      <div className="header-bar">
        <div className="header-title">
          <h1>System Evaluation</h1>
          <p>
            Full-dataset metrics ({throughput.total_transactions || 75} cases) · Cutoff: <strong>{displayCutoff}</strong> (±{displayWindow} days)
          </p>
        </div>
        <button className="btn-primary" onClick={() => onRunAudit(cutoffDate ? `${cutoffDate} 23:59:59` : undefined, windowDays)} disabled={auditRunning}>
          {auditRunning ? 'Evaluating full ledger…' : 'Re-run full evaluation'}
        </button>
      </div>

      {langsmithStatus && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(99, 102, 241, 0.08)', border: '1px solid rgba(99, 102, 241, 0.25)', padding: '8px 16px', borderRadius: 8, marginBottom: 20, fontSize: '0.85rem' }}>
          <div>
            <strong>LangSmith Observability:</strong> Tracing is{' '}
            <span style={{ color: langsmithStatus.tracing_enabled ? '#34d399' : '#94a3b8', fontWeight: 'bold' }}>
              {langsmithStatus.tracing_enabled ? 'ACTIVE' : 'OFFLINE'}
            </span>
            {' · '}Project: <code>{langsmithStatus.project}</code>
          </div>
          <span style={{ color: 'var(--text-secondary)' }}>
            Observability evaluates LangGraph node latency, token usage, and retrieval traces.
          </span>
        </div>
      )}

      {!metrics && (
        <div className="unresolved-alert">
          <div className="unresolved-header">No evaluation results yet</div>
          <p style={{ margin: 0 }}>Run the cut-off audit to score every synthetic case against held-out ground truth.</p>
        </div>
      )}

      <div className="kpi-grid">
        <div className="kpi-card">
          <span className="kpi-title">Transactions</span>
          <span className="kpi-value">{throughput.total_transactions || 0}</span>
          <span className="kpi-desc">Processed: {throughput.processed || 0}</span>
        </div>
        <div className="kpi-card accuracy">
          <span className="kpi-title">Accuracy</span>
          <span className="kpi-value">{((accuracy.accuracy_rate || 0) * 100).toFixed(1)}%</span>
          <span className="kpi-desc">
            Macro F1 {(accuracy.macro_f1 || 0).toFixed(3)} · P {(accuracy.macro_precision || 0).toFixed(3)} · R {(accuracy.macro_recall || 0).toFixed(3)}
          </span>
        </div>
        <div className="kpi-card">
          <span className="kpi-title">AI investigated</span>
          <span className="kpi-value">{throughput.ai_investigated || 0}</span>
          <span className="kpi-desc">Auto-classified {throughput.auto_classified || 0}</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-title">Avg latency</span>
          <span className="kpi-value">{throughput.avg_latency_ms || 0}<span style={{ fontSize: '0.9rem' }}>ms</span></span>
          <span className="kpi-desc">Total {throughput.total_time_sec || 0}s</span>
        </div>
      </div>

      {/* Per-class metrics breakdown */}
      {accuracy.per_class && (
        <div className="table-card" style={{ marginBottom: 24 }}>
          <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--border-color)' }}>
            <h3 className="chart-title" style={{ margin: 0 }}>Per-class metrics</h3>
          </div>
          <table className="custom-table">
            <thead>
              <tr>
                <th>Classification</th>
                <th>Precision</th>
                <th>Recall</th>
                <th>F1</th>
                <th>Support</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(accuracy.per_class).map(([label, m]) => (
                <tr key={label}>
                  <td><strong>{label.replace(/_/g, ' ')}</strong></td>
                  <td>{(m.precision * 100).toFixed(1)}%</td>
                  <td>{(m.recall * 100).toFixed(1)}%</td>
                  <td>{(m.f1 * 100).toFixed(1)}%</td>
                  <td>{m.support}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="charts-grid">
        <div className="chart-card">
          <div className="chart-header">
            <h3 className="chart-title">Exception handling</h3>
          </div>
          <div className="bar-chart-container">
            <div className="chart-bar-row">
              <span className="bar-label">Resolved</span>
              <div className="bar-wrapper">
                <div className="bar-fill before" style={{ width: `${exceptions.resolved || 0}%` }}></div>
              </div>
              <span className="bar-value">{exceptions.resolved || 0}</span>
            </div>
            <div className="chart-bar-row">
              <span className="bar-label">Unresolved</span>
              <div className="bar-wrapper">
                <div className="bar-fill unresolved" style={{ width: `${exceptions.unresolved || 0}%` }}></div>
              </div>
              <span className="bar-value">{exceptions.unresolved || 0}</span>
            </div>
            <div className="chart-bar-row">
              <span className="bar-label">Escalated</span>
              <div className="bar-wrapper">
                <div className="bar-fill misstatement" style={{ width: `${exceptions.escalated || 0}%` }}></div>
              </div>
              <span className="bar-value">{exceptions.escalated || 0}</span>
            </div>
            <div className="chart-bar-row">
              <span className="bar-label">Misstatements</span>
              <div className="bar-wrapper">
                <div className="bar-fill after" style={{ width: `${exceptions.potential_misstatements || 0}%` }}></div>
              </div>
              <span className="bar-value">{exceptions.potential_misstatements || 0}</span>
            </div>
          </div>
        </div>

        <div className="chart-card">
          <div className="chart-header">
            <h3 className="chart-title">Safety</h3>
          </div>
          <div style={{ display: 'grid', gap: 12, fontSize: '0.9rem' }}>
            <div>Incorrect forced classifications: <strong>{safety.incorrect_forced_classifications || 0}</strong></div>
            <div>Correctly escalated cases: <strong>{safety.correctly_escalated_cases || 0}</strong></div>
            <div>Unsupported conclusions: <strong>{safety.unsupported_conclusions || 0}</strong></div>
            <div>Hallucinated evidence: <strong>{safety.hallucinated_evidence || 0}</strong></div>
            <p style={{ color: 'var(--text-secondary)', margin: '8px 0 0' }}>
              Forced classification means the agent chose BEFORE/AFTER when ground truth required UNRESOLVED or POTENTIAL_MISSTATEMENT.
            </p>
          </div>
        </div>
      </div>

      <div className="table-card">
        <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--border-color)' }}>
          <h3 className="chart-title" style={{ margin: 0 }}>
            Full dataset outcomes {metrics?.run_id ? `· ${metrics.run_id}` : ''}
          </h3>
        </div>
        <table className="custom-table">
          <thead>
            <tr>
              <th>Transaction</th>
              <th>AI used</th>
              <th>Ground truth</th>
              <th>Prediction</th>
              <th>Match</th>
              <th>Confidence</th>
              <th>Latency</th>
            </tr>
          </thead>
          <tbody>
            {details.map((row) => (
              <tr key={row.transaction_id}>
                <td><strong>{row.transaction_id}</strong></td>
                <td>{row.used_ai ? 'LangGraph' : 'Rules'}</td>
                <td>
                  <span className={`badge ${classificationBadge(row.ground_truth)}`}>
                    {formatLabel(row.ground_truth)}
                  </span>
                </td>
                <td>
                  <span className={`badge ${classificationBadge(row.prediction)}`}>
                    {formatLabel(row.prediction)}
                  </span>
                </td>
                <td>{row.correct ? 'Yes' : 'No'}</td>
                <td>{Math.round((row.confidence || 0) * 100)}%</td>
                <td>{row.latency_ms}ms</td>
              </tr>
            ))}
            {details.length === 0 && (
              <tr>
                <td colSpan="7" style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: 24 }}>
                  Evaluation details appear after an audit run.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default Evaluation;
