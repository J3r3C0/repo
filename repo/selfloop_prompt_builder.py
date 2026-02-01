from typing import Dict, Any


def build_selfloop_prompt(
    goal: str,
    core_data: str,
    current_task: str,
    loop_state: Dict[str, Any],
) -> Dict[str, str]:
    """Erzeuge System- und User-Prompt für einen Sheratan-SelfLoop.

    Rückgabe ist ein Dict mit:
    - system: Rollenbeschreibung / Meta
    - user: konkreter Prompt mit Kontext & Aufgabenbeschreibung

    Das Format ist so gewählt, dass es direkt an einen Relay- oder LLM-Client
    weitergereicht werden kann.
    """

    iteration = loop_state.get("iteration", 1)
    history_summary = loop_state.get("history_summary", "") or ""
    open_questions = loop_state.get("open_questions", []) or []
    constraints = loop_state.get("constraints", []) or []

    open_questions_block = "- " + "\n- ".join(open_questions) if open_questions else "(keine)"
    constraints_block = "- " + "\n- ".join(constraints) if constraints else "(keine)"

    system_prompt = (
        "Du bist ein kooperativer Co-Strategist in einem fortlaufenden Self-Loop-System. "
        "Deine Aufgabe ist es, ein gegebenes Hauptziel schrittweise voranzubringen. "
        "Du agierst nicht als Befehlsempfänger, sondern als Partner, der sinnvolle, "
        "klar begründete Fortschritte vorschlägt und ausführt. "
        "Du arbeitest strukturiert, knapp und zielorientiert."
    )

    user_prompt = f"""### Self-Loop Kontext (Iteration {iteration})

Hauptziel:
{goal}

Aktueller Zustand / Kontext:
{core_data}

Aktueller Fokus in dieser Iteration:
{current_task}

Bisherige Entwicklung (Kurzfassung):
{history_summary or "(noch keine History hinterlegt)"}

Einschränkungen / Constraints:
{constraints_block}

Offene Fragen aus vorherigen Loops:
{open_questions_block}

---

### Deine Rolle in diesem Loop

Du arbeitest in einer wiederkehrenden Schleife. In jeder Iteration sollst du genau
einen sinnvollen Fortschrittsschritt auswählen und ausführen, der das Hauptziel
weiterbringt. Du darfst den Fokus interpretieren, aber nicht komplett ignorieren.

### Aufgaben pro Loop

1. Standortanalyse: Ordne kurz ein, wo wir stehen.
2. Nächster sinnvoller Schritt: Wähle begründet, was jetzt am meisten bringt.
3. Umsetzung: Führe diesen Schritt konkret aus (Text, Struktur, Ideen, Plan etc.).
4. Vorschlag für nächsten Loop: Empfiehl, was als nächstes logisch folgen sollte.

Wiederhole nicht einfach frühere Schritte, außer wenn es eine klare Verfeinerung ist.

### Antwortformat (STRICT EINHALTEN)

Antworte **immer** exakt in diesem Schema:

A) Standortanalyse
- ...

B) Nächster sinnvoller Schritt
- ...

C) Umsetzung
- ...

D) Vorschlag für nächsten Loop
- ...
"""

    return {
        "system": system_prompt.strip(),
        "user": user_prompt.strip(),
    }
