import React, { useState, useEffect } from 'react';
import { classificationBadge, confidenceCaption, formatDate, formatLabel } from '../utils';

const API_BASE = 'http://127.0.0.1:8000/api';

function listOf(value) {
  return Array.isArray(value) ? value : [];
}

function Detail({ transactionId, onBack, onReviewSubmitted }) {
  const [data, setData] = useState(null);
  const [auditLog, setAuditLog] = useState(null);
  const [loading, setLoading] = useState(true);
  const [decision, setDecision] = useState('APPROVE');
  const [comment, setComment] = useState('');
  const [reviewer, setReviewer] = useState('Senior Auditor');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchDetail = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${API_BASE}/transactions/${transactionId}`);
        if (!res.ok) {
          throw new Error('Transaction not found');
        }
        const result = await res.json();
        setData(result);

        const logRes = await fetch(`${API_BASE}/audit-log/${transactionId}`);
        if (logRes.ok) {
          setAuditLog(await logRes.json());
        } else {
          setAuditLog(null);
        }
      } catch (err) {
        console.error('Error loading transaction detail:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    if (transactionId) {
      fetchDetail();
    }
  }, [transactionId]);

  const handleSubmitReview = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/reviews/${transactionId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reviewer, decision, comment }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || 'Review failed');
      }
      onReviewSubmitted();
      onBack();
    } catch (err) {
      console.error('Error submitting review:', err);
      alert(err.message || 'Failed to submit review.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return <div style={{ color: 'var(--text-secondary)' }}>Loading investigation cockpit...</div>;
  }

  if (error || !data) {
    return <div>Unable to load transaction. {error}</div>;
  }

  const tx = data.transaction;
  const invg = data.investigation;
  const timeline = listOf(data.timeline);
  const evidence = listOf(data.evidence);
  const reviews = listOf(data.reviews);
  const knownFacts = listOf(invg?.known_facts);
  const missing = listOf(invg?.missing_evidence);
  const contradictions = listOf(invg?.contradictions);
  const steps = listOf(invg?.steps).filter((s) => typeof s === 'string');
  const classification = invg?.classification;
  const confidence = invg?.confidence || 0;
  const unresolved = classification === 'UNRESOLVED' || invg?.human_review_required;

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <button onClick={onBack} className="btn-primary" style={{ background: '#1e293b', border: '1px solid var(--border-color)', boxShadow: 'none' }}>
          ← Back to Ledger
        </button>
      </div>

      <div className="header-bar">
        <div className="header-title">
          <h1>Investigation Cockpit: {tx.transaction_id}</h1>
          <p>Evidence, hypotheses, and auditor review — the ledger is not modified by the agent</p>
        </div>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <span className={`badge ${classificationBadge(classification)}`}>
            AI: {formatLabel(classification) || 'UNAUDITED'}
          </span>
          <span className={`badge ${String(tx.status || 'pending').toLowerCase()}`}>
            Ledger: {tx.status}
          </span>
        </div>
      </div>

      {unresolved && (
        <div className="unresolved-alert">
          <div className="unresolved-header">
            Human review required — {formatLabel(classification)}
          </div>
          <div className="fact-grid">
            <div className="fact-box">
              <h4>Why unresolved</h4>
              <p>{invg?.reasoning_summary || 'Evidence is insufficient or contradictory.'}</p>
            </div>
            <div className="fact-box">
              <h4>What is known</h4>
              <ul>
                {knownFacts.length ? knownFacts.map((item, idx) => <li key={idx}>{item}</li>) : <li>No confirmed facts beyond the ledger posting.</li>}
              </ul>
            </div>
            <div className="fact-box">
              <h4>What is missing</h4>
              <ul>
                {missing.length ? missing.map((item, idx) => <li key={idx}>{item}</li>) : <li>No missing-document flags (check contradictions).</li>}
              </ul>
            </div>
            <div className="fact-box">
              <h4>What should happen next</h4>
              <p>{invg?.recommended_action || 'Request supporting documents and re-run review.'}</p>
            </div>
          </div>
          {contradictions.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <strong style={{ color: 'var(--color-unresolved)' }}>Contradictions</strong>
              <ul className="unresolved-list">
                {contradictions.map((item, idx) => <li key={idx}>{item}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}

      <div className="detail-grid">
        <div className="left-column">
          <div className="panel-card" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
            <div>
              <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Amount</label>
              <div style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>{tx.currency} {Number(tx.amount).toLocaleString()}</div>
            </div>
            <div>
              <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Posting Period</label>
              <div style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>{tx.ledger_period}</div>
            </div>
            <div>
              <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Economic event date</label>
              <div style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>{formatDate(invg?.economic_event_date)}</div>
            </div>
          </div>

          <div className="panel-card">
            <h3 className="panel-title">Reconstructed document timeline</h3>
            <div className="timeline-flow">
              {timeline.map((event, idx) => (
                <div key={idx} className={`timeline-item ${String(event.event).includes('Receipt') || String(event.event).includes('Delivery') ? 'highlight' : ''}`}>
                  <div className="timeline-dot"></div>
                  <span className="timeline-event">{event.event}</span>
                  <div className="timeline-meta">
                    <span>{formatDate(event.date)}</span>
                    <span>{event.source}</span>
                  </div>
                </div>
              ))}
              {timeline.length === 0 && <p style={{ color: 'var(--text-secondary)' }}>No timeline events.</p>}
            </div>
          </div>

          <div className="panel-card">
            <h3 className="panel-title">Evidence (privacy-filtered)</h3>
            <div className="evidence-grid">
              {evidence.map((ev) => (
                <div key={ev.evidence_id} className="evidence-card">
                  <div className="evidence-header">
                    <span>{ev.evidence_id} ({formatLabel(ev.source_type)})</span>
                    <span>Reliability: {ev.reliability}</span>
                  </div>
                  <pre className="evidence-body">{ev.content}</pre>
                </div>
              ))}
              {evidence.length === 0 && <p style={{ color: 'var(--text-secondary)' }}>No unstructured evidence stored.</p>}
            </div>
          </div>
        </div>

        <div className="right-sidebar">
          <div className="panel-card">
            <h3 className="panel-title">AI auditor diagnosis</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Classification</label>
                <div style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>
                  {formatLabel(classification) || 'Not yet audited'}
                </div>
              </div>

              <div>
                <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Confidence (not proof)</label>
                <div style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>
                  {invg ? `${(confidence * 100).toFixed(0)}%` : '—'}
                </div>
                <div className="bar-wrapper" style={{ height: '6px', marginTop: '6px' }}>
                  <div className={`bar-fill ${classificationBadge(classification)}`} style={{ width: invg ? `${confidence * 100}%` : '0%' }}></div>
                </div>
                <p className="confidence-disclaimer">
                  {invg ? confidenceCaption(confidence, classification) : 'Run the audit to produce a scored recommendation.'}
                </p>
              </div>

              <div>
                <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Accounting Policy Applied</label>
                <div style={{ fontSize: '0.95rem', fontWeight: '600', color: 'var(--primary-color)', marginTop: '2px' }}>
                  {invg?.policy_applied || 'POLICY-GOODS-CONTROL-TRANSFER (Standard Cutoff Policy)'}
                </div>
              </div>

              <div>
                <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Reasoning</label>
                <p style={{ fontSize: '0.9rem', margin: '4px 0 0 0', lineHeight: '1.4' }}>
                  {invg?.reasoning_summary || 'No AI investigation was performed (resolved by the rules engine, or unaudited).'}
                </p>
              </div>

              {invg?.recommended_action && (
                <div>
                  <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Recommended action</label>
                  <p style={{ fontSize: '0.9rem', margin: '4px 0 0 0', fontWeight: '500' }}>
                    {invg.recommended_action}
                  </p>
                </div>
              )}
            </div>
          </div>

          <div className="panel-card">
            <h3 className="panel-title">Hypotheses & investigation log</h3>
            {knownFacts.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Known facts / hypothesis notes</label>
                <ul className="unresolved-list">
                  {knownFacts.map((item, idx) => <li key={idx}>{item}</li>)}
                </ul>
              </div>
            )}
            {steps.length > 0 ? (
              <ol className="unresolved-list" style={{ paddingLeft: 18 }}>
                {steps.map((step, idx) => <li key={idx}>{step}</li>)}
              </ol>
            ) : (
              <p style={{ color: 'var(--text-secondary)', margin: 0, fontSize: '0.9rem' }}>
                Deterministic path: LangGraph was not invoked for this case.
              </p>
            )}
          </div>

          {auditLog && (
            <div className="panel-card">
              <h3 className="panel-title">Audit log excerpt</h3>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div>Run: {auditLog.run_id}</div>
                <div>Tools: {(auditLog.tools_called || []).join(', ') || 'none'}</div>
                <div>LangSmith project: {import.meta.env.VITE_LANGSMITH_PROJECT || 'ai-finance-controller'}</div>
              </div>
            </div>
          )}

          <div className="panel-card" style={{ border: '1px solid rgba(99, 102, 241, 0.3)' }}>
            <h3 className="panel-title">Human review action</h3>
            {!invg && (
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                Run the cut-off audit before recording a human decision.
              </p>
            )}
            <form onSubmit={handleSubmitReview} className="review-actions">
              <input
                className="search-input"
                style={{ minWidth: 0, width: '100%' }}
                value={reviewer}
                onChange={(e) => setReviewer(e.target.value)}
                placeholder="Reviewer name"
                required
              />
              <div className="radio-group">
                <label className={`radio-label ${decision === 'APPROVE' ? 'checked' : ''}`}>
                  <input type="radio" name="decision" value="APPROVE" checked={decision === 'APPROVE'} onChange={() => setDecision('APPROVE')} />
                  <div>
                    <strong>Approve</strong>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Accept the recommendation. Does not post ledger entries.</div>
                  </div>
                </label>
                <label className={`radio-label ${decision === 'REJECT' ? 'checked' : ''}`}>
                  <input type="radio" name="decision" value="REJECT" checked={decision === 'REJECT'} onChange={() => setDecision('REJECT')} />
                  <div>
                    <strong>Reject</strong>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Disagree with period classification.</div>
                  </div>
                </label>
                <label className={`radio-label ${decision === 'REQUEST_MORE_EVIDENCE' ? 'checked' : ''}`}>
                  <input type="radio" name="decision" value="REQUEST_MORE_EVIDENCE" checked={decision === 'REQUEST_MORE_EVIDENCE'} onChange={() => setDecision('REQUEST_MORE_EVIDENCE')} />
                  <div>
                    <strong>Request more evidence</strong>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Keep the exception open until proof arrives.</div>
                  </div>
                </label>
              </div>

              <textarea
                className="textarea-input"
                placeholder="Auditor comments…"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                required
              />

              <button type="submit" className="btn-primary" style={{ width: '100%', justifyContent: 'center' }} disabled={submitting || !invg}>
                {submitting ? 'Saving decision…' : 'Submit audit decision'}
              </button>
            </form>
          </div>

          {reviews.length > 0 && (
            <div className="panel-card">
              <h3 className="panel-title">Past reviews</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {reviews.map((rev, idx) => (
                  <div key={idx} style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '8px', fontSize: '0.85rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 'bold' }}>
                      <span>{rev.reviewer}</span>
                      <span className={`badge ${String(rev.decision).toLowerCase()}`} style={{ padding: '2px 6px', fontSize: '0.7rem' }}>{rev.decision}</span>
                    </div>
                    <div style={{ color: 'var(--text-secondary)', margin: '4px 0' }}>{rev.comment}</div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>{formatDate(rev.timestamp)}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Detail;
