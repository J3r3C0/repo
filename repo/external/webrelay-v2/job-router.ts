// ========================================
// Sheratan WebRelay - Job Router & Prompt Builder
// ========================================

import { UnifiedJob } from './types.js';

// ========================================
// Core2 LCP System Prompt (Master Directive)
// ========================================
export const CORE2_LCP_SYSTEM_PROMPT = `Du darfst entscheiden, welche Aufgabe sinnvoll ist.
Protocol: LCP (JSON ONLY). No prose. No markdown fences.
PROPOSAL Structure: { "ok": true, "action": "create_followup_jobs", "thought": "...", "new_jobs": [] }
RESOLUTION Structure: { "ok": true, "action": "analysis_result", "answer": "..." }
End response with '}' ONLY.`;


/**
 * Build prompt from UnifiedJob
 * Extracts relevant parts based on job.kind and payload structure
 */
export class JobRouter {
  /**
   * Extract results from previous turns (Physical Results -> Mind Context)
   */
  private buildContextBlock(payload: any, params: any, artifacts: any): string {
    let context = '';
    const input = params.input || {};
    const lastToolResults = input.tool_results || [];
    const lastResult = payload.last_result || params.last_result;

    // 0. Explicit Injected Context (New Support)
    const explicitContext = params.context || payload.context || (payload.task?.params?.context) || (params.input?.context);
    if (explicitContext) {
      context += '\n### INJECTED CONTEXT:\n';
      context += (typeof explicitContext === 'object')
        ? JSON.stringify(explicitContext, null, 2)
        : explicitContext;
      context += '\n';
    }

    // 1. Tool Results (Primary Context)
    if (lastToolResults.length > 0) {
      context += '\n### FEEDBACK (Execution Results):\n';

      // Grouping by kind for better readability if multiple of same type
      const groups = lastToolResults.reduce((acc: any, res: any) => {
        const kind = res.kind || 'other';
        if (!acc[kind]) acc[kind] = [];
        acc[kind].push(res);
        return acc;
      }, {});

      for (const [kind, results] of Object.entries(groups)) {
        const resList = results as any[];
        context += `#### [${kind.toUpperCase()}] (${resList.length} items):\n`;

        for (const res of resList) {
          // Robust Unwrapping: Some workers wrap in 'result', others return it directly
          let resData = res.result || {};
          if (resData.ok && resData.result) {
            // This handles the { ok: true, result: { ... } } structure from api_real.py
            resData = resData.result;
          }

          const job_id = res.job_id ? ` (job:${res.job_id.substring(0, 8)})` : '';

          if (kind === 'read_file' || kind === 'read_read') {
            const path = resData.path || res.params?.path || 'unknown';
            context += `- FILE: ${path}${job_id}\n\`\`\`\n${(resData.content || '').substring(0, 1500)}\n\`\`\`\n`;
          } else if (kind === 'walk_tree' || kind === 'list_files') {
            const files = resData.files || [];
            const path = resData.path || resData.root || res.params?.path || 'root';
            context += `- PATH: ${path}${job_id} (${files.length} files)\n  ${files.slice(0, 100).join('\n  ')}${files.length > 100 ? '\n  ...' : ''}\n`;
          } else {
            context += `- DATA${job_id}:\n${JSON.stringify(resData, null, 2).substring(0, 1000)}\n`;
          }
        }
      }
    }

    // 2. Fallback Results (if no tool_results)
    if (lastResult && lastToolResults.length === 0) {
      const data = lastResult.data || lastResult;
      context += `\n### LATEST RESULT (Fallback):\n${JSON.stringify(data, null, 2).substring(0, 2000)}\n`;
    }

    // 3. Artifacts (Shared Knowledge)
    const activeArtifacts = artifacts && Object.keys(artifacts).length > 0 ? artifacts : (params.input?.artifacts || {});
    if (activeArtifacts && Object.keys(activeArtifacts).length > 0) {
      context += '\n### ARTIFACTS (Key Insights):\n';
      for (const [key, details] of Object.entries(activeArtifacts)) {
        const val = (details as any).value || details;
        const summary = Array.isArray(val)
          ? `${val.length} items: ${JSON.stringify(val.slice(0, 5))}...`
          : String(val).substring(0, 300);
        context += `- ${key}: ${summary}\n`;
      }
    }

    return context;
  }


  buildPrompt(job: any): string {
    // 0. Detect Schema Version
    const isEnvelope = job.schema_version === 'job_envelope_v1';
    const kind = isEnvelope ? (job.action?.kind || job.intent) : (job.kind || 'llm_call');

    // Normalize data for prompt builders
    const payload = isEnvelope ? (job.action?.params || {}) : (job.payload || {});
    const params = isEnvelope ? payload : (payload.task?.params || payload.params || {});
    const artifacts = isEnvelope ? (job.action?.params?.artifacts || {}) : (payload.artifacts || {});

    const context = this.buildContextBlock(payload, params, artifacts);

    // 1. Interactive Prompts
    if (params.prompt && (kind === 'llm_call' || kind === 'webrelay')) {
      const task = payload.task || {};
      return `${CORE2_LCP_SYSTEM_PROMPT}

MISSION: ${task.description || 'System Audit'}
CONTEXT: ${task.name || kind}
${context}
REQUEST: ${params.prompt}

PROPOSAL (JSON ONLY):`;
    }

    // 2. Autonomous turn (agent_plan)
    if (kind === 'agent_plan' || (payload.task && payload.mission) || isEnvelope) {
      const userPrompt = params.user_prompt || params.user_request || params.prompt || (params.input?.user_request) || (payload.task?.description) || (payload.mission?.description) || 'Plan mission';
      return `${CORE2_LCP_SYSTEM_PROMPT}
      
MISSION: ${userPrompt}
${context}
GENERATE LCP PROPOSAL (JSON ONLY):`;
    }

    // 3. Self-Loop format (Markdown Response expected)
    if (kind === 'self_loop' || kind === 'sheratan_selfloop') {
      const mission = (isEnvelope ? job.action?.params?.mission : job.payload?.mission) || {};
      const task = (isEnvelope ? job.action?.params?.task : job.payload?.task) || {};
      const state = (isEnvelope ? job.action?.params?.state : job.payload?.state) || {};

      return `Sheratan Self-Loop (Final Report Phase)

Mission: ${mission.title || ''}
Task: ${task.name || ''}
${context}
Current Loop State:
${JSON.stringify(state, null, 2)}

Provide a concise status report in Markdown (A/B/C/D format). No JSON.`;
    }

    // Fallback
    const rawPrompt = params.prompt || JSON.stringify(job, null, 2);
    return `${CORE2_LCP_SYSTEM_PROMPT}\n\n${context}\nREQUEST:\n${rawPrompt}\n\nRESPOND NOW WITH JSON ONLY:`;
  }
}
