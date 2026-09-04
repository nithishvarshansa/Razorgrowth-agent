const base = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
async function get(path) { const response = await fetch(`${base}${path}`); if (!response.ok) { const body = await response.json().catch(() => ({})); const error = new Error(body.detail || `Request failed (${response.status})`); error.status = response.status; throw error } return response.json() }
// A 404 on these endpoints means "not evaluated / no events yet" — an expected state, not a failure.
async function getIfAvailable(path) { const response = await fetch(`${base}${path}`); if (response.status === 404) return null; if (!response.ok) { const body = await response.json().catch(() => ({})); const error = new Error(body.detail || `Request failed (${response.status})`); error.status = response.status; throw error } return response.json() }
async function post(path) { const response = await fetch(`${base}${path}`, { method: 'POST' }); if (!response.ok) { const body = await response.json().catch(() => ({})); const error = new Error(body.detail || `Request failed (${response.status})`); error.status = response.status; throw error } return response.json() }
export const getHealth = () => get('/health')
export const getAnalytics = () => get('/api/analytics')
export const getOpportunities = () => get('/api/analytics/opportunities')
export const getAnalyticsSummary = () => get('/api/analytics/summary')
export const getAgentRuns = () => get('/api/agent/runs')
export const getExperimentHistory = () => get('/api/experiments/history')
export const getApproval = (id) => getIfAvailable(`/api/guardrails/${id}`)
export const getMeasurement = (id) => getIfAvailable(`/api/measurement/${id}`)
export const createDemoRecommendation = () => post('/api/demo/recommendation')
export const runGrowthAgent = () => post('/api/agent/run')
export const syncTestModeData = () => post('/api/analytics/sync')
export const evaluateGuardrail = (id) => post(`/api/guardrails/evaluate/${id}`)
export const approveRecommendation = (id) => post(`/api/guardrails/${id}/approve`)
export const rejectRecommendation = (id) => post(`/api/guardrails/${id}/reject`)
export const createTestOrder = (id) => fetch(`${base}/api/commerce/${id}/create-test-order`,{method:'POST'}).then(async r=>{if(!r.ok){const error=new Error((await r.json()).detail||'Unable to create Test Mode order');error.status=r.status;throw error};return r.json()})
export const verifyTestPayment = (payload) => fetch(`${base}/api/commerce/verify-payment`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}).then(async r=>{if(!r.ok){const error=new Error((await r.json()).detail||'Verification failed');error.status=r.status;throw error};return r.json()})
export const addMeasurementEvent = (id, eventType, metadata) => fetch(`${base}/api/measurement/${id}/event`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({event_type:eventType,metadata})}).then(async r=>{if(!r.ok)throw new Error((await r.json()).detail||'Unable to record event');return r.json()})
