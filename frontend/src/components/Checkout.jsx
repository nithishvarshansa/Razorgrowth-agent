import { useEffect, useState } from 'react'
import { createTestOrder, getApproval } from '../services/api'
import { openTestCheckout } from '../services/razorpayCheckout'

export default function Checkout({ id }) {
  const [a, setA] = useState()
  const [m, setM] = useState('')
  useEffect(() => {
    if (!id.startsWith('demo-')) return
    getApproval(id)
      .then((result) => setA(result || { status: 'missing_guardrail', message: 'No guardrail evaluation yet' }))
      .catch((error) => setA({ status: 'error', message: (error && error.message) || 'Guardrail evaluation unavailable' }))
  }, [id])
  if (!a) return null
  if (a.status === 'missing_guardrail') return <small style={{ color: 'var(--text-faint)' }}>{a.message}</small>
  if (a.status === 'error') return <small className="error-box">{a.message}</small>
  if (a.status !== 'approved') return null
  const start = async () => {
    setM('Creating TEST MODE order…')
    try {
      const order = await createTestOrder(id)
      setM('Opening TEST MODE checkout…')
      await openTestCheckout(order)
      setM('Payment verified')
    } catch (e) { setM(e.message) }
  }
  return (
    <div style={{ marginTop: 10 }}>
      <button className="btn btn-secondary" onClick={start}>Start Test Checkout</button>
      {m && <small style={{ display: 'block', marginTop: 6, color: 'var(--text-faint)' }}>{m}</small>}
    </div>
  )
}
