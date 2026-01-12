import { useState, useMemo } from "react";
import { MessageSquare, Send, Bot, User, Zap, CheckCircle2, AlertCircle, FileText, List, Search, Target } from "lucide-react";
import { useMissions } from "../../hooks/useMissions";
import { useJobs } from "../../hooks/useJobs";
import { useMissionChains } from "../../hooks/useChainContext";
import { missionsApi } from "../../api/missions";
import { useQueryClient } from "@tanstack/react-query";
import type { Mission, Job } from "../../types";

export function ChatTab() {
  const queryClient = useQueryClient();
  const [selectedMissionId, setSelectedMissionId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Data fetching
  const { data: missions = [] } = useMissions();
  const { data: allJobs = [] } = useJobs();

  // Filter for autonomous missions only
  const autonomousMissions = useMemo(() =>
    missions.filter(m => m.metadata?.type === "autonomous" || m.metadata?.created_by === "mission_control"),
    [missions]
  );

  // Chains for selected mission
  const { data: chains = [] } = useMissionChains(selectedMissionId || undefined);
  const activeChain = chains[0]; // Assuming one main chain per mission for now

  // Jobs for selected mission
  const missionJobs = useMemo(() => {
    if (!selectedMissionId) return [];
    // j.missionId in Job model is actually task_id, so we need a better filter
    // But missionsApi already transforms this. Let's filter allJobs by missionId
    return allJobs.filter(j => j.missionId === selectedMissionId);
  }, [allJobs, selectedMissionId]);

  const handleSubmit = async () => {
    if (!input.trim() || isSubmitting) return;

    setIsSubmitting(true);
    try {
      const { mission_id } = await missionsApi.submitMission(input);
      setSelectedMissionId(mission_id);
      setInput("");
      // Refresh data
      queryClient.invalidateQueries({ queryKey: ['missions'] });
    } catch (error) {
      console.error("Failed to submit mission:", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Find the agent_plan job to show the "Thought"
  const agentPlanJob = missionJobs.find(j => j.type === 'agent_plan');
  const thought = agentPlanJob?.result?.thought || activeChain?.artifacts?.last_thought?.value || "Waiting for agent to formulate plan...";

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-xl">Mission Control</h1>
        <p className="text-sm text-slate-400 mt-1">
          Formulate autonomous missions and monitor the cognitive driver's execution.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 h-[calc(100vh-220px)]">
        {/* Mission History Sidebar */}
        <div className="lg:col-span-1 bg-sheratan-card border border-slate-700 rounded-lg overflow-hidden flex flex-col">
          <div className="px-4 py-3 border-b border-slate-700 bg-slate-800/20">
            <h3 className="text-sm font-medium">Mission History</h3>
          </div>
          <div className="flex-1 overflow-y-auto divide-y divide-slate-800">
            {autonomousMissions.length === 0 && (
              <p className="p-4 text-xs text-slate-500 text-center">No autonomous missions yet.</p>
            )}
            {autonomousMissions.map((mission) => (
              <button
                key={mission.id}
                onClick={() => setSelectedMissionId(mission.id)}
                className={`w-full text-left px-4 py-3 hover:bg-slate-900/40 transition ${selectedMissionId === mission.id ? "bg-sheratan-accent/5 border-l-2 border-sheratan-accent" : ""
                  }`}
              >
                <div className="flex items-start gap-2 mb-1">
                  <Target className="w-4 h-4 text-slate-400 flex-shrink-0 mt-0.5" />
                  <span className="text-sm text-slate-200 line-clamp-1">{mission.name}</span>
                </div>
                <div className="flex items-center gap-2 mt-2 text-xs">
                  <span className={`px-1.5 py-0.5 rounded-full ${mission.status === 'running' ? 'bg-blue-900/40 text-blue-400' :
                    mission.status === 'completed' ? 'bg-emerald-900/40 text-emerald-400' :
                      'bg-slate-800 text-slate-400'
                    }`}>
                    {mission.status}
                  </span>
                  <span className="text-slate-500">{new Date(mission.createdAt).toLocaleDateString()}</span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Main Control Center */}
        <div className="lg:col-span-3 flex flex-col gap-6 overflow-hidden">

          {/* Top Panel: Goal & Thought */}
          <div className="bg-sheratan-card border border-slate-700 rounded-lg p-5">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-sheratan-accent/10 border border-sheratan-accent/40 flex items-center justify-center">
                <Bot className="w-6 h-6 text-sheratan-accent" />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-slate-200">
                  {selectedMissionId ? missions.find(m => m.id === selectedMissionId)?.name : "Ready for Deployment"}
                </h2>
                <p className="text-xs text-sheratan-accent">Cognitive Driver [LCP v2.0]</p>
              </div>
            </div>

            <div className="bg-slate-900/50 border border-slate-700/50 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <Zap className="w-3 h-3 text-amber-400" />
                <span className="text-[10px] uppercase tracking-wider font-bold text-slate-400">Current Thought</span>
              </div>
              <p className="text-sm text-slate-300 italic leading-relaxed">
                "{thought}"
              </p>
            </div>
          </div>

          {/* Bottom Panel: Split view for Chain & Artifacts */}
          <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-6 min-h-0">

            {/* Job Chain Tracking */}
            <div className="bg-sheratan-card border border-slate-700 rounded-lg flex flex-col overflow-hidden">
              <div className="px-4 py-2 bg-slate-800/20 border-b border-slate-700 flex items-center justify-between">
                <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400">Execution Chain</h3>
                <span className="text-[10px] text-slate-500">{missionJobs.length} Jobs</span>
              </div>
              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {missionJobs.length === 0 && (
                  <div className="h-full flex flex-col items-center justify-center text-slate-600 gap-2">
                    <List className="w-8 h-8 opacity-20" />
                    <p className="text-xs">No jobs in chain</p>
                  </div>
                )}
                {missionJobs.map((job) => (
                  <div key={job.id} className="flex items-center gap-3 p-2 bg-slate-800/30 rounded border border-slate-700/30">
                    <div className="flex-shrink-0">
                      {job.status === 'completed' || job.status === 'done' ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> :
                        job.status === 'failed' || job.status === 'error' ? <AlertCircle className="w-4 h-4 text-red-400" /> :
                          <div className="w-4 h-4 border-2 border-sheratan-accent border-t-transparent rounded-full animate-spin" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-xs font-medium text-slate-200 truncate">{job.type}</p>
                        <span className="text-[10px] text-slate-500">{job.id.substring(0, 8)}</span>
                      </div>
                      <div className="bg-slate-700/30 h-1 rounded-full mt-1.5 overflow-hidden">
                        <div className={`h-full ${job.status === 'completed' ? 'bg-emerald-500 w-full' : 'bg-sheratan-accent w-1/2 animate-pulse'}`} />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Collected Artifacts */}
            <div className="bg-sheratan-card border border-slate-700 rounded-lg flex flex-col overflow-hidden">
              <div className="px-4 py-2 bg-slate-800/20 border-b border-slate-700 flex items-center justify-between">
                <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400">Collected Artifacts</h3>
                <span className="text-[10px] text-slate-500">{Object.keys(activeChain?.artifacts || {}).length} Items</span>
              </div>
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {!activeChain?.artifacts && (
                  <div className="h-full flex flex-col items-center justify-center text-slate-600 gap-2">
                    <Search className="w-8 h-8 opacity-20" />
                    <p className="text-xs">Discovery in progress...</p>
                  </div>
                )}

                {/* File List Artifact */}
                {activeChain?.artifacts?.file_list && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <List className="w-3 h-3 text-sheratan-accent" />
                      <span className="text-[10px] font-bold text-slate-400 uppercase">File List</span>
                      <span className="text-[10px] text-slate-500">({(activeChain.artifacts.file_list.value as string[]).length} files)</span>
                    </div>
                    <div className="bg-slate-900/40 rounded border border-slate-800 p-2 max-h-32 overflow-y-auto">
                      {(activeChain.artifacts.file_list.value as string[]).slice(0, 10).map((file, i) => (
                        <div key={i} className="text-[11px] text-slate-400 font-mono py-0.5 flex items-center gap-2">
                          <div className="w-1 h-1 rounded-full bg-slate-700" title={file} />
                          <span className="truncate">{file.split('/').pop()}</span>
                        </div>
                      ))}
                      {(activeChain.artifacts.file_list.value as string[]).length > 10 && (
                        <div className="text-[10px] text-slate-500 italic mt-1">... and {(activeChain.artifacts.file_list.value as string[]).length - 10} more</div>
                      )}
                    </div>
                  </div>
                )}

                {/* File Content Artifacts */}
                {activeChain?.artifacts?.file_blobs && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <FileText className="w-3 h-3 text-blue-400" />
                      <span className="text-[10px] font-bold text-slate-400 uppercase">Read Content</span>
                    </div>
                    <div className="space-y-2">
                      {Object.entries(activeChain.artifacts.file_blobs.value as Record<string, string>).map(([path, content], i) => (
                        <div key={i} className="bg-slate-900/40 rounded border border-slate-800 overflow-hidden">
                          <div className="bg-slate-800/40 px-2 py-1 border-b border-slate-800 text-[10px] text-slate-300 font-mono truncate">
                            {path}
                          </div>
                          <pre className="p-2 text-[10px] text-slate-500 font-mono line-clamp-3">
                            {content}
                          </pre>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Input Area */}
          <div className="bg-sheratan-card border border-slate-700 rounded-lg p-4 shadow-xl shadow-black/20">
            <div className="flex gap-3">
              <div className="flex-1 relative">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
                  placeholder="Formulate your next mission (e.g., 'Discover and analyze worker code')..."
                  disabled={isSubmitting}
                  className="w-full bg-slate-800/50 border border-slate-700 rounded-lg pl-4 pr-12 py-3 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-sheratan-accent/60 transition"
                />
                <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${isSubmitting ? 'bg-amber-500 animate-pulse' : 'bg-emerald-500'}`} />
                </div>
              </div>
              <button
                onClick={handleSubmit}
                disabled={!input.trim() || isSubmitting}
                className={`bg-sheratan-accent text-slate-900 font-bold rounded-lg px-6 py-2 transition flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95 shadow-lg shadow-sheratan-accent/20`}
              >
                {isSubmitting ? (
                  <div className="w-4 h-4 border-2 border-slate-900 border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
                <span className="text-sm">Launch</span>
              </button>
            </div>
            <p className="text-[10px] text-slate-500 mt-2 ml-1 flex items-center gap-2">
              <Zap className="w-2 h-2" />
              Direct access to Sheratan Cognitive Engine. Missions are automatically broken down into autonomous job chains.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
