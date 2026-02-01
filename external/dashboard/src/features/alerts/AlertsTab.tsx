import { useEffect, useState } from "react";
import { getSystemAlerts } from "../../api/system";
import { StatusPill } from "../../components/common/StatusPill";
import { Bell, Filter, Search } from "lucide-react";

export function AlertsTab() {
    const [alerts, setAlerts] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetch = async () => {
            const data = await getSystemAlerts(100);
            setAlerts(data);
            setLoading(false);
        };
        fetch();
        const interval = setInterval(fetch, 10000);
        return () => clearInterval(interval);
    }, []);

    const getSeverityVariant = (event: string) => {
        if (event.includes("CRITICAL") || event.includes("FAILURE")) return "danger";
        if (event.includes("WARNING") || event.includes("BURST")) return "warning";
        return "info";
    };

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold flex items-center gap-3">
                        <Bell className="w-6 h-6 text-amber-500" />
                        Alerts Center
                    </h1>
                    <p className="text-slate-400">System Alarms and SLO Violations</p>
                </div>
                <div className="flex gap-2">
                    <button className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 rounded-lg text-sm transition">
                        <Filter className="w-4 h-4" /> Filter
                    </button>
                </div>
            </div>

            <div className="bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden">
                <div className="p-4 border-b border-slate-800 bg-slate-800/30 flex justify-between items-center">
                    <span className="text-sm font-medium text-slate-300">{alerts.length} Recent Events</span>
                    <div className="relative">
                        <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                        <input
                            type="text"
                            placeholder="Search events..."
                            className="bg-black/40 border border-slate-700 rounded-md pl-9 pr-3 py-1.5 text-xs focus:outline-none focus:border-sheratan-accent transition"
                        />
                    </div>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                        <thead className="text-xs uppercase text-slate-500 bg-black/20 font-medium">
                            <tr>
                                <th className="px-6 py-3">Timestamp</th>
                                <th className="px-6 py-3">Event</th>
                                <th className="px-6 py-3">Severity</th>
                                <th className="px-6 py-3">Details</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/50">
                            {alerts.length === 0 ? (
                                <tr>
                                    <td colSpan={4} className="px-6 py-12 text-center text-slate-500 italic">
                                        {loading ? "Loading alerts..." : "No recent alerts found."}
                                    </td>
                                </tr>
                            ) : (
                                alerts.map((alert, i) => (
                                    <tr key={i} className="hover:bg-white/5 transition">
                                        <td className="px-6 py-4 whitespace-nowrap text-slate-400 font-mono text-xs">
                                            {alert.ts ? new Date(alert.ts).toLocaleTimeString() : "N/A"}
                                        </td>
                                        <td className="px-6 py-4 font-semibold text-slate-200">
                                            {alert.event}
                                        </td>
                                        <td className="px-6 py-4">
                                            <StatusPill
                                                status={alert.event.split('_')[1] || 'INFO'}
                                                variant={getSeverityVariant(alert.event)}
                                            />
                                        </td>
                                        <td className="px-6 py-4 text-xs text-slate-400 max-w-md truncate">
                                            {JSON.stringify(alert.details)}
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
