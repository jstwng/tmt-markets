# Vantage

A scientific investment research copilot (scientific, as defined by Stanford's MS&E 245A/B courses) that integrates a conversational AI agent with a comprehensive suite of quantitative finance tools, real-time market data, and persistent portfolio management.

## Features

**Copilot Interface**

- Natural language queries for portfolio construction, optimization, and market research
- Multi-turn conversations with persistent history
- Streaming responses with tool calling (portfolio optimization, backtesting, data fetching)
- Intent classification routing to specialized handlers

**Portfolio Dashboard**

- Saved portfolio viewer with performance metrics and equity curves
- Holdings breakdown with interactive charts
- Position table editing and historical performance slicing

**Market Terminal**

- Real-time panels: macro indicators, major indices, top movers, sector heatmaps, economic calendar
- Configurable auto-refresh intervals
- Data sourced from OpenBB SDK, yfinance, and FRED

**Quantitative Tools**

- Mean-variance portfolio optimization (max Sharpe, min variance, risk parity)
- Efficient frontier generation
- Backtesting with transaction costs
- Covariance matrix calculation
- Risk attribution analysis

## Tech Stack

| Layer      | Stack                                                                              |
| ---------- | ---------------------------------------------------------------------------------- |
| Frontend   | React 19, TypeScript, Vite, TailwindCSS 4, React Router, TanStack Query, Plotly.js |
| Backend    | FastAPI, Python 3.12, NumPy, SciPy, Pandas, scikit-learn                           |
| AI         | Google Gemini (primary), OpenAI (fallback)                                         |
| Data       | yfinance, OpenBB SDK, FRED API                                                     |
| Database   | Supabase (PostgreSQL + Auth)                                                       |
| Deployment | Vercel (frontend), AWS EC2 (API)                                                   |

## Project Structure

```
packages/
  api/                  # Python FastAPI backend
    api/
      agent/            # AI agent (LLM integration, tools, classification)
      routes/           # API endpoints (agent, portfolio, backtest, etc.)
      auth.py           # JWT authentication
      main.py           # FastAPI app entry point
    quant/              # Quantitative analysis modules
    tests/              # Python tests
    environment.yml     # Conda dependencies
  web/                  # React/TypeScript frontend
    src/
      pages/            # Chat, Dashboard, Terminal, Saved
      components/       # UI components organized by feature
      hooks/            # Custom React hooks
      api/              # API client
      contexts/         # React contexts (Auth)
      lib/              # Utilities (portfolio math, formatting)
```

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.12 via [Conda](https://docs.conda.io/)
- API keys for: Google Gemini, FRED, OpenAI (optional fallback)
- A Supabase project (for auth and database)

### Backend Setup

```bash
# Create and activate conda environment
conda env create -f packages/api/environment.yml
conda activate tmt-markets
```

Create `packages/api/.env`:

```
GEMINI_API_KEY=your_gemini_key
FRED_API_KEY=your_fred_key
OPENAI_API_KEY=your_openai_key        # optional, used as fallback
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
SUPABASE_JWT_SECRET=your_jwt_secret
```

### Frontend Setup

```bash
npm install
```

Create `packages/web/.env`:

```
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
```

### Running Locally

```bash
# Start both frontend and backend
npm run dev

# Or run individually
npm run dev:api      # FastAPI on port 8000
npm run dev:web      # Vite dev server on port 5175 (proxies /api to 8000)
```

### Running Tests

```bash
# Frontend
cd packages/web && npm test

# Backend
cd packages/api && pytest
```

## Deployment

- **Frontend**: Deployed to Vercel. Configuration in `vercel.json`.
- **Backend**: Runs on an EC2 instance. API requests from Vercel are proxied via rewrites.

## MIT License

All rights reserved.
