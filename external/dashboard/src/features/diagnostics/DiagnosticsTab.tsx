import { useEffect, useState } from "react";
import { getDiagnosticsList, triggerDiagnostics } from "../../api/system";
import { Archive, Download, Play, RefreshCw, CheckCircle2, Clock } from "lucide-react";

export function DiagnosticsTab() {
    const [bundles, setBundles] = useState<any[]>([]);
    const [running, setRunning] = useState(false);
    const [loading, setLoading] = useState(true);

    const fetch = async () => {
        setLoading(true);
        const data = await getDiagnosticsList();
        setBundles(data);
        setLoading(false);
    };

    useEffect(() => {
        fetch();
    }, []);

    const handleTrigger = async () => {
        setRunning(true);
        try {
            await triggerDiagnostics();
            await fetch();
        } catch (err) {
            console.error(err);
            alert("Diagnostic trigger failed. Check core logs.");
        } finally {
            setRunning(false);
        }
    };

    const formatSize = (bytes: number) => {
        if (bytes === 0) return "0 B";
        const k = 1024;
        const sizes = ["B", "KB", "MB", "GB"];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
    };

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold flex items-center gap-3">
                        <Archive className="w-6 h-6 text-indigo-400" />
                        Diagnostics
                    </h1>
                    <p className="text-slate-400">System State Snapshots & Log Bundles</p>
                </div>
                <button
                    onClick={handleTrigger}
                    disabled={running}
                    className={`flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm transition font-medium
          ${running ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                    {running ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                    Generate New Bundle
                </button>
            </div>

            <div className="bg-indigo-500/5 border border-indigo-500/10 rounded-xl p-6 flex items-start gap-4">
                <div className="bg-indigo-600/20 p-3 rounded-lg">
                    <CheckCircle2 className="w-6 h-6 text-indigo-400" />
                </div>
                <div>
                    <h4 className="text-sm font-semibold text-slate-200">Production Ready Diagnostics</h4>
                    <p className="text-xs text-slate-400 mt-1 max-w-xl">
                        Each bundle is automatically sanitized to remove secrets and credentials.
                        It captures the last 1000 lines of all logs, registry state, and current system configuration.
                    </p>
                </div>
            </div>

            <div className="bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden">
                <div className="p-4 border-b border-slate-800 bg-slate-800/30 flex justify-between items-center">
                    <span className="text-sm font-medium text-slate-300">Diagnostic Bundles History</span>
                    <button onClick={fetch} className="p-1 hover:bg-slate-700 rounded transition" title="Refresh list">
                        <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                    </button>
                </div>

                <div className="divide-y divide-slate-800/50">
                    {bundles.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-12 text-slate-500">
                            <Archive className="w-12 h-12 mb-2 opacity-20" />
                            <p className="text-sm italic">No bundles generated yet.</p>
                        </div>
                    ) : (
                        bundles.map((bundle, i) => (
                            <div key={i} className="px-6 py-4 flex items-center justify-between hover:bg-white/5 transition group">
                                <div className="flex items-center gap-4">
                                    <div className="w-10 h-10 rounded-lg bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20 group-hover:bg-indigo-500/20 transition">
                                        <Archive className="w-5 h-5 text-indigo-400" />
                                    </div>
                                    <div>
                                        <div className="text-sm font-medium text-slate-200">{bundle.name}</div>
                                        <div className="flex items-center gap-3 mt-1">
                                            <span className="flex items-center gap-1 text-[11px] text-slate-500">
                                                <Clock className="w-3 h-3" /> {new Date(bundle.created_at).toLocaleString()}
                                            </span>
                                            <span className="text-[11px] text-slate-600">•</span>
                                            <span className="text-[11px] text-slate-500 uppercase">{formatSize(bundle.size)}</span>
                                        </div>
                                    </div>
                                </div>
                                <button className="p-2 hover:bg-slate-800 rounded-full transition text-slate-500 hover:text-indigo-400" title="Download bundle">
                                    <Download className="w-5 h-5" />
                                </button>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
}
