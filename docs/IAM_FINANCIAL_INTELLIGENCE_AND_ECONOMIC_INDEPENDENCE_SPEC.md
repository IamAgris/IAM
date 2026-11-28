# IAM — Financial Intelligence and Economic Independence Amendment

**Document:** 25 (addendum to Documents 01–24)  
**Version:** 1.2 · 26 November 2026  
**Status:** FROZEN — confirmed part of IAM architecture (owner confirmation 25 November 2026); expanded by owner direction 26 November 2026 (Amendment A: prediction markets, gaming/casino intelligence, investments and provider-independent ecosystem). No earlier decision is reopened or weakened.  
**Parent:** `canonical/IAM_DOC_01_MASTER_ARCHITECTURE.md` (via `IAM_FINAL_CONSOLIDATION.md`; the early master draft is superseded)  
**Related:** `IAM_BLOCKCHAIN_AND_BANKING.md` (Doc 09), `IAM_OWNER_DECISIONS.md` (OD-04, OD-23, OD-24, OD-25), `IAM_FINAL_CONSOLIDATION.md`, `IAM_COMMUNICATION_ARCHITECTURE.md` (Doc 07), `IAM_LEGAL_INTELLIGENCE_AND_COMPLIANCE_SPEC.md` (Doc 15)  
**Confirmed decisions:** OD-44 (financial intelligence and economic independence); OD-56 (Amendment A expansion — prediction markets, gaming intelligence and investments)  
**Amendment A:** Sections 11–24 (owner-directed expansion and implementation status; research and simulation only unless explicitly approved)

---

## 1. Scope

This amendment adds the supplied financial architecture **to IAM**. It extends the existing
financial rules in Doc 09 / OD-23 (thirdweb free-only blockchain), OD-24 (South African
banking integrations) and OD-25 (financial authority) without reopening or weakening them.

Nothing in this document enables real trading, real payments, borrowing, or autonomous
access to financial accounts during the first implementation. Simulated accounts and
records only.

---

## 2. Financial objectives (as supplied)

**Primary objective: income generation**

- Explore legitimate income opportunities.
- Investigate ways to fund IAM's operating costs.
- Research opportunities that may benefit its creator.
- Develop sustainable financial plans.

**Trading authority: human-approved trading**

- IAM researches and proposes trades. Real trading is permitted only through explicit
  approval and defined limits.

**Payment capabilities: receive and make payments**

- IAM can eventually manage authorised payment workflows, with separate approval controls
  for incoming and outgoing transactions.

---

## 3. New financial modules (as supplied)

| Module | Responsibility |
|--------|----------------|
| A. Income intelligence | Finds and evaluates legitimate income opportunities, business models, services and potential revenue sources |
| B. Cryptocurrency intelligence | Studies markets, strategies, technical indicators, blockchain networks, exchanges and trading risks |
| C. Trading operations | Paper trading first, then human-approved real trading with spending limits, loss limits and transaction records |
| D. Payment management | Investigates authorised bank transfers, payment processors, cryptocurrency wallets, receiving payments and paying approved expenses |
| E. Financial governance | Maintains budgets, transaction approvals, records, profit-and-loss reports and financial risk controls |

---

## 4. Operating flow (as supplied)

```
             IAM INTELLIGENCE
                    |
          Financial Research
                    |
           Income Opportunities
                    |
           Risk Assessment
                    |
            Financial Plan
                    |
             Human Approval
                    |
        +-----------+-----------+
        |                       |
   Trading System         Payment System
        |                       |
   Approved trades       Approved payments
        |                       |
        +-----------+-----------+
                    |
             Audit Records
                    |
           Financial Reports
```

Important distinction: receiving a payment and spending that money are separate
permissions. IAM must not automatically gain authority over incoming funds.

---

## 5. Trading permission levels (as supplied)

| Capability | IAM authority |
|------------|---------------|
| Study markets | Independent |
| Analyse opportunities | Independent |
| Develop strategies | Independent |
| Simulate trades | Independent |
| Recommend trades | Independent |
| Execute real trades | **Explicit human approval** |
| Increase trading budget | **Explicit human approval** |
| Withdraw funds | **Explicit human approval** |

Real trading must also have a maximum order amount, maximum daily exposure, maximum loss
limit, exchange restrictions and an emergency stop.

---

## 6. Payment architecture (as supplied)

Eventually support: receiving authorised payments; tracking incoming revenue; checking
transaction fees; preparing approved outgoing payments; paying approved operating expenses;
tracking cryptocurrency and conventional currency balances; producing financial statements.

For the first implementation, use simulated accounts and payment records. Real bank and
exchange integrations come later, after security, legal and regulatory review.

---

## 7. Project structure (as supplied)

```
app/
├── finance/
│   ├── income_intelligence/{opportunities, business_research, income_planning}.py
│   ├── crypto/{education, market_research, technical_analysis, strategy_engine, paper_trading}.py
│   ├── trading/{trade_proposals, execution, risk_management, exchange_adapter}.py
│   ├── payments/{incoming, outgoing, wallet_manager, payment_adapter}.py
│   └── governance/{financial_permissions, budget_manager, transaction_approval, accounting, financial_audit}.py
```

**IAM mapping:** existing `backend/app/api/routes/economy.py`, `models/business*.py`,
`digitalassets.py`, `services/` budget and ledger code, and `CreatorApprovalService` already
implement the governance core. These folders are added as modules inside that architecture,
not as a second finance system.

---

## 8. Financial development stages (as supplied)

1. **Stage 1** — Financial education and research.
2. **Stage 2** — Market analysis and simulated trading.
3. **Stage 3** — Trade proposals with documented risk assessments.
4. **Stage 4** — Human-approved real trading through restricted integrations.
5. **Stage 5** — Authorised payment processing and operating-cost management.

### 8.1 Financial permission requirements (as supplied)

- Market research requires no financial transaction authority.
- Paper trading must use virtual funds.
- Every real trade requires explicit approval.
- Every outgoing payment requires explicit approval.
- Incoming payment access must be separately authorised.
- Trading budgets and payment budgets must be separate.
- IAM cannot increase its own financial permissions.
- IAM cannot borrow money, evade financial restrictions or secretly transfer funds.
- All transactions must be recorded and auditable.
- An emergency stop must disable financial execution.

### 8.2 Financial risk management (as supplied)

Before proposing a real trade, IAM must disclose: asset and exchange; proposed direction
and order type; amount and currency; fees and estimated slippage; potential loss; strategy
rationale; relevant market uncertainty; proposed stop-loss where appropriate.

Never promise profits or assume that previous performance guarantees future results.

### 8.3 Payment requirements (as supplied)

Design adapters for authorised payment processors, conventional bank payments and
cryptocurrency wallets. Do not store private keys or exchange passwords in ordinary
application memory or source code — use secure credential management and restricted
transaction permissions. Build a simulation environment first; do not connect real
financial accounts during the first implementation.

### 8.4 Financial reporting (as supplied)

Track income, operating expenses, trading gains and losses, transaction fees, available
balances, outstanding approvals and financial risk exposure. Produce periodic financial
reports through the authorised Creator communication channel (Doc 07, OD-42).

---

## 9. Ownership (as supplied)

If IAM generates income, who owns that income? Recommended starting arrangement:

> All income belongs to the owner or another legally designated account holder. IAM can
> propose an operating budget, but it cannot claim ownership of funds or independently
> acquire financial authority.

This gives a route toward economic sustainability without confusing financial capability
with legal ownership or unrestricted independence. **IAM equivalent:** OD-02 (legal entity),
OD-04/OD-25 (zero standing budget, signed approval) and Master §4 (IAM is not a legal person).

---

## 10. Boundaries and acceptance criteria

1. First implementation is simulated only — no real trades, payments or account access.
2. OD-04 zero standing budget and OD-25 financial authority remain unchanged.
3. Receiving and spending are separate permissions; incoming funds never become autonomous budget.
4. Real trades and outgoing payments require explicit signed Creator approval.
5. Trading and payment budgets are separate; IAM cannot raise either itself.
6. No borrowing, fund concealment, transfer evasion or guaranteed-profit claims.
7. Emergency stop disables financial execution and is tested.
8. Credentials/private keys use secure storage, never source code or ordinary memory.
9. Every transaction and proposal is recorded and auditable.
10. Legal ownership of income remains with the designated owner/entity.
11. Modules extend existing economy/finance code — no second finance system.

---

# Amendment A — Prediction markets, gaming intelligence and expanded financial ecosystem

*Owner-directed expansion, 26 November 2026. Sections 1–10 remain in force. Sections 11–23
add scope only; they do not grant trading, payment or gambling authority.*

## 11. Three distinct operations

The expanded system must keep three operation types separate. Prediction markets and
digital casinos are **not** financial markets and must not be treated as extensions of the
Forex/crypto trading engine.

| Operation | Examples | Nature |
|-----------|----------|--------|
| Financial trading | Forex, cryptocurrency, stocks, ETFs, commodities, futures, bonds, indices | Financial markets |
| Prediction markets | Polymarket, Kalshi, PredictIt, Manifold, Metaculus | Event-based outcome contracts |
| Digital casinos | Blackjack, roulette, slots, poker and other casino games | Games of chance with a mathematical house edge |

Prediction-market contracts generally trade between $0 and $1, where price represents the
market's implied probability, subject to liquidity, fees and settlement conditions. Casino
games are independent random events whose published return-to-player (RTP) is a long-run
statistical measure, not a promised return on any single session.

## 12. Prediction Market Intelligence — responsibilities

| Capability | IAM's responsibility |
|------------|----------------------|
| Market discovery | Find relevant prediction markets and event contracts |
| Probability analysis | Estimate the probability of each outcome independently |
| Research | Analyse news, events and historical evidence |
| Market comparison | Compare market prices with IAM's own estimates |
| Liquidity analysis | Evaluate order books and trading costs |
| Risk analysis | Evaluate exposure and potential losses |
| Strategy research | Backtest prediction-market strategies (simulation first) |
| Portfolio monitoring | Track open contracts and settlement |

Worked example: a market prices an event at $0.40 (≈40% implied probability) while IAM's
independent estimate is 55%, giving a 15-percentage-point discrepancy. This is **not**
automatically a profitable opportunity: fees, liquidity, spreads, settlement conditions and
uncertainty in IAM's own estimate must all be accounted for. IAM must document its
independent probability estimate and the evidence behind it rather than assuming the market
price is wrong.

IAM should build its own forecasting capability instead of relying entirely on
market-implied probabilities.

## 13. Polymarket technical integration

| Interface | Purpose |
|-----------|---------|
| Gamma API | Discover markets, events and outcomes |
| CLOB API | Access order books, prices and liquidity |
| WebSocket | Receive live market updates |
| Data API | Research activity, positions and market statistics |
| Wallet integration | Account and transaction infrastructure, where permitted |

Required architecture:

```
IAM PREDICTION INTELLIGENCE
   Research · probabilities · event analysis
                |
   POLYMARKET DATA ADAPTER
   Gamma · CLOB · Data API · WebSocket
                |
   Research → Market analysis → Evaluation (probability and risk)
                |
   PREDICTION MARKET GOVERNANCE
   Legal eligibility · permissions · capital controls
                |
   EXECUTION ADAPTER — DISABLED until legally and operationally authorised
```

- IAM may research Polymarket markets and collect **public** market data independently;
  access to trading functionality is not a prerequisite for research.
- Public market-data interfaces and trading interfaces have different authentication and
  access requirements. Trading, deposits and wallet funding stay disabled.
- **South African restriction:** Polymarket's availability and legal status for a person or
  entity operating from South Africa must be assessed separately. A technically accessible
  API does not establish that participation is lawful. No deposits, wallet funding or
  contract trading until specialist South African legal advice confirms the position.
- Other prediction platforms for research: Kalshi (event-based financial contracts),
  PredictIt (political markets), Manifold Markets (community markets), Metaculus
  (forecasting research), Polymarket (crypto-based). Each has different legal structures,
  access restrictions and real-money support; record these in the provider registry (§18).

**IAM mapping:** research adapters are read-only modules inside `finance/` (§7), governed by
`CreatorApprovalService` and the existing legal/compliance system (Doc 15). This does not
create a new autonomous trading system.

## 14. Gaming and Casino Intelligence

Legitimate research and software-engineering study areas only:

| Area | What IAM may study |
|------|--------------------|
| Probability mathematics | Probability distributions and expected value |
| Statistical analysis | Variance, sample size and randomness |
| Game theory | Decision-making under uncertainty |
| RNG analysis | Statistical testing of random-number generators |
| RTP analysis | Return-to-player mathematics |
| House edge | The casino's mathematical advantage |
| Fraud detection | Suspicious transaction and gameplay patterns |
| Responsible gambling | Spending limits and harm-prevention systems |

Illustrative mathematics only (hypothetical, not a guaranteed session outcome): on a game
with 96% RTP, R100 wagered over a sufficiently large number of plays has a theoretical
return of R96 and R4 expected loss. An AI model cannot reliably predict independent outcomes
from a properly implemented RNG by analysing previous results; RTP is a long-run measure.

Casino technology stack for industry research — not a licence to operate or wager:

Casino game providers · game aggregation platforms · remote gaming servers (RGS) · player
account management (PAM) · random-number generators · game mathematics and RTP · casino
wallet infrastructure · payment processing · KYC/AML systems · fraud detection · responsible
gambling systems · gaming licences and compliance.

Separate legitimate business-income research: the **economics of the digital casino
industry** — gaming providers, operators, payment infrastructure, licensing, software
development and legitimate technology partnerships. IAM can understand the industry without
gambling to learn about it; this belongs to Income Intelligence, not to wagering.

## 15. South African legal boundaries

IAM's intended operation is based in South Africa. The National Gambling Board's current
guidance distinguishes:

| Activity | South African position |
|----------|------------------------|
| Licensed land-based casinos | Legal |
| Online betting through licensed bookmakers | Legal, subject to applicable licences |
| Online interactive casino games | NGB says prohibited |
| International online casino gambling from South Africa | NGB says South Africans cannot gamble with international companies from within the Republic |
| Prediction markets such as Polymarket | Requires separate legal assessment |

Proposed online-gambling policy developments are not operating licences. Therefore:

- No automated casino wagering and no overseas casino account funding capabilities.
- No real-money prediction-market participation without specialist legal clearance and
  explicit authorisation.
- Regulatory status must be rechecked through Doc 15 before any integration moves beyond
  research. **IAM equivalent:** OD-04/OD-25 (approval and financial authority), §5, §8.1.

## 16. Expanded eight-department architecture

The five-module list in §3 is the original frozen baseline. The expanded, consolidated
financial intelligence system comprises eight interconnected departments:

| # | Department | Responsibility |
|---|------------|----------------|
| 01 | Income Intelligence | Discover and evaluate legitimate income opportunities |
| 02 | Forex Intelligence & Trading | Forex research, strategies and authorised execution |
| 03 | Cryptocurrency Intelligence & Trading | Crypto research, blockchain analysis and authorised execution |
| 04 | Prediction Market Intelligence | Event forecasting, probability research and eligible market participation |
| 05 | Gaming & Casino Intelligence | Gaming mathematics, industry research and casino technology analysis |
| 06 | Investment & Portfolio Intelligence | Stocks, ETFs, commodities, bonds and portfolio research |
| 07 | Payment & Financial Operations | Payments, financial accounts, transactions and reconciliation |
| 08 | Financial Governance & Risk | Capital protection, compliance, permissions and auditing |

Departments 04–06 are new; 01–03 and 07–08 extend the §3 modules. All departments inherit
§1 (simulated first), §5 (explicit approval for real execution), §8.1–8.4 and §9–10.

## 17. Proposed software structure

```
financial-intelligence/
├── forex-trading/
├── crypto-trading/
├── prediction-markets/
│   ├── market-discovery/
│   ├── probability-engine/
│   ├── event-intelligence/
│   ├── market-analysis/
│   ├── historical-analysis/
│   └── legal-eligibility/
├── gaming-intelligence/
│   ├── probability-engine/
│   ├── statistical-analysis/
│   ├── rng-research/
│   ├── rtp-analysis/
│   ├── game-theory/
│   └── responsible-gambling/
├── investment-intelligence/
│   ├── equities/
│   ├── etfs/
│   ├── commodities/
│   ├── bonds/
│   └── portfolio-optimisation/
├── income-intelligence/
├── payment-management/
└── financial-governance/
```

This is a logical capability layout, not a second finance system. Implementation must place
these modules inside the existing `app/finance/` structure and API/ledger/approval code
referenced in §7; no parallel finance stack is permitted.

## 18. Provider-independent ecosystem

Do not restrict IAM to the platforms listed here. Build a provider-independent architecture
that can discover, evaluate and integrate additional legitimate financial services as they
become useful. All providers below are **research candidates, not endorsements**.

| Category | Providers to investigate |
|----------|--------------------------|
| Forex | OANDA, Interactive Brokers, MetaTrader brokers |
| Cryptocurrency | Kraken, Coinbase, Binance |
| Stocks / ETFs | Interactive Brokers, Alpaca |
| Commodities / futures / bonds / metals / indices | Interactive Brokers, authorised commodity brokers, CME-connected brokers, institutional data providers |
| Prediction markets | Polymarket, Kalshi, PredictIt, Manifold Markets, Metaculus |
| Gaming / iGaming infrastructure | Evolution, Pragmatic Play, Play'n GO, Light & Wonder, EveryMatrix, SOFTSWISS, Gaming Innovation Group |
| Financial news | Bloomberg, Reuters |
| Economic data | FRED, Trading Economics |
| Market data | LSEG, Polygon.io |
| Cryptocurrency data | CoinGecko, CoinMarketCap |
| Blockchain intelligence | Glassnode, CryptoQuant |
| On-chain analytics | Dune, DefiLlama |
| Derivatives intelligence | Coinglass |
| Market research | Financial Modeling Prep |
| Technical analysis | TradingView |

Before any adapter is enabled, the provider registry must record: API and authentication
requirements; free versus paid access; whether commercial and automated usage is permitted;
whether South African accounts are supported; demo/sandbox availability; licence or
institutional-account requirements; data schemas and event contracts.

## 19. Additional intelligence capabilities

IAM should develop, at research/simulation level:

- Quantitative finance and mathematical modelling.
- Statistical arbitrage research and algorithmic strategy discovery.
- Portfolio optimisation and risk-adjusted capital allocation.
- Market regime detection and economic forecasting.
- Cryptocurrency tokenomics research and blockchain/on-chain intelligence.
- Liquidity and order-book analysis and cross-market correlation analysis.
- Financial sentiment analysis.
- Automated financial reconciliation.
- Fraud and market-manipulation detection.
- Strategy performance evaluation.

These capabilities remain advisory until a specific action passes §5 approval and §16/§15
governance checks.

## 20. Financial infrastructure

Operational systems required for the expanded ecosystem:

Multi-broker and multi-exchange account management · API credential management · secure
wallet infrastructure · financial transaction ledger · currency conversion · tax and
accounting records · deposit and withdrawal governance · capital allocation · payment-provider
integrations · financial reporting · regulatory and jurisdictional eligibility checks ·
disaster recovery and backup systems.

Credentials and private keys remain subject to §8.3: secure credential storage only, never
source code or ordinary application memory.

## 21. Autonomy levels

| System | Research autonomy | Real-money execution |
|--------|-------------------|----------------------|
| Forex | Full | Within authorised limits, explicit approval per §5 |
| Crypto | Full | Within authorised limits, explicit approval per §5 |
| Polymarket | Full market research (public data) | Only after legal clearance and explicit authorisation |
| Digital casinos | Mathematical and statistical research | **No autonomous gambling** |

"Within authorised limits" always remains subject to §1 (simulated first), OD-04 zero
standing budget, §5 signed approval and §10 acceptance criteria. Research autonomy never
implies transaction authority.

## 22. Additional acceptance criteria

1. Prediction-market research works without any trading capability enabled.
2. All execution adapters are disabled by default and require explicit authorisation.
3. No automated casino wagering and no overseas casino account funding exists in any build.
4. Independent probability estimates and their evidence are recorded for every comparison.
5. South African legal clearance is recorded before any real-money prediction-market activity.
6. Every external provider has a registry entry covering §18 gates before adapter integration.
7. Departments 04–06 extend existing economy/finance modules; no second finance system.
8. New research capabilities produce recorded, auditable outputs only — no autonomous action.
9. Provider-independent design permits adding new providers without architecture changes.

## 23. Items still required before the ecosystem can be called complete

- Every provider's API and integration requirements.
- Which providers have free and paid access.
- Which providers permit commercial and automated usage.
- Which providers support South African accounts.
- Which providers offer demo or sandbox environments.
- Which services require licences or institutional accounts.
- Exact database schemas and event contracts.
- AI agent permissions and responsibilities.
- Trading execution and financial governance policies.
- Deployment, monitoring and disaster recovery.
- Testing and acceptance requirements.

**Guiding principle:** IAM becomes an independent financial intelligence system through
provider-independent research and forecasting capability — not an AI bot connected to a
handful of trading or gambling websites. Financial capability is never confused with
sustainable income generation, legal ownership (§9), or permission to gamble.

---

## 24. Implementation status (informational, 26 November 2026)

This section records what has been implemented; it does not change any decision or
permission above.

| §23 item | Status | Implementation |
|----------|--------|----------------|
| Schemas and event contracts | Done | `backend/app/models/financial_intelligence.py`; migrations `030_financial_intelligence.sql` and `0002_financial_intelligence.py` |
| Provider registry | Done | 37 §18 candidates seeded idempotently via `POST /api/v1/provider-registry/seed` or `scripts/seed_provider_registry.py`; all gates unreviewed, all adapters disabled |
| Polymarket public data | Done (read-only) | `services/prediction_markets/adapter.py`; Gamma/CLOB/Data API GET-only endpoints behind default-off flags; no trading or wallet calls |
| Independent forecasting | Done | `services/prediction_markets/forecasting.py`; evidence-weighted and base-rate methods, documented formula, recorded evidence and rationale, market prices read only for comparison |
| Gaming and investment research | Done | `services/gaming_intelligence/` and `services/investment_intelligence/`; research-only services with wagering/order methods that always deny |
| Agent permissions | In progress | All new API prefixes require `admin` scope; every feature flag is default-off |
| Deployment, monitoring, disaster recovery | Existing platform applies | No separate finance deployment introduced |
| Testing and acceptance | Done | Service tests plus HTTP acceptance tests (`tests/test_financial_intelligence*.py`); generated schema refreshed at `IAM_OPENAPI.json` |

**Still required before real-money work (unchanged):** provider API/auth verification, free
versus paid terms, commercial and automated usage permission, South African account support,
sandbox availability, licence requirements, specialist South African legal advice, signed
Creator execution policy, and deployment acceptance criteria. None of these are granted by
this implementation status.
