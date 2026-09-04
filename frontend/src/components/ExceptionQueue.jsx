import React, { useState } from 'react';
import { classificationBadge, formatDate, formatLabel } from '../utils';

function ExceptionQueue({ exceptions, onSelectTx }) {
  const [filter, setFilter] = useState('PENDING');

  const filteredExceptions = exceptions.filter(ex => {
    if (filter === 'PENDING') {
      return ex.status === 'PENDING' || ex.human_review_required === true;
    }
    if (filter === 'REVIEWED') {
      return ex.status === 'AUDITED' || ex.status === 'REJECTED';
    }
    return true;
  });

  return (
    <div>
      <div className="header-bar">
        <div className="header-title">
          <h1>Flagged Exception Queue</h1>
          <p>Unresolved or suspicious transactions requiring human-in-the-loop review (README §26)</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button 
            className={`btn-primary ${filter === 'PENDING' ? '' : 'btn-secondary'}`}
            style={filter !== 'PENDING' ? { background: '#1e293b', border: '1px solid var(--border-color)', boxShadow: 'none' } : {}}
            onClick={() => setFilter('PENDING')}
          >
            Pending Review ({exceptions.filter(e => e.status === 'PENDING' || e.human_review_required === true).length})
          </button>
          <button 
            className={`btn-primary ${filter === 'ALL' ? '' : 'btn-secondary'}`}
            style={filter !== 'ALL' ? { background: '#1e293b', border: '1px solid var(--border-color)', boxShadow: 'none' } : {}}
            onClick={() => setFilter('ALL')}
          >
            All Flagged ({exceptions.length})
          </button>
          <button 
            className={`btn-primary ${filter === 'REVIEWED' ? '' : 'btn-secondary'}`}
            style={filter !== 'REVIEWED' ? { background: '#1e293b', border: '1px solid var(--border-color)', boxShadow: 'none' } : {}}
            onClick={() => setFilter('REVIEWED')}
          >
            Reviewed ({exceptions.filter(e => e.status === 'AUDITED' || e.status === 'REJECTED').length})
          </button>
        </div>
      </div>

      <div className="unresolved-alert" style={{ background: 'rgba(245, 158, 11, 0.05)', border: '1px solid rgba(245, 158, 11, 0.2)' }}>
        <div className="unresolved-header" style={{ color: 'var(--color-misstatement)' }}>
          ⚠️ Period-End Accrual Exposure & Unresolved Cases
        </div>
        <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
          The following transactions have been flagged by the engine due to missing evidence, data inconsistencies, or temporal contradictions. 
          Auditors must inspect the evidence bundle and APPROVE, REJECT, or REQUEST MORE EVIDENCE. The AI agent never posts to the ledger.
        </p>
      </div>

      <div className="table-card">
        <table className="custom-table">
          <thead>
            <tr>
              <th>Transaction ID</th>
              <th>Amount</th>
              <th>Vendor Token</th>
              <th>Cutoff Date</th>
              <th>Classification</th>
              <th>Confidence</th>
              <th>Evidence Count</th>
              <th>Missing Evidence / Contradictions</th>
              <th>Ledger Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {filteredExceptions.map((ex) => (
              <tr key={ex.transaction_id} onClick={() => onSelectTx(ex.transaction_id)}>
                <td><strong>{ex.transaction_id}</strong></td>
                <td>{ex.currency || 'INR'} {Number(ex.amount).toLocaleString()}</td>
                <td><code>{ex.vendor_id || 'N/A'}</code></td>
                <td>{formatDate(ex.cutoff_date)}</td>
                <td>
                  <span className={`badge ${classificationBadge(ex.classification)}`}>
                    {formatLabel(ex.classification)}
                  </span>
                </td>
                <td>{Math.round((ex.confidence || 0) * 100)}%</td>
                <td><span className="badge pending">{ex.evidence_count || 0} items</span></td>
                <td style={{ maxWidth: '280px', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  {(ex.missing_evidence || []).length > 0 && (
                    <div><strong>Missing:</strong> {(ex.missing_evidence || []).join(', ')}</div>
                  )}
                  {(ex.contradictions || []).length > 0 && (
                    <div style={{ color: 'var(--color-unresolved)', marginTop: 4 }}>
                      <strong>Contradiction:</strong> {(ex.contradictions || []).join(', ')}
                    </div>
                  )}
                  {(!ex.missing_evidence || ex.missing_evidence.length === 0) && (!ex.contradictions || ex.contradictions.length === 0) && (
                    <span>Data validation exception</span>
                  )}
                </td>
                <td>
                  <span className={`badge ${String(ex.status || 'pending').toLowerCase()}`}>
                    {ex.status}
                  </span>
                </td>
                <td>
                  <button className="btn-primary" style={{ padding: '6px 12px', fontSize: '0.8rem' }}>
                    Investigate
                  </button>
                </td>
              </tr>
            ))}
            {filteredExceptions.length === 0 && (
              <tr>
                <td colSpan="10" style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '24px' }}>
                  No exceptions matching the current filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default ExceptionQueue;
