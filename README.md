# RazorGrowth Agent

RazorGrowth Agent is an AI-powered growth agent built for the **Razorpay AI Buildathon — Track 01: AI Growth & Agentic Commerce**.

It turns Razorpay **Test Mode** transaction signals into explainable, bounded, approval-gated growth actions, executes only what the merchant approves, and measures the outcome so the agent can propose a next action.

## Core workflow

```text
Transaction Signals
  → AI Analysis
    → Opportunity Discovery
      → Ranking
        → Recommendation
          → Evidence & Reasoning
            → Guardrails
              → Merchant Approval
                → Razorpay TEST MODE Execution
                  → Measurement
                    → Next Action
```

How the decision responsibility is split:

- **The AI recommends** the growth action from observed transaction signals.
- **Guardrails validate** whether that action is eligible to be offered at all. A blocked action never reaches execution.
- **The merchant makes the final approval decision.** Nothing is executed without an explicit approve.
- **The system executes** only the approved action.
- **Razorpay TEST MODE provides the payment execution environment.**
- **No real money is involved.** The backend refuses any Razorpay key id that does not start with `rzp_test_`.
- **Measurement** records the outcome of the executed action, which feeds the next action proposal.

## Technology stack

- Frontend: React 19, Vite 6, JavaScript
- Backend: Python 3.12, FastAPI, Uvicorn
- Database: SQLite (local file; schema created automatically)
- Payments: Razorpay Test Mode REST API + Razorpay Checkout (Test Mode)

```text
React + Vite frontend  <-->  FastAPI backend  <-->  SQLite (local)
                                     |
                            Razorpay Test Mode API
```

## Requirements

- Node.js 20+ (developed on Node 22)
- Python 3.11+ (developed on Python 3.12)
- npm 10+
- Your own **Razorpay Test Mode** Key ID and Key Secret

No database server is required. The SQLite file and its schema are created automatically on first use.

## Setup

All commands are run from the project root unless stated otherwise.

1. Clone the repository and enter it:

   ```powershell
   git clone <repository-url>
   cd razorpay
   ```

2. Create the backend environment file and fill in your own Test Mode credentials:

   ```powershell
   copy backend\.env.example backend\.env
   ```

   On macOS/Linux:

   ```bash
   cp backend/.env.example backend/.env
   ```

3. Install backend dependencies:

   ```powershell
   pip install -r backend/requirements.txt
   ```

4. Install frontend dependencies:

   ```powershell
   cd frontend
   npm install
   cd ..
   ```

5. Install the root dev dependency used to start both services together:

   ```powershell
   npm install
   ```

## Environment variables

Copy `backend/.env.example` to `backend/.env` and fill in the values locally. `backend/.env` is git-ignored and must never be committed.

Variables you must provide yourself:

| Variable | Required | Notes |
| --- | --- | --- |
| `RAZORPAY_KEY_ID` | Yes | Your **Test Mode** Key ID from the Razorpay Dashboard. Must start with `rzp_test_`. |
| `RAZORPAY_KEY_SECRET` | Yes | Your **Test Mode** Key Secret. Secret value — never commit it, never share it, never place it in frontend code. |

Variables with working defaults (change only if needed):

| Variable | Default |
| --- | --- |
| `APP_NAME` | `AI Growth Agent API` |
| `ENVIRONMENT` | `development` |
| `DATABASE_URL` | `sqlite:///./data/ai_growth_agent.db` |
| `FRONTEND_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` |

The frontend has an optional `frontend/.env` (see `frontend/.env.example`) with `VITE_API_BASE_URL`. It defaults to `http://127.0.0.1:8000` and normally needs no change. **The frontend never receives API secrets.**

Use **Test Mode credentials only**. Do not use production/live credentials for this demo.

## Run

From the project root:

```powershell
npm run dev
```

This starts the FastAPI backend and the React + Vite frontend together.

- Frontend: `http://127.0.0.1:5173`
- Backend health check: `http://127.0.0.1:8000/health`
- FastAPI interactive docs: `http://127.0.0.1:8000/docs`

To run the services separately instead, from the project root:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

```powershell
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Backend tests:

```powershell
python -m pytest backend/tests
```

Frontend production build:

```powershell
cd frontend
npm run build
```

## Demo flow

Open `http://127.0.0.1:5173` and follow this sequence:

1. Open **Overview**.
2. Open **Growth Strategy**.
3. Click **Run Growth Demo**.
4. Review the AI recommendation.
5. Inspect the evidence and reasoning behind it.
6. Review the guardrail decision.
7. Approve as the merchant (or reject — a rejection is recorded and stops execution).
8. Create the Razorpay **Test Mode** order.
9. Complete the Razorpay Test Mode checkout.
10. Verify the measurement result.
11. Review **Experiment History** and the proposed **Next Action**.

For Test Mode checkout, use the test card details published in the Razorpay Test Mode documentation. No real money moves at any point.

## Important data disclosure

The demonstration uses **controlled Test Mode fixture data**, clearly marked in the application as `DEMO / TEST DATA`. This fixture exists so the growth loop can be demonstrated end to end without real merchant history.

The application does **not** fabricate unavailable real merchant history, and the demo fixture must not be read as real merchant history. Where real Razorpay Test Mode orders and payments are available through the API, they are used as-is; the fixture is kept isolated from that data.

## Security

- **Never commit `.env`.** `backend/.env` and any other `.env` file are excluded by `.gitignore`.
- **Never expose API secrets.** The Razorpay Key Secret stays in backend environment variables only and is never sent to the frontend.
- **Use Razorpay TEST MODE credentials.** The backend rejects any key id that is not `rzp_test_…`.
- **Do not use production/live credentials** with this project.
- The repository contains no real credentials. `.env.example` files contain variable names and comments only.
- Local SQLite database files, database backups, build output, virtual environments, and `node_modules` are git-ignored and are not part of the repository.
