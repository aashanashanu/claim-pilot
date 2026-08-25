import { useEffect, useMemo, useState } from 'react'
import './App.css'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const scenarioLabels = {
  price_drop: 'Price drop',
  damaged_item: 'Damaged item',
  return_window: 'Return window',
}

function App() {
  const [snapshot, setSnapshot] = useState({
    active_orders: 0,
    pending_decisions: 0,
    last_action: 'idle',
    decision_source: 'unknown',
    latest_audit: 'No activity yet',
    orders: [],
    audit_records: [],
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const fetchSnapshot = async () => {
    try {
      setError('')
      const response = await fetch(`${API_BASE}/demo`)
      if (!response.ok) {
        throw new Error(`API request failed: ${response.status}`)
      }
      const data = await response.json()
      setSnapshot(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSnapshot()
  }, [])

  const triggerScenario = async (scenario) => {
    setLoading(true)
    try {
      const response = await fetch(`${API_BASE}/demo/scenario/${scenario}`, {
        method: 'POST',
      })
      if (!response.ok) {
        throw new Error(`Scenario request failed: ${response.status}`)
      }
      const data = await response.json()
      setSnapshot((current) => ({
        ...current,
        last_action: data.action || current.last_action,
        latest_audit: `${data.action}:${data.reason || 'decision processed'}`,
      }))
      await fetchSnapshot()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const recentAudit = useMemo(
    () => [...(snapshot.audit_records || [])].slice(-6).reverse(),
    [snapshot.audit_records],
  )

  return (
    <div className="app-shell">
      <div className="dashboard">
        <aside className="panel sidebar">
          <h1 className="brand">ClaimPilot</h1>
          <p className="muted">Desktop demo dashboard for purchase exception decisions.</p>

          <div className="actions">
            {Object.entries(scenarioLabels).map(([scenario, label]) => (
              <button
                key={scenario}
                type="button"
                className="action-button"
                disabled={loading}
                onClick={() => triggerScenario(scenario)}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="summary-grid">
            <div className="kpi">
              <span className="label">Active orders</span>
              <span className="value">{snapshot.active_orders}</span>
            </div>
            <div className="kpi">
              <span className="label">Pending decisions</span>
              <span className="value">{snapshot.pending_decisions}</span>
            </div>
            <div className="kpi">
              <span className="label">Last action</span>
              <span className="value">{snapshot.last_action}</span>
            </div>
            <div className="kpi">
              <span className="label">Decision source</span>
              <span className="value">{snapshot.decision_source || 'unknown'}</span>
            </div>
          </div>

          <div className="status-box">
            {error ? `Connection issue: ${error}` : snapshot.latest_audit}
          </div>
        </aside>

        <main className="panel main">
          <div className="main-header">
            <div className="header-title">Operations overview</div>
            <button type="button" className="refresh-button" onClick={fetchSnapshot}>
              Refresh
            </button>
          </div>

          <div className="metrics-row">
            <div className="metric-card">
              <h3>Auto resolved</h3>
              <strong>{(snapshot.audit_records || []).filter((r) => r.action === 'auto_resolve').length}</strong>
            </div>
            <div className="metric-card">
              <h3>Needs decision</h3>
              <strong>{(snapshot.audit_records || []).filter((r) => r.action === 'needs_decision').length}</strong>
            </div>
            <div className="metric-card">
              <h3>Order flow</h3>
              <strong>{snapshot.active_orders}</strong>
            </div>
          </div>

          <div className="table-card">
            <h3>Orders</h3>
            <table className="table">
              <thead>
                <tr>
                  <th>Order ID</th>
                  <th>Item</th>
                  <th>Merchant</th>
                  <th>Price</th>
                </tr>
              </thead>
              <tbody>
                {(snapshot.orders || []).length === 0 ? (
                  <tr>
                    <td colSpan="4">No orders yet</td>
                  </tr>
                ) : (
                  (snapshot.orders || []).map((order) => (
                    <tr key={order.order_id}>
                      <td>{order.order_id}</td>
                      <td>{order.item_name}</td>
                      <td>{order.merchant}</td>
                      <td>${Number(order.current_price || 0).toFixed(2)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="timeline-card" style={{ marginTop: '18px' }}>
            <h3>Audit timeline</h3>
            <div className="timeline">
              {recentAudit.length === 0 ? (
                <div className="timeline-item">No audit entries yet.</div>
              ) : (
                recentAudit.map((entry, index) => (
                  <div className="timeline-item" key={`${entry.order_id}-${entry.action}-${index}`}>
                    <div>
                      <strong>{entry.action}</strong>
                      <div>{entry.details}</div>
                    </div>
                    <span className={`badge ${entry.action === 'needs_decision' ? 'needs_decision' : ''}`}>
                      {entry.status}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}

export default App
