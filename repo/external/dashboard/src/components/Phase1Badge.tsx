import React, { useEffect, useState } from "react";
import { fetchPhase1, Phase1Response } from "../api/phase1";

function shortHash(h?: string | null) {
    if (!h) return "";
    const s = h.replace("sha256:", "");
    return s.slice(0, 8);
}

export const Phase1Badge: React.FC = () => {
    const [data, setData] = useState<Phase1Response | null>(null);

    useEffect(() => {
        const tick = async () => {
            const d = await fetchPhase1();
            setData(d);
        };

        tick();
        const id = setInterval(tick, 5000);
        return () => clearInterval(id);
    }, []);

    if (!data) return null;

    const isOk = data.status === "OK";
    const bgColor = isOk ? "rgba(16, 185, 129, 0.1)" : "rgba(239, 68, 68, 0.1)";
    const borderColor = isOk ? "#10b981" : "#ef4444";
    const textColor = isOk ? "#34d399" : "#f87171";

    return (
        <div
            style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                padding: "4px 12px",
                borderRadius: "20px",
                border: `1px solid ${borderColor}`,
                backgroundColor: bgColor,
                color: textColor,
                fontSize: "12px",
                fontWeight: "bold",
                fontFamily: "Inter, sans-serif"
            }}
            title={isOk ? `Policy: ${data.policy_id} v${data.policy_version}` : `Blocked: ${data.reason}`}
        >
            <div
                style={{
                    width: "8px",
                    height: "8px",
                    borderRadius: "50%",
                    backgroundColor: borderColor
                }}
            />
            <span>{isOk ? "PHASE-1: OK" : "PHASE-1: BLOCKED"}</span>
            {isOk && <span style={{ opacity: 0.7, fontWeight: "normal" }}>{shortHash(data.policy_hash)}</span>}
        </div>
    );
};
