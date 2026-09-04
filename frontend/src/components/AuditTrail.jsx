import React, { useEffect, useState } from 'react';
import { classificationBadge, formatDate, formatLabel } from '../utils';

const API_BASE = 'http://127.0.0.1:8000/api';

function AuditTrail({ onSelectTx }) {
  const [logs, setLogs] = useState([]);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const res = await fetch(`${API_BASE}/audit-log`);
        const data = await res.json();
        setLogs(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error('Error loading audit trail:', err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const openLog = async (transactionId) => {
    setSelected(transactionId);
    try {
      const res = await fetch(`${API_BASE}/audit-log/${transactionId}`);
      if (!res.ok) {
        setDetail(null);
        return;
      }
      setDetail(await res.json());
    } catch (err) {
      console.error('Error loading audit log detail:', err);
    }
  };

  return (
    <div>
      <div className="header-bar">
        <div className="header-title">
          <h1>Audit Trail</h1>
          <p>Immutable-style investigation history: rules, tools, evidence, and human decisions</p>
        </div>
      </div>

      <div className="detail-grid">
        <div className="table-card">
          {loading && <div style={{ padding: 24, color: 'var(--text-secondary)' }}>Loading audit logs…</div>}
          <table className="custom-table">
            <thead>
              <tr>
                <th>Transaction</th>
                <th>Timestamp</th>
                <th>Classification</th>
                <th>Confidence</th>
                <th>Human Decision</th>
                <th>Reviewer</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.log_id} onClick={() => openLog(log.transaction_id)}>
                  <td><strong>{log.transaction_id}</strong></td>
                  <td>{formatDate(log.timestamp)}</td>
                  <td>
                    <span className={`badge ${classificationBadge(log.classification)}`}>
                      {formatLabel(log.classification)}
                    </span>
                  </td>
                  <td>{Math.round((log.confidence || 0) * 100)}%</td>
                  <td>{formatLabel(log.human_decision) || '—'}</td>
                  <td>{log.reviewer || '—'}</td>
                </tr>
              ))}
              {!loading && logs.length === 0 && (
                <tr>
                  <td colSpan="6" style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: 24 }}>
                    No audit logs yet. Run a cut-off audit first.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div>
          <div className="panel-card">
            <h3 className="panel-title">Investigation Record</h3>
            {!detail && (
              <p style={{ color: 'var(--text-secondary)', margin: 0 }}>
                Select a row to inspect rules triggered, tools called, and evidence retrieved.
              </p>
            )}
            {detail && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14, fontSize: '0.9rem' }}>
                <div>
                  <label style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Run / Log</label>
                  <div>{detail.run_id} · {detail.log_id}</div>
                </div>
                <div>
                  <label style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Rules triggered</label>
                  <ul className="unresolved-list">
                    {(detail.rules_triggered || []).map((rule, idx) => <li key={idx}>{typeof rule === 'string' ? rule : JSON.stringify(rule)}</li>)}
                  </ul>
                </div>
                <div>
                  <label style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Tools called</label>
                  <div>{(detail.tools_called || []).join(', ') || 'None (rules-only)'}</div>
                </div>
                <div>
                  <label style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Evidence retrieved</label>
                  <div>{(detail.evidence_retrieved || []).join(', ') || '—'}</div>
                </div>
                <div>
                  <label style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Recommended action</label>
                  <div>{detail.recommended_action || '—'}</div>
                </div>
                <button className="btn-primary" onClick={() => onSelectTx(detail.transaction_id)}>
                  Open investigation cockpit
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default AuditTrail;
