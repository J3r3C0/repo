# Sheratan Capability Map (Strategische Exploitation)

Dieses Dokument definiert die einzigartigen Stärken (USPs) von Sheratan und identifiziert das Produktpotential basierend auf dem aktuellen Baseline-Release.

## 1. Die "Unersetzliche" Qualität
Sheratan ist im Kern eine **deterministische Wahrnehmungs-Engine**. 

*   **Der USP**: Während andere Systeme direkt auf LLM-Inference setzen (und damit Halluzinationen in Kauf nehmen), segmentiert Sheratan rohe Ereignisströme mathematisch.
*   **Der Wert**: Salienz wird *vor* der agentialen Verarbeitung erkannt. Dies erlaubt eine massive Reduktion der Token-Kosten und eine drastische Erhöhung der Zuverlässigkeit.

## 2. Produktfähige Komponenten (Tier 1 Integration)
Diese zwei Bereiche sind heute bereits technisch stabil und marktfähig:

### A. Sheratan Perception Proxy
Ein vorgeschalteter Ingest-Layer für Agenten-Plattformen.
- **Funktion**: Filtert Rauschen aus Webhook- oder Log-Streams, bevor diese an ein teures LLM gehen.
- **Vorteil**: 80-90% Rauschreduktion bei gleichbleibendem Signalgehalt.

### B. LCP Mission Orchestrator (v2)
Ein dezentraler Scheduler für kognitive Jobs.
- **Funktion**: Standardisierte Job-Envelopes (LCP), die zwischen spezialisierten Worker-Instanzen ausgetauscht werden.
- **Vorteil**: Keine Vendor-Lock-ins; Agenten können nahtlos zwischen Providern (OpenAI, Anthropic, Local Lama) wechseln.

## 3. Strategischer Vorteil durch "Non-Scope"
Sheratan gewinnt durch das, was es **nicht** tut:
- **Keine eigenen LLMs**: Sheratan muss keinen Hardware-Krieg gegen Hyperscaler führen. Es bleibt der neutrale Beobachter und Koordinator.
- **Keine monolithische App**: Die Trennung von Core und Hub erlaubt es, Sheratan in bestehende Enterprise-Architekturen zu integrieren (z.B. Core am Edge, Hub in der Cloud).

## 4. Capability Matrix

| Fähigkeit | Status | Einsatzgebiet |
| :--- | :--- | :--- |
| **Deterministische Salienz** | Stable | Monitoring, Rauschunterdrückung. |
| **LCP Job-Protocol** | Ready | Dezentrale Worker-Orchestrierung. |
| **Multi-Provider Routing** | Ready | Kosten- und Ausfalleffizienz. |
| **MCTS Planning** | Explorative | Autonome Problemlösung. |

---
*Dieser Entwurf dient der strategischen Ausrichtung (Modus B).*
