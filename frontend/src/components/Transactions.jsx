import React, { useState } from 'react';
import { classificationBadge, formatLabel } from '../utils';

function Transactions({ transactions, onSelectTx }) {
  const [search, setSearch] = useState('');
  const [classFilter, setClassFilter] = useState('ALL');
  const [typeFilter, setTypeFilter] = useState('ALL');
  const [reviewFilter, setReviewFilter] = useState('ALL');
  const [minAmount, setMinAmount] = useState('');
  const [maxConfidence, setMaxConfidence] = useState('');

  const filtered = transactions.filter(t => {
    const matchesSearch = t.transaction_id.toLowerCase().includes(search.toLowerCase()) || 
                          (t.vendor_id && t.vendor_id.toLowerCase().includes(search.toLowerCase()));
    
    const matchesClass = classFilter === 'ALL' || t.classification === classFilter;
    const matchesType = typeFilter === 'ALL' || t.transaction_type === typeFilter;
    const matchesReview = reviewFilter === 'ALL'
      || (reviewFilter === 'NEEDS_REVIEW' && t.human_review_required)
      || (reviewFilter === 'NO_REVIEW' && !t.human_review_required);
    const matchesAmount = minAmount === '' || t.amount >= Number(minAmount);
    const matchesConfidence = maxConfidence === '' || (t.confidence * 100) <= Number(maxConfidence);
    
    return matchesSearch && matchesClass && matchesType && matchesReview && matchesAmount && matchesConfidence;
  });

  return (
    <div>
      <div className="header-bar">
        <div className="header-title">
          <h1>General Ledger Review</h1>
          <p>Complete ledger list and auditor analysis</p>
        </div>
      </div>

      <div className="table-card">
        {/* Filters Header */}
        <div className="table-header-filters">
          <input 
            type="text" 
            className="search-input" 
            placeholder="Search by Transaction ID or Vendor..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />

          <div className="filter-group">
            <select 
              className="select-input"
              value={classFilter}
              onChange={(e) => setClassFilter(e.target.value)}
            >
              <option value="ALL">All Classifications</option>
              <option value="BEFORE_CUTOFF">Before Cutoff</option>
              <option value="AFTER_CUTOFF">After Cutoff</option>
              <option value="POTENTIAL_MISSTATEMENT">Potential Misstatement</option>
              <option value="UNRESOLVED">Unresolved Exception</option>
              <option value="UNAUDITED">Unaudited</option>
            </select>

            <select 
              className="select-input"
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
            >
              <option value="ALL">All Types</option>
              <option value="goods_purchase">Goods Purchase</option>
              <option value="service_purchase">Service Purchase</option>
            </select>

            <select
              className="select-input"
              value={reviewFilter}
              onChange={(e) => setReviewFilter(e.target.value)}
            >
              <option value="ALL">All review statuses</option>
              <option value="NEEDS_REVIEW">Needs human review</option>
              <option value="NO_REVIEW">No review required</option>
            </select>

            <input
              type="number"
              className="search-input"
              style={{ minWidth: 140 }}
              placeholder="Min amount"
              value={minAmount}
              onChange={(e) => setMinAmount(e.target.value)}
            />
            <input
              type="number"
              className="search-input"
              style={{ minWidth: 160 }}
              placeholder="Max confidence %"
              value={maxConfidence}
              onChange={(e) => setMaxConfidence(e.target.value)}
            />
          </div>
        </div>

        {/* Transactions Table */}
        <table className="custom-table">
          <thead>
            <tr>
              <th>Transaction ID</th>
              <th>Type</th>
              <th>Amount</th>
              <th>Transaction Date</th>
              <th>Posting Date</th>
              <th>Period Status</th>
              <th>Confidence</th>
              <th>Audit Status</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((t) => (
              <tr key={t.transaction_id} onClick={() => onSelectTx(t.transaction_id)}>
                <td><strong>{t.transaction_id}</strong></td>
                <td>{t.transaction_type.replace('_', ' ')}</td>
                <td>{t.currency} {t.amount.toLocaleString()}</td>
                <td>{t.transaction_date.split('T')[0]}</td>
                <td>{t.posting_date.split('T')[0]}</td>
                <td>
                  <span className={`badge ${classificationBadge(t.classification)}`}>
                    {formatLabel(t.classification)}
                  </span>
                </td>
                <td>{t.classification !== 'UNAUDITED' ? `${(t.confidence * 100).toFixed(0)}%` : '-'}</td>
                <td>
                  <span className={`badge ${t.status.toLowerCase()}`}>
                    {t.status}
                  </span>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan="8" style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '24px' }}>
                  No matching records found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default Transactions;
