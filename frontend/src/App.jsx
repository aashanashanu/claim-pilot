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
  const [storefront, setStorefront] = useState({
    recipient_email: '',
    recipient_email_configured: false,
    gmail_ready: { status: 'error', code: 'UNKNOWN', message: 'Not loaded yet' },
    catalog: [],
    orders: [],
    activities: [],
    pending_decision_items: [],
  })
  const [loading, setLoading] = useState(true)
  const [storefrontLoading, setStorefrontLoading] = useState(true)
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

  const fetchStorefront = async () => {
    try {
      setError('')
      const response = await fetch(`${API_BASE}/storefront`)
      if (!response.ok) {
        throw new Error(`Storefront request failed: ${response.status}`)
      }
      const data = await response.json()
      setStorefront(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setStorefrontLoading(false)
    }
  }

  const fetchAll = async () => {
    setLoading(true)
    setStorefrontLoading(true)
    await Promise.all([fetchSnapshot(), fetchStorefront()])
  }

  useEffect(() => {
    fetchAll()
  }, [])

  const storefrontOrdersByProduct = useMemo(() => {
    const mapping = new Map()
    for (const order of storefront.orders || []) {
      mapping.set(order.product_id, order)
    }
    return mapping
  }, [storefront.orders])

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
      await fetchAll()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const seedStorefront = async () => {
    setStorefrontLoading(true)
    try {
      setError('')
      const response = await fetch(`${API_BASE}/storefront/seed-demo`, {
        method: 'POST',
      })
      if (!response.ok) {
        throw new Error(`Storefront seed failed: ${response.status}`)
      }
      await fetchAll()
    } catch (err) {
      setError(err.message)
    } finally {
      setStorefrontLoading(false)
    }
  }

  const purchaseProduct = async (productId) => {
    setStorefrontLoading(true)
    try {
      setError('')
      const response = await fetch(`${API_BASE}/storefront/orders/${productId}`, {
        method: 'POST',
      })
      if (!response.ok) {
        throw new Error(`Purchase request failed: ${response.status}`)
      }
      await fetchAll()
    } catch (err) {
      setError(err.message)
    } finally {
      setStorefrontLoading(false)
    }
  }

  const priceDrop = async (orderId, currentPrice) => {
    setStorefrontLoading(true)
    try {
      setError('')
      const nextPrice = Math.max(Number(currentPrice || 0) - 20, 1)
      const response = await fetch(`${API_BASE}/storefront/orders/${orderId}/price-drop?new_price=${nextPrice}`, {
        method: 'POST',
      })
      if (!response.ok) {
        throw new Error(`Price drop request failed: ${response.status}`)
      }
      await fetchAll()
    } catch (err) {
      setError(err.message)
    } finally {
      setStorefrontLoading(false)
    }
  }

  const startReturn = async (orderId) => {
    setStorefrontLoading(true)
    try {
      setError('')
      const response = await fetch(`${API_BASE}/storefront/orders/${orderId}/return`, {
        method: 'POST',
      })
      if (!response.ok) {
        throw new Error(`Return request failed: ${response.status}`)
      }
      await fetchAll()
    } catch (err) {
      setError(err.message)
    } finally {
      setStorefrontLoading(false)
    }
  }

  const fileClaim = async (orderId) => {
    setStorefrontLoading(true)
    try {
      setError('')
      const response = await fetch(`${API_BASE}/storefront/orders/${orderId}/claim?claim_type=damaged_item`, {
        method: 'POST',
      })
      if (!response.ok) {
        throw new Error(`Claim request failed: ${response.status}`)
      }
      await fetchAll()
    } catch (err) {
      setError(err.message)
    } finally {
      setStorefrontLoading(false)
    }
  }

  const captureDecision = async (orderId, decision) => {
    setLoading(true)
    try {
      setError('')
      const response = await fetch(
        `${API_BASE}/decisions/${orderId}?decision=${encodeURIComponent(decision)}`,
        {
          method: 'POST',
        },
      )
      if (!response.ok) {
        throw new Error(`Decision capture failed: ${response.status}`)
      }
      await fetchAll()
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
            <button type="button" className="refresh-button" onClick={fetchAll}>
              Refresh
            </button>
          </div>

          <section className="storefront-section">
            <div className="storefront-header">
              <div>
                <h3>Storefront demo</h3>
                <p>
                  Real Gmail order mails are sent from the storefront to{' '}
                  <strong>{storefront.recipient_email || 'configure CLAIMPILOT_GMAIL_TARGET_ADDRESS'}</strong>.
                </p>
              </div>
              <button type="button" className="refresh-button" disabled={storefrontLoading} onClick={seedStorefront}>
                Seed demo storefront
              </button>
            </div>

            <div className="storefront-status-row">
              <span className={`badge ${storefront.gmail_ready?.status === 'ok' ? '' : 'needs_decision'}`}>
                Gmail: {storefront.gmail_ready?.code || 'UNKNOWN'}
              </span>
              <span className="muted-inline">
                {storefront.gmail_ready?.message || 'Gmail readiness unavailable'}
              </span>
            </div>

            <div className="storefront-grid">
              {(storefront.catalog || []).length === 0 ? (
                <div className="storefront-empty">No storefront products yet.</div>
              ) : (
                (storefront.catalog || []).map((product) => {
                  const order = storefrontOrdersByProduct.get(product.product_id)
                  return (
                    <article className="storefront-card" key={product.product_id}>
                      <div className="storefront-card-top">
                        <div>
                          <h4>{product.name}</h4>
                          <p>{product.description}</p>
                        </div>
                        <span className={`badge ${order ? '' : 'needs_decision'}`}>
                          {order ? order.status : 'ready'}
                        </span>
                      </div>

                      <div className="storefront-meta">
                        <span>${Number(product.price || 0).toFixed(2)}</span>
                        <span>{product.return_window_days} day return window</span>
                      </div>

                      <div className="storefront-actions">
                        <button type="button" className="action-button" disabled={storefrontLoading} onClick={() => purchaseProduct(product.product_id)}>
                          Buy
                        </button>
                        <button
                          type="button"
                          className="action-button subtle"
                          disabled={storefrontLoading || !order}
                          onClick={() => priceDrop(order?.order_id, order?.current_price)}
                        >
                          Price drop
                        </button>
                        <button
                          type="button"
                          className="action-button subtle"
                          disabled={storefrontLoading || !order}
                          onClick={() => startReturn(order?.order_id)}
                        >
                          Return
                        </button>
                        <button
                          type="button"
                          className="action-button subtle"
                          disabled={storefrontLoading || !order}
                          onClick={() => fileClaim(order?.order_id)}
                        >
                          Claim
                        </button>
                      </div>

                      {order ? (
                        <div className="storefront-order-note">
                          Order {order.order_id} sent as {order.email_kind} mail to {order.recipient_email}.
                        </div>
                      ) : (
                        <div className="storefront-order-note">No order created yet.</div>
                      )}
                    </article>
                  )
                })
              )}
            </div>

            <div className="storefront-order-table">
              <h4>Recent storefront orders</h4>
              <table className="table">
                <thead>
                  <tr>
                    <th>Order</th>
                    <th>Item</th>
                    <th>Status</th>
                    <th>Mail</th>
                  </tr>
                </thead>
                <tbody>
                  {(storefront.orders || []).length === 0 ? (
                    <tr>
                      <td colSpan="4">Seed the storefront to create real Gmail order mails.</td>
                    </tr>
                  ) : (
                    (storefront.orders || []).map((order) => (
                      <tr key={order.order_id}>
                        <td>{order.order_id}</td>
                        <td>{order.item_name}</td>
                        <td>{order.status}</td>
                        <td>{order.email_kind}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>

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

          <div className="table-card" style={{ marginTop: '18px' }}>
            <div className="main-header" style={{ marginBottom: '12px' }}>
              <h3>Pending decisions</h3>
              <span className="badge needs_decision">{snapshot.pending_decisions || 0} open</span>
            </div>
            <div className="pending-grid">
              {(snapshot.pending_decision_items || []).length === 0 ? (
                <div className="timeline-item">No pending decisions right now.</div>
              ) : (
                (snapshot.pending_decision_items || []).map((item) => (
                  <article className="pending-card" key={item.order_id}>
                    <div className="storefront-card-top">
                      <div>
                        <h4>{item.order_id}</h4>
                        <p>{item.details}</p>
                      </div>
                      <span className="badge needs_decision">{item.status}</span>
                    </div>
                    <div className="storefront-meta">
                      <span>User {item.user_id}</span>
                      <span>{item.created_at || 'recent'}</span>
                    </div>
                    <div className="storefront-actions">
                      <button
                        type="button"
                        className="action-button"
                        disabled={loading}
                        onClick={() => captureDecision(item.order_id, 'approve_photo')}
                      >
                        Approve
                      </button>
                      <button
                        type="button"
                        className="action-button subtle"
                        disabled={loading}
                        onClick={() => captureDecision(item.order_id, 'reject')}
                      >
                        Reject
                      </button>
                    </div>
                  </article>
                ))
              )}
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
