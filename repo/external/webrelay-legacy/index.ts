import 'dotenv/config';

import path from 'path';
import fs from 'fs-extra';
import chokidar from 'chokidar';
import { fileURLToPath } from 'url';
import crypto from 'crypto';
import axios from 'axios';
import { UnifiedJob, UnifiedResult } from './types.js';
import { JobRouter } from './job-router.js';
import { ChatGPTBackend } from './backends/chatgpt.js';
import { GeminiBackend } from './backends/gemini.js';
import { parseResponse } from './parser.js';
import { startServer } from './api.js';
import { WebRelayHeartbeat } from './heartbeat.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const isDist = __dirname.endsWith('dist') || __dirname.includes('dist' + path.sep);

// Improved root detection: __dirname is the folder containing the script (e.g. dist/ or .)
// The project root is one level up from dist/
const PROJECT_ROOT = isDist ? path.resolve(__dirname, '..') : __dirname;

// Helper to resolve paths relative to PROJECT_ROOT
function resolvePath(envValue: string | undefined, defaultValue: string): string {
    if (!envValue) return path.join(PROJECT_ROOT, defaultValue);
    if (path.isAbsolute(envValue)) return envValue;
    return path.resolve(PROJECT_ROOT, envValue);
}

const RELAY_OUT = resolvePath(process.env.RELAY_OUT_DIR, 'runtime/narrative');
const RELAY_IN = resolvePath(process.env.RELAY_IN_DIR, 'runtime/output');
const RELAY_ARCHIVE = path.join(PROJECT_ROOT, 'runtime/archive');


// Load configuration
const configPath = path.join(PROJECT_ROOT, 'v_config', 'default-config.json');
const config = fs.readJSONSync(configPath);

// Initialize backend based on environment
const LLM_BACKEND = process.env.LLM_BACKEND || 'chatgpt';
const backend = LLM_BACKEND === 'gemini' ? new GeminiBackend(config) : new ChatGPTBackend();

// Job queue
type Job = { filename: string; fullPath: string };
const PENDING = new Map<string, NodeJS.Timeout>();
const QUEUE: Job[] = [];
let processing = false;

async function ensureDirs() {
    await fs.ensureDir(RELAY_OUT);
    await fs.ensureDir(RELAY_IN);
    await fs.ensureDir(RELAY_ARCHIVE);
}

const LEDGER_FILE = path.join(PROJECT_ROOT, 'runtime/output/ledger.jsonl');

async function logLedgerEvent(event: string, jobId: string | null, zone: string | null, artifactPath: string | null, meta: any = {}) {
    try {
        const ts = new Date().toISOString();
        let artifact = null;
        if (artifactPath && await fs.pathExists(artifactPath)) {
            const stats = await fs.stat(artifactPath);
            const content = await fs.readFile(artifactPath);
            const hash = crypto.createHash('sha256').update(content).digest('hex');
            artifact = {
                path: path.relative(PROJECT_ROOT, artifactPath).replace(/\\/g, '/'),
                sha256: hash,
                bytes: stats.size
            };
        }
        const entry = {
            ts,
            actor: 'webrelay',
            event,
            job_id: jobId,
            trace_id: jobId || 'root',
            zone,
            artifact,
            meta
        };
        await fs.ensureDir(path.dirname(LEDGER_FILE));
        await fs.appendFile(LEDGER_FILE, JSON.stringify(entry) + '\n');
    } catch (err) {
        console.error('[ledger] Ledger logging failed:', err);
    }
}

async function enqueue(job: Job) {
    QUEUE.push(job);
    if (!processing) {
        processing = true;
        try {
            while (QUEUE.length > 0) {
                const next = QUEUE.shift()!;
                await handleJob(next);
            }
        } finally {
            processing = false;
        }
    }
}

async function handleJob(job: Job) {
    try {
        const data: UnifiedJob = await fs.readJSON(job.fullPath).catch(() => null);
        if (!data) {
            console.warn(`[WARN] Invalid JSON: ${job.filename}`);
            return;
        }

        const router = new JobRouter();
        const registration = {
            capabilities: [
                { kind: 'llm_call' },
                { kind: 'agent_plan' },
                { kind: 'analyze_file' }
            ]
        };

        const isSupported = (kind: string) => {
            return registration.capabilities.some(c => c.kind === kind);
        };

        if (!isSupported(data.kind)) {
            console.warn(`[MSG] ⏭ Skipping Job ${data.job_id} (kind: ${data.kind}) - Capability not supported by WebRelay.`);
            return;
        }

        console.log(`\n[MSG] Processing Job: ${data.job_id} (${data.kind})`);

        const startTime = Date.now();

        try {
            // Build prompt
            const prompt = router.buildPrompt(data);
            console.log(`[EDIT] Prompt length: ${prompt.length} chars`);

            // Call ChatGPT
            console.log(`[ROBOT] Calling ChatGPT...`);
            const result = await backend.call(prompt);

            // Parse response
            const parsed = parseResponse(result.answer, { sentinel: config.parser.sentinel });
            console.log(`[PASS] Response type: ${parsed.type}`);

            // Build canonical ResultEnvelope v1 (Sheratan v1.1)
            const out: any = {
                schema_version: 'result_envelope_v1',
                job_id: data.job_id,
                ok: true,
                result: {
                    summary: parsed.summary || parsed.thought || 'Action processed.',
                    data: parsed
                },
                completed_at: new Date().toISOString(),
                metrics: {
                    execution_time_ms: Date.now() - startTime,
                    llm_backend: backend.name
                },
                refs: {
                    trace_id: (data as any).refs?.trace_id || data.job_id,
                    worker_id: process.env.WORKER_ID || 'webrelay_worker'
                }
            };

            await writeResult(job.filename, out);
            console.log(`[PASS] Job Result: ${data.job_id}`);

            // Archive the job file (Gemini's Wish)
            await archiveJob(job.fullPath, job.filename, out);

        } catch (err: any) {
            console.error(`[FAIL] Job failed:`, err?.message || err);
            const errorEnvelope: any = {
                schema_version: 'result_envelope_v1',
                job_id: data.job_id,
                ok: false,
                error: err?.message || String(err),
                completed_at: new Date().toISOString(),
                metrics: { execution_time_ms: Date.now() - startTime }
            };

            await writeResult(job.filename, errorEnvelope);
            await archiveJob(job.fullPath, job.filename, errorEnvelope);
        }
    } catch (err: any) {
        console.error(`[FAIL] Error processing ${job.filename}:`, err?.message || err);
    }
}

async function writeResult(jobFilename: string, result: any) {
    try {
        const resultFilename = jobFilename.replace(/(\.job)?\.json$/, '.result.json');
        const outPath = path.join(RELAY_IN, resultFilename);
        console.log(`[PASS] Writing result to: ${outPath}`);
        await fs.writeJSON(outPath, result, { spaces: 2 });

        // Log: MESH_RESULT_WRITTEN
        await logLedgerEvent('MESH_RESULT_WRITTEN', result.job_id, 'output', outPath, {
            ok: result.ok,
            llm_backend: result.metrics?.llm_backend
        });
    } catch (err) {
        console.error(`[FAIL] Failed to write result file:`, err);
    }
}

async function archiveJob(fullPath: string, filename: string, result: any) {
    try {
        const archivePath = path.join(RELAY_ARCHIVE, filename);
        const jobData = await fs.readJSON(fullPath);

        // Merge result into job data (User's preference)
        const completedJob = {
            ...jobData,
            status: result.ok ? 'completed' : 'failed',
            result: result
        };

        await fs.writeJSON(archivePath, completedJob, { spaces: 2 });
        await fs.remove(fullPath);
        console.log(`[ARCHIVE] Job archived to runtime/archive/${filename}`);
    } catch (err) {
        console.error(`[FAIL] Archiving failed for ${filename}:`, err);
    }
}

function debounceFile(fullPath: string) {
    const filename = path.basename(fullPath).toLowerCase();
    if (!filename.endsWith('.json')) return;

    // Log: PROPOSAL_WRITTEN (if it's a proposal_*.json)
    if (filename.startsWith('proposal_')) {
        const jobId = filename.replace('proposal_', '').replace('.json', '');
        logLedgerEvent('PROPOSAL_WRITTEN', jobId, 'narrative', fullPath, { actor: 'gemini' });
    }

    const prev = PENDING.get(fullPath);
    if (prev) clearTimeout(prev);

    const timer = setTimeout(() => {
        PENDING.delete(fullPath);
        enqueue({ filename: path.basename(fullPath), fullPath });
    }, config.watcher.debounce_ms);

    PENDING.set(fullPath, timer);
}

async function startFileWatcher() {
    await ensureDirs();

    console.log('[FILES] File Watcher Mode:');
    console.log(`   OUT: ${RELAY_OUT}`);
    console.log(`   IN:  ${RELAY_IN}`);
    console.log();

    // Process existing files
    const files = (await fs.readdir(RELAY_OUT)).filter((f: string) => f.endsWith('.json'));
    for (const f of files) debounceFile(path.join(RELAY_OUT, f));

    console.log(`[WATCH] Watcher active on: ${RELAY_OUT}`);
    console.log();

    const watcher = chokidar.watch(RELAY_OUT, {
        ignoreInitial: true,
        depth: 0,
        awaitWriteFinish: {
            stabilityThreshold: config.watcher.stability_threshold,
            pollInterval: config.watcher.poll_interval
        }
    });

    watcher
        .on('add', debounceFile)
        .on('change', debounceFile)
        .on('error', (e) => console.error('[FAIL] Watcher-Fehler:', e));
}

async function registerWorker() {
    const CORE_URL = process.env.SHERATAN_CORE_URL || 'http://localhost:8001';
    const WORKER_ID = process.env.WORKER_ID || 'webrelay_worker';

    const registration = {
        worker_id: WORKER_ID,
        capabilities: [
            { kind: 'llm_call', cost: 25 },
            { kind: 'agent_plan', cost: 30 },
            { kind: 'analyze_file', cost: 20 }
        ],
        status: 'online',
        endpoint: process.env.WEBRELAY_ENDPOINT || 'http://localhost:3000',
        meta: {
            llm_backend: process.env.LLM_BACKEND || 'chatgpt',
            version: '2.0'
        }
    };

    try {
        const response = await axios.post(
            `${CORE_URL}/api/mesh/workers/register`,
            registration,
            { timeout: 5000 }
        );
        console.log(`[MESH] ✓ Registered as ${WORKER_ID}`);
        console.log(`[MESH] Capabilities: ${registration.capabilities.map(c => c.kind).join(', ')}`);
    } catch (err: any) {
        console.error('[MESH] ⚠ Registration failed:', err.message);
        console.error('[MESH] Will retry on next startup...');
    }
}

async function main() {
    console.log('╔═══════════════════════════════════════════════════════╗');
    console.log('║   Sheratan WebRelay v2.0 - Dual LLM Support         ║');
    console.log('╚═══════════════════════════════════════════════════════╝');
    console.log();
    console.log(`[ROBOT] LLM Backend: ${backend.name}`);
    console.log(`[DIR] Watcher (IN):  ${RELAY_OUT}`);
    console.log(`[DIR] Results (OUT): ${RELAY_IN}`);
    console.log(`[DIR] Archive:       ${RELAY_ARCHIVE}`);
    console.log();

    // Start HTTP API Server
    await startServer();

    // 🆕 Register with Mesh
    await registerWorker();

    // Start File Watcher (for backward compatibility)
    await startFileWatcher();

    // Start Heartbeat
    const heartbeat = new WebRelayHeartbeat();
    heartbeat.start();

    console.log('[READY] WebRelay Ready! HTTP API + File Watcher + Mesh Registration + Heartbeat Active');
    console.log();
}

main();

