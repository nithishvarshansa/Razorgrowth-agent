import { useEffect, useRef, useState } from 'react'
import AgentActivity from './components/AgentActivity'
import ExperimentHistory from './components/ExperimentHistory'
import GrowthStrategy from './components/GrowthStrategy'
import Header from './components/Header'
import MetricCard from './components/MetricCard'
import OpportunityPipeline from './components/OpportunityPipeline'
import Sidebar from './components/Sidebar'
import { IconActivity, IconAnalytics, IconOrders, IconPayments, IconPipeline } from './components/icons'
import { getAgentRuns, getAnalytics, getAnalyticsSummary, getHealth, getOpportunities } from './services/api'
import './styles.css'

const SECTION_IDS = ['overview', 'growth-strategy', 'opportunities', 'agent-activity', 'experiment-history', 'analytics', 'settings']

function useActiveSection() {
  const [active, setActive] = useState('overview')
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)
        if (visible[0]) setActive(visible[0].target.id)
      },
      { rootMargin: '-15% 0px -70% 0px', threshold: 0 }
    )
    SECTION_IDS.forEach((id) => {
      const el = document.getElementById(id)
      if (el) observer.observe(el)
    })
    return () => observer.disconnect()
  }, [])
  return active
}

export default function App() {
  const [s, setS] = useState({ loading: true })
  const [summary, setSummary] = useState(null)
  const firstLoad = useRef(true)

  const load = () => {
    setS((prev) => ({ ...prev, loading: true }))
    Promise.allSettled([getHealth(), getAnalytics(), getOpportunities(), getAgentRuns()]).then(([h, a, o, r]) =>
      setS({ loading: false, ok: h.status === 'fulfilled', a: a.value, o: o.value, r: r.value, oe: o.reason, re: r.reason })
    )
    getAnalyticsSummary().then(setSummary).catch(() => setSummary(null))
  }
  useEffect(() => { load(); firstLoad.current = false }, [])

  const active = useActiveSection()
  const orders = s.a?.orders || []
  const payments = s.a?.payments || []
  const opportunityCount = s.o?.opportunities?.length || 0
  const runCount = s.r?.runs?.length || 0

  return (
    <div className="shell">
      <Sidebar active={active} razorpayConnected={!!s.ok} />
      <div className="main">
        <Header active={active} razorpayConnected={!!s.ok} onRefresh={load} refreshing={s.loading && !firstLoad.current} />
        <div className="page">

          <section id="overview" className="page-section enter">
            <span className="command-eyebrow">AI Growth Command Center</span>
            <h2 className="command-title">See the one action worth taking next.</h2>
            <p className="command-sub">The Growth Agent turns Test Mode transaction data into a single, evidence-ranked recommendation — nothing executes without your approval.</p>
          </section>

          <GrowthStrategy />

          <section className="page-section enter metrics-strip">
            <div className="section-head">
              <h2>At a glance</h2>
            </div>
            <div className="metric-grid quiet">
              <MetricCard icon={IconOrders} label="Orders" value={orders.length || '--'} loading={s.loading} foot={!orders.length && !s.loading ? 'No data yet' : undefined} />
              <MetricCard icon={IconPayments} label="Payments" value={payments.length || '--'} loading={s.loading} foot={!payments.length && !s.loading ? 'No data yet' : undefined} />
              <MetricCard icon={IconPipeline} label="Opportunities" value={opportunityCount || '--'} loading={s.loading} foot={!opportunityCount && !s.loading ? 'No data yet' : undefined} />
              <MetricCard icon={IconActivity} label="Agent Runs" value={runCount || '--'} loading={s.loading} foot={!runCount && !s.loading ? 'No data yet' : undefined} />
            </div>
          </section>

          <section id="opportunities" className="page-section enter">
            <div className="section-head">
              <h2>Opportunity Pipeline</h2>
              <span className="section-sub">Real, evidence-based opportunities from stored Test Mode orders and payments</span>
            </div>
            {s.loading ? (
              <div className="skeleton" style={{ height: 120 }} />
            ) : s.oe ? (
              <div className="error-box">{s.oe.message || 'Unable to load opportunities.'}</div>
            ) : (
              <OpportunityPipeline opportunities={s.o?.opportunities} emptyReason={s.o?.reason} />
            )}
          </section>

          <section id="agent-activity" className="page-section enter">
            <div className="section-head">
              <h2>Agent Activity</h2>
              <span className="section-sub">Every recommendation the agent has produced</span>
            </div>
            <AgentActivity data={s.r} loading={s.loading} error={s.re} />
          </section>

          <section id="experiment-history" className="page-section enter">
            <div className="section-head">
              <h2>Experiment History &amp; Learning</h2>
              <span className="section-sub">See what the growth agent recommended, what the merchant decided, and what happened next</span>
            </div>
            <ExperimentHistory />
          </section>

          <section id="analytics" className="page-section enter">
            <div className="section-head">
              <h2>Analytics</h2>
              <span className="section-sub">Deterministic facts supported by stored Test Mode data — nothing estimated</span>
            </div>
            {!summary ? (
              <div className="skeleton" style={{ height: 100 }} />
            ) : (
              <div className="grid-3">
                <div className="card card-pad">
                  <div className="m-head" style={{ marginBottom: 10 }}><span className="m-icon"><IconOrders width={15} height={15} /></span></div>
                  <div className="m-value">{summary.orders?.count ?? '--'}</div>
                  <div className="m-foot">Stored orders</div>
                </div>
                <div className="card card-pad">
                  <div className="m-head" style={{ marginBottom: 10 }}><span className="m-icon"><IconPayments width={15} height={15} /></span></div>
                  <div className="m-value">{summary.payments?.captured_count ?? 0}<span style={{ fontSize: 13, color: 'var(--text-faint)', fontWeight: 600 }}> / {summary.payments?.count ?? 0}</span></div>
                  <div className="m-foot">Captured payments{summary.payments?.captured_amount_total != null ? ` · ${summary.payments.captured_amount_total / 100} total` : ''}</div>
                </div>
                <div className="card card-pad">
                  <div className="m-head" style={{ marginBottom: 10 }}><span className="m-icon"><IconAnalytics width={15} height={15} /></span></div>
                  <div className="m-value">{summary.customers?.identified_customer_count ?? '--'}</div>
                  <div className="m-foot">Identified customers · {summary.products?.identified_product_count ?? '--'} products</div>
                </div>
              </div>
            )}
          </section>

          <section id="settings" className="page-section enter">
            <div className="section-head"><h2>Settings</h2></div>
            <div className="card card-pad" style={{ color: 'var(--text-muted)', fontSize: 13.5 }}>
              Merchant configuration is managed via backend environment variables (Razorpay Test Mode credentials, CORS origins). Nothing to configure here yet.
            </div>
          </section>

        </div>
      </div>
    </div>
  )
}
