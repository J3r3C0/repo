import { useEffect, useState } from "react";
import { getOpsHealth, getSystemMetrics } from "../../api/system";
import { StatCard } from "../../components/common/StatCard";
import { StatusPill } from "../../components/common/StatusPill";
import { Gauge, HardDrive, Cpu, Activity } from "lucide-react";

export function OpsTab() {
    const [health, setHealth] = useState<any>(null);
    const [metrics, setMetrics] = useState<any>(null);

    useEffect(() => {
        const fetch = async () => {
            const [h, m] = await Promise.all([getOpsHealth(), getSystemMetrics()]);
            setHealth(h);
            setMetrics(m);
        };
        fetch();
        const interval = setInterval(fetch, 5000);
        return () => clearInterval(interval);
    }, []);

    const getHealthVariant = (status: string) => {
        if (status === 'OK' || status === 'OPERATIONAL') return 'success';
        if (status === 'DEGRADED') return 'warning';
        return 'danger';
    };

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold">Ops Overview (NOC)</h1>
                    <p className="text-slate-400">Total System Health & Performance</p>
                </div>
                <StatusPill
                    status={health?.status || 'UNKNOWN'}
                    variant={getHealthVariant(health?.status)}
                />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <StatCard
                    label="Uptime"
                    value={`${Math.floor((metrics?.uptime_sec || 0) / 3600)}h ${Math.floor(((metrics?.uptime_sec || 0) % 3600) / 60)}m`}
                    icon={Activity}
                />
                <StatCard
                    label="Queue Depth"
                    value={health?.queue?.depth || 0}
                    icon={Gauge}
                    variant={(health?.queue?.depth || 0) > (health?.queue?.max * 0.8) ? 'warning' : 'default'}
                />
                <StatCard
                    label="Inflight Jobs"
                    value={health?.queue?.inflight || 0}
                    icon={Cpu}
                    variant={(health?.queue?.inflight || 0) > (health?.queue?.max_inflight * 0.8) ? 'warning' : 'default'}
                />
                <StatCard
                    label="CPU Usage"
                    value={`${metrics?.process?.cpu_pct || 0}%`}
                    icon={HardDrive}
                />
            </div>

            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                <h3 className="text-lg font-medium mb-4 flex items-center gap-2">
                    <Activity className="w-5 h-5 text-sheratan-accent" />
                    Active Violations / SLOs
                </h3>
                {health?.violations?.length > 0 ? (
                    <div className="space-y-2">
                        {health.violations.map((v: string) => (
                            <div key={v} className="flex items-center gap-2 text-red-400 text-sm bg-red-500/5 p-3 rounded-lg border border-red-500/20">
                                <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                                <span className="font-mono">{v}</span>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="text-slate-500 text-sm italic py-4 bg-slate-900/30 rounded-lg text-center border border-dashed border-slate-800">
                        No active SLO violations detected. System is stable.
                    </div>
                )}
            </div>
        </div>
    );
}
