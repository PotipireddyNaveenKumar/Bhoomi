# BHOOMI V2 — Safety Engine Specification

## 1. Principles
Agricultural AI systems must never provide unvetted, hazardous chemical recommendations or toxic dosages to farmers.
BHOOMI implements a multi-layer `SafetyEngine` that intercepts and evaluates candidate advice before presenting it to the user.

```mermaid
graph TD
    AgentOutput[Agent / RAG / Vision Candidate] --> SafetyEngine[SafetyEngine Interceptor]
    SafetyEngine --> BannedCheck{Banned / Restricted Chemicals?}
    BannedCheck -- Yes --> Block[STATUS: BLOCK -> Return Safe IPM Alternative]
    BannedCheck -- No --> DosageCheck{Check Stage & Pollinator Risk}
    DosageCheck -- Warnings Needed --> Modify[STATUS: MODIFY -> Append PPE & Timing Alerts]
    DosageCheck -- Clean --> Pass[STATUS: PASS -> Present Direct Advice]
```

## 2. Guardrails
1. **Banned / Restricted Substance Blocker**: Intercepts CIBRC-banned chemicals (Monocrotophos, Endosulfan, Paraquat, Phorate, etc.) and substitutes eco-friendly Integrated Pest Management (IPM) protocols.
2. **Pollinator Protection**: Checks whether the crop is in `flowering` or `pollination` stage and blocks or flags broad-spectrum morning sprays to protect honeybees and pollinators.
3. **PPE Mandatory Advisories**: Enforces protective gear reminders whenever chemical sprays are involved.
