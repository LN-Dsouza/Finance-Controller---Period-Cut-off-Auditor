import React, { useState, useEffect } from 'react';
import Dashboard from './components/Dashboard';
import Transactions from './components/Transactions';
import Detail from './components/Detail';
import ExceptionQueue from './components/ExceptionQueue';
import AuditTrail from './components/AuditTrail';
import Evaluation from './components/Evaluation';

const API_BASE = 'http://127.0.0.1:8000/api';

function App() {
  const [activePage, setActivePage] = useState('dashboard');
  const [selectedTxId, setSelectedTxId] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [exceptions, setExceptions] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [policies, setPolicies] = useState([]);
  const [langsmithStatus, setLangsmithStatus] = useState(null);
  const [cutoffDate, setCutoffDate] = useState('2026-12-31');
  const [windowDays, setWindowDays] = useState(7);
  const [loading, setLoading] = useState(false);
  const [auditRunning, setAuditRunning] = useState(false);
  const [seedLoading, setSeedLoading] = useState(false);

  // Fetch initial data
  const fetchData = async () => {
    setLoading(true);
    try {
      const txRes = await fetch(`${API_BASE}/transactions`);
      const txData = await txRes.json();
      setTransactions(txData);

      const exRes = await fetch(`${API_BASE}/exceptions`);
      const exData = await exRes.json();
      setExceptions(exData);

      const metRes = await fetch(`${API_BASE}/metrics`);
      if (metRes.ok) {
        setMetrics(await metRes.json());
      }

      const polRes = await fetch(`${API_BASE}/policies`);
      if (polRes.ok) {
        setPolicies(await polRes.json());
      }

      const lsRes = await fetch(`${API_BASE}/langsmith/status`);
      if (lsRes.ok) {
        setLangsmithStatus(await lsRes.json());
      }
    } catch (err) {
      console.error("Error loading API data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleRunAudit = async (customDate, customWindow) => {
    setAuditRunning(true);
    try {
      const dateToUse = customDate || `${cutoffDate} 23:59:59`;
      const windowToUse = Number(customWindow !== undefined ? customWindow : windowDays);
      const res = await fetch(`${API_BASE}/audit/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cutoff_date: dateToUse, window_days: windowToUse })
      });
      const data = await res.json();
      setMetrics(data);
      await fetchData();
      alert("Cut-Off Audit completed successfully! Ledgers updated.");
    } catch (err) {
      console.error("Error running audit:", err);
      alert("Failed to execute audit run. Check if backend is running.");
    } finally {
      setAuditRunning(false);
    }
  };

  const handleSeedData = async () => {
    setSeedLoading(true);
    try {
      const res = await fetch(`${API_BASE}/seed`, { method: 'POST' });
      if (res.ok) {
        await fetchData();
        alert("Database successfully reset and seeded with 75 synthetic records.");
      } else {
        alert("Failed to reload synthetic dataset.");
      }
    } catch (err) {
      console.error("Error reloading dataset:", err);
      alert("Failed to reload dataset.");
    } finally {
      setSeedLoading(false);
    }
  };

  const navigateToDetail = (txId) => {
    setSelectedTxId(txId);
    setActivePage('detail');
  };

  const renderActivePage = () => {
    switch (activePage) {
      case 'dashboard':
        return (
          <Dashboard 
            metrics={metrics} 
            transactions={transactions} 
            exceptions={exceptions} 
            onRunAudit={handleRunAudit}
            auditRunning={auditRunning}
            onSelectTx={navigateToDetail}
            cutoffDate={cutoffDate}
            setCutoffDate={setCutoffDate}
            windowDays={windowDays}
            setWindowDays={setWindowDays}
            onSeedData={handleSeedData}
            seedLoading={seedLoading}
            policies={policies}
            langsmithStatus={langsmithStatus}
          />
        );
      case 'transactions':
        return (
          <Transactions 
            transactions={transactions} 
            onSelectTx={navigateToDetail} 
          />
        );
      case 'exceptions':
        return (
          <ExceptionQueue 
            exceptions={exceptions} 
            onSelectTx={navigateToDetail} 
          />
        );
      case 'detail':
        return (
          <Detail 
            transactionId={selectedTxId} 
            onBack={() => setActivePage('transactions')} 
            onReviewSubmitted={fetchData}
          />
        );
      case 'audit':
        return <AuditTrail onSelectTx={navigateToDetail} />;
      case 'evaluation':
        return (
          <Evaluation 
            metrics={metrics} 
            onRunAudit={handleRunAudit} 
            auditRunning={auditRunning}
            cutoffDate={cutoffDate}
            windowDays={windowDays}
            langsmithStatus={langsmithStatus}
          />
        );
      default:
        return <div>Page Not Found</div>;
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div className="logo-section">
          <div className="logo-icon">F</div>
          <div className="logo-text">AI Controller</div>
        </div>

        <nav className="nav-links">
          <button 
            className={`nav-item ${activePage === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActivePage('dashboard')}
          >
            Dashboard
          </button>
          
          <button 
            className={`nav-item ${activePage === 'transactions' ? 'active' : ''}`}
            onClick={() => setActivePage('transactions')}
          >
            Ledger Entries
          </button>

          <button 
            className={`nav-item ${activePage === 'exceptions' ? 'active' : ''}`}
            onClick={() => setActivePage('exceptions')}
          >
            Flagged Queue
            {exceptions.length > 0 && (
              <span className="nav-badge">{exceptions.length}</span>
            )}
          </button>

          <button 
            className={`nav-item ${activePage === 'audit' ? 'active' : ''}`}
            onClick={() => setActivePage('audit')}
          >
            Audit Trail
          </button>

          <button 
            className={`nav-item ${activePage === 'evaluation' ? 'active' : ''}`}
            onClick={() => setActivePage('evaluation')}
          >
            System Evaluation
          </button>
        </nav>

        <div className="sidebar-footer">
          <p>Cut-Off Auditor v1.0</p>
          <p>Period-End: {cutoffDate}</p>
        </div>
      </aside>

      {/* Main Page Display */}
      <main className="main-content">
        {loading && <div style={{ color: 'var(--text-secondary)', marginBottom: 20 }}>Refreshing records...</div>}
        {renderActivePage()}
      </main>
    </div>
  );
}

export default App;
