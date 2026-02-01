// ========================================
// Sheratan WebRelay - Type Definitions
// ========================================

/**
 * Unified Job Schema - kompatibel mit Python worker_loop.py
 */
export interface UnifiedJob {
    job_id: string;
    kind: string;                      // "llm_call" | "agent_plan" | etc.
    created_at: string;

    payload: {
        // LCP Format (für agent_plan etc.)
        response_format?: 'lcp' | 'text';
        mission?: Record<string, any>;
        task?: {
            kind?: string;
            params?: Record<string, any>;
        };
        params?: Record<string, any>;

        // Direct prompt (für einfache llm_call)
        prompt?: string;
        context?: Record<string, any>;

        // Configuration
        llm_backend?: string;
        max_retries?: number;

        [key: string]: any;
    };

    meta?: Record<string, any>;
    session_id?: string | null;
    llm_backend?: string; // Top-level routing hint
}

/**
 * LCP Action - Represents a single action in the LCP protocol
 */
export interface LCPAction {
    kind: string;
    target: string;
    payload: Record<string, any>;
    meta?: Record<string, any>;
}

/**
 * Unified Result Schema - kompatibel mit Python worker expectations
 */
export interface UnifiedResult {
    job_id: string;
    kind?: string;
    created_at: string;
    ok: boolean;

    // LCP Response (wenn response_format === "lcp")
    action?: string;
    thought?: string;
    actions?: LCPAction[];
    commentary?: string;
    new_jobs?: any[];
    lcp_version?: string;
    type?: 'followup_jobs' | 'final_answer';
    jobs?: any[];
    answer?: any;
    meta?: Record<string, any>;

    // Plain Text Response
    summary?: string;

    // Self-Loop Response (raw markdown)
    text?: string;

    // Error info
    error?: string;

    // Metadata
    convoUrl?: string;
    session_id?: string | null;
    llm_backend?: string;
    execution_time_ms?: number;
}

/**
 * Parse Result - Internal parsing result
 */
export interface ParseResult {
    type: 'lcp' | 'text';
    thought?: string;
    actions?: LCPAction[];
    summary?: string;
    action?: string;
    new_jobs?: any[];
    commentary?: string;
    lcp_version?: string;
    lcp_type?: 'followup_jobs' | 'final_answer';
    jobs?: any[];
    answer?: any;
}

/**
 * LLM Backend Interface
 */
export interface LLMBackend {
    name: string;
    call(prompt: string): Promise<BackendCallResult>;
}

/**
 * Backend Call Result
 */
export interface BackendCallResult {
    answer: string;
    url?: string;
}

/**
 * Configuration Interface
 */
export interface WorkerConfig {
    backend: {
        chrome_port: number;
        timeout_ms: number;
    };
    parser: {
        auto_detect_lcp: boolean;
        sentinel: string;
    };
    watcher: {
        debounce_ms: number;
        stability_threshold: number;
        poll_interval: number;
    };
}

// ========================================
// Canonical Envelopes (Sheratan v1.1)
// ========================================

/**
 * JobEnvelope v1 (KANONISCH)
 * Reference: repo/docs/job_schema.md
 */
export interface JobEnvelopeV1 {
    schema_version: 'job_envelope_v1';
    job_id: string;
    mission_id?: string | null;
    task_id?: string | null;
    intent: string;
    action: {
        kind: string;
        params: Record<string, any>;
        capabilities?: string[];
        requires?: Record<string, any>;
    };
    provenance: {
        source_zone: string;
        created_at?: string | null;
        created_by?: any;
        build_id?: string | null;
    };
    policy_context?: Record<string, any>;
    refs?: {
        trace_id?: string | null;
        chain_id?: string | null;
    };
}

/**
 * ResultEnvelope v1 (KANONISCH)
 * Reference: repo/docs/job_schema.md
 */
export interface ResultEnvelopeV1 {
    schema_version: 'result_envelope_v1';
    job_id: string;
    ok: boolean;
    error?: string | null;
    result?: {
        summary?: string;
        data?: any;
    } | null;
    completed_at?: string | null;
    metrics?: Record<string, any> | null;
    refs?: {
        trace_id?: string | null;
        worker_id?: string | null;
    };
}
