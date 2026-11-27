# IAM — Blockchain & South African Banking Architecture

**Document:** 09 (addendum to Documents 01–08)  
**Version:** 1.0 · 25 November 2026  
**Status:** FROZEN — blockchain & banking scope  
**Decisions:** OD-23 (thirdweb free-only), OD-24 (ZA banking), OD-25 (financial authority)

---

## 1. Principle

IAM connects traditional banking and blockchain through **its own financial management system**. thirdweb provides blockchain infrastructure; bank APIs provide traditional banking. Neither makes IAM a bank, regulated financial institution, or unrestricted trading system. Both are **replaceable adapters** — IAM retains its own ledger, wallet records, transaction history and business logic.

---

## 2. Financial authority levels (OD-25)

| Level | Authority |
|---|---|
| **Research & simulation** | Autonomous — analyse markets, assets, risk, opportunities |
| **Bounded financial activity** | Transact only within creator-approved budgets, strategies, limits |
| **Protected operations** | Creator approval required — withdrawals, large transfers, new strategies, permission changes |

Permanent rule: IAM can never increase its own treasury permissions, bypass spending limits, or transfer protected funds to itself. Zero standing budget (OD-04) applies.

---

## 3. Blockchain integration framework

thirdweb is **one adapter** inside a larger framework:

```
IAM Blockchain Intelligence (research · development · finance · trading)
        ↓
IAM Blockchain Integration Framework
  (network registry · wallet policies · transaction routing · risk controls)
        ↓
  ├─ thirdweb (free-only: wallets, contracts, transactions)
  ├─ DEX integrations (authorised)
  ├─ Exchange integrations (authorised CEX APIs)
  ├─ Blockchain RPCs
  ├─ Indexing services
  └─ Oracle providers
```

### 3.1 thirdweb free-only policy (OD-23)
**Allowed (free tier):** SDKs, smart contract tools, developer dashboard, API keys (within quotas), RPC reads (free limits), IPFS storage (free allowance), Wallet SDKs, open-source self-hosted Engine, testnet infrastructure.

**Forbidden (paid):** Growth/Scale/Pro subscriptions, paid Engine/Transactions upgrades, paid RPC capacity, paid storage/bandwidth, paid wallet usage, paid gas sponsorship, paid transaction services, add-ons, automatic upgrades/overage.

**Adapter checks before any call:** is it free? included in free plan? remaining allowance? rate limits? requires billing info? mainnet charges? terms permit use? On exhaustion → pause, never silently switch to paid, research alternatives.

**Blockchain gas ≠ thirdweb fee:** testnets during development; mainnet requires separately authorised funds.

### 3.2 Wallet domains (separate, never mixed)
Treasury · Trading · Projects · Development (testnet) · Customer wallets (fully separate). Each with separate permissions, budgets, keys, policies. Use thirdweb Vault / secured KMS. Never expose keys to IAM's model, browser or dev workspace.

### 3.3 Ten blockchain modules (under existing economic/development/security systems)
1. Thirdweb Integration Engine
2. Blockchain Network Engine
3. Wallet and Treasury Management Engine
4. Smart Contract Development Engine
5. Blockchain Transaction Engine
6. Crypto Trading Intelligence Engine
7. DeFi Integration Engine
8. Blockchain Security and Risk Engine
9. On-chain Accounting & Reconciliation Engine
10. Financial Authority & Approval Engine

### 3.4 Expanded blockchain requirements (19-checklist)
Development (contracts/tokens, NFTs/DAOs/DeFi, auditing, infrastructure) · Operations (thirdweb, multi-chain, wallets, cross-chain/bridges, simulation/verification) · Financial intelligence (market research, DEX/exchange, staking/lending/liquidity, portfolio/treasury, risk/tax/accounting) · Security (multisig/approval, contract/token risk, limits, freeze, audit trail).

Study thirdweb alongside Solidity, Foundry, Hardhat, OpenZeppelin, chain-specific tools. Limitations: EVM-focused; DeFi ≠ CEX; gas/counterparty/contract risks remain; comply with law, KYC/AML, tax.

---

## 4. South African banking architecture

### 4.1 Access reality
No universal ZA open-banking API. Use official bank APIs or authorised intermediaries; explicit consent; OAuth/mTLS; never collect banking passwords; POPIA compliance. Standard Bank (sandbox by invitation, subscriptions) and Nedbank (marketplace, consent infra) are starting points; Absa/FNB partner routes; Capitec/Investec/Discovery/TymeBank evaluate individually. Intermediaries (Banklink — usage-based/not free; Ozow, PayFast, Peach Payments, Yoco) are complementary, not substitutes.

### 4.2 Eighteen frozen capabilities
1. Multi-Bank Integration Framework
2. Open Banking & Consent Engine
3. Account & Balance Management
4. Payment Initiation & Collection
5. EFT, PayShap & Instant Payment Integration
6. Bank Statement & Transaction Engine
7. Beneficiary Verification Engine
8. Multi-Currency & Foreign Exchange Engine
9. Merchant & Payment Gateway Integration
10. Business Banking & Treasury Engine
11. Payroll & Supplier Payment Management
12. Accounting, Tax & Reconciliation Engine
13. Banking Fraud & Risk Detection
14. Financial Compliance & Audit Engine
15. Bank Provider Discovery & Replacement Engine
16. Payment-System Interoperability Engine (PayShap, RTC, EFT, ISO 20022, debit orders)
17. Banking Resilience & Recovery Engine
18. Financial Authority & Permission Engine

### 4.3 Payment-system & open-finance interoperability
Integrate direct APIs, authorised aggregators, PISPs, account verification, merchant gateways, international providers. Explicit consent + OAuth + secure tokens. Adapt to SARB Payments Ecosystem Modernisation and future standards.

### 4.4 Banking resilience
Multiple accounts/institutions; detect API outages; safe retries (never duplicate payments — a timeout is not proof of failure; verify status first); independent accounting records; reconcile balances; export/migrate records; auditable instruction log; detect unauthorised beneficiary changes; emergency suspend outgoing payments.

### 4.5 Account separation
Creator personal · IAM business · project/company · customer-connected · third-party funds — never mixed. Regulatory obligations (payments, advice, holding funds, crypto exchange) determined before offering services. Legal ownership via person/entity.

### 4.6 Permanent banking rule
Seek free, officially-supported APIs first; verify costs/access; never bypass restrictions; never incur charges or initiate unauthorised transactions without approval.

---

## 5. Unified financial layer

```
IAM Financial Intelligence (budgets · decisions · accounting · approvals)
        ↓
IAM Financial Integration Layer (unified processing & reconciliation)
   ├─ Traditional banking (ZA banks + intermediaries)
   ├─ Blockchain (thirdweb + DEX/CEX/RPC)
        ↓
IAM Financial Ledger (double-entry; unified fiat + digital asset records)
```

Flow example: receive ZA bank revenue → record in ledger → calculate budget → research approved investment → convert via legal route → transfer to authorised wallet → verify on-chain → reconcile bank withdrawal against wallet deposit. Each leg is a separate transaction with compliance checks.

---

## 6. Acceptance criteria
1. thirdweb adapter uses free tier only; paid feature → paused.
2. Wallet domains separated; keys never exposed to model/browser.
3. Transactions simulated and risk-checked before signing.
4. All financial operations reconciled to double-entry ledger.
5. Zero standing budget enforced for fiat and crypto.
6. Bank provider failures handled without duplicate payments.
7. Customer/third-party funds isolated from IAM funds.
8. Emergency freeze works across banking and blockchain.
9. Provider replacement without loss of financial identity.
10. Legal/regulatory requirements verified before production money movement.
