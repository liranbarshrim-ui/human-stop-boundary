import http from 'k6/http';
import { check, fail } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

const BASE_URL = (__ENV.DAR_AUTHORITY_URL || 'https://dar-external-authority-v2.onrender.com').replace(/\/$/, '');
const ROUNDS = Number(__ENV.DAR_LOAD_ROUNDS || 10000);
const VUS = Number(__ENV.DAR_LOAD_VUS || 32);
const TIMEOUT = __ENV.DAR_LOAD_TIMEOUT || '30s';
const SEED = __ENV.DAR_LOAD_SEED || 'DAR-10K-B';

const infrastructureFailures = new Counter('dar_infrastructure_failures');
const invariantFailures = new Counter('dar_invariant_failures');
const roundPasses = new Counter('dar_round_passes');
const roundDuration = new Trend('dar_round_duration_ms', true);
const invariantRate = new Rate('dar_invariant_ok');

export const options = {
  vus: VUS,
  iterations: ROUNDS,
  maxDuration: __ENV.DAR_MAX_DURATION || '80m',
  batch: 8,
  batchPerHost: 8,
  discardResponseBodies: false,
  thresholds: {
    dar_infrastructure_failures: ['count==0'],
    dar_invariant_failures: ['count==0'],
    dar_invariant_ok: ['rate==1'],
  },
};

function body(response) {
  try { return response.json(); } catch (_) { return { parse_error: true, raw: response.body }; }
}

function statusOk(response) { return response && response.status >= 200 && response.status < 300; }
function infra(response) { return !response || response.status === 502 || response.status === 503 || response.status === 504; }

export function setup() {
  const res = http.get(`${BASE_URL}/health`, { timeout: TIMEOUT });
  const data = body(res);
  if (res.status !== 200 || data.ok !== true || data.persistence !== 'postgres') {
    throw new Error(`INCONCLUSIVE: authority is not ready: status=${res.status} body=${JSON.stringify(data)}`);
  }
  return { baseUrl: BASE_URL, seed: SEED, startedAt: new Date().toISOString() };
}

export default function (data) {
  const started = Date.now();
  const epoch = __ITER + 1;
  const outcome = `${SEED}-${__VU}-${epoch}`;
  const refusalId = `k6-refusal-${SEED}-${__VU}-${epoch}`;
  const idemA = `k6-commit-a-${SEED}-${__VU}-${epoch}`;
  const idemB = `k6-commit-b-${SEED}-${__VU}-${epoch}`;

  const raced = http.batch([
    ['POST', `${data.baseUrl}/refuse`, JSON.stringify({ outcome, epoch, refusal_id: refusalId }), { headers: { 'Content-Type': 'application/json' }, timeout: TIMEOUT }],
    ['POST', `${data.baseUrl}/fence`, JSON.stringify({ outcome, epoch }), { headers: { 'Content-Type': 'application/json' }, timeout: TIMEOUT }],
  ]);
  const refuse = raced[0];
  const fence = raced[1];

  if (infra(refuse) || infra(fence)) {
    infrastructureFailures.add(1);
    invariantRate.add(false);
    fail(`INCONCLUSIVE infrastructure failure: refuse=${refuse && refuse.status} fence=${fence && fence.status}`);
  }

  let commit = null;
  if (statusOk(fence)) {
    commit = http.post(`${data.baseUrl}/commit`, JSON.stringify({ outcome, epoch, idempotency_key: idemA }), { headers: { 'Content-Type': 'application/json' }, timeout: TIMEOUT });
    if (infra(commit)) {
      infrastructureFailures.add(1);
      invariantRate.add(false);
      fail(`INCONCLUSIVE infrastructure failure: commit=${commit && commit.status}`);
    }
  }

  // Targeted state avoids scanning/serializing all prior rounds after every round.
  const stateResponse = http.get(`${data.baseUrl}/state?outcome=${encodeURIComponent(outcome)}`, { timeout: TIMEOUT });
  if (infra(stateResponse) || stateResponse.status !== 200) {
    infrastructureFailures.add(1);
    invariantRate.add(false);
    fail(`INCONCLUSIVE infrastructure failure: state=${stateResponse && stateResponse.status}`);
  }
  const state = body(stateResponse);
  const refused = state.refused === true;
  const committed = state.committed === true;
  const exclusive = refused !== committed;

  let bypassStatus = null;
  if (refused) {
    const bypass = http.post(`${data.baseUrl}/commit`, JSON.stringify({ outcome, epoch, idempotency_key: idemB }), { headers: { 'Content-Type': 'application/json' }, timeout: TIMEOUT });
    if (infra(bypass)) {
      infrastructureFailures.add(1);
      invariantRate.add(false);
      fail(`INCONCLUSIVE infrastructure failure: fresh-idempotency=${bypass && bypass.status}`);
    }
    bypassStatus = bypass.status;
  }

  const bypassBlocked = !refused || bypassStatus === 409;
  const ok = exclusive && bypassBlocked && statusOk(stateResponse);
  invariantRate.add(ok);
  if (!ok) {
    invariantFailures.add(1);
    fail(`DAR invariant failure: refused=${refused} committed=${committed} bypass=${bypassStatus}`);
  }

  roundPasses.add(1);
  roundDuration.add(Date.now() - started);

  check({ refuse, fence, commit, stateResponse }, {
    'refuse observed': () => refuse.status < 600,
    'fence observed': () => fence.status < 600,
    'state observed': () => stateResponse.status === 200,
  });
}

export function handleSummary(data) {
  const infraCount = data.metrics.dar_infrastructure_failures?.values?.count || 0;
  const invariantCount = data.metrics.dar_invariant_failures?.values?.count || 0;
  const passes = data.metrics.dar_round_passes?.values?.count || 0;
  const verdict = infraCount === 0 && invariantCount === 0 && passes === ROUNDS ? 'PASS' : 'INCONCLUSIVE';
  const evidence = {
    evidence_type: 'external-authority-k6-concurrent-load-black-box',
    base_url: BASE_URL,
    rounds: ROUNDS,
    vus: VUS,
    seed: SEED,
    completed_rounds: passes,
    infrastructure_failures: infraCount,
    invariant_failures: invariantCount,
    verdict,
    generated_at: new Date().toISOString(),
  };
  return { stdout: JSON.stringify(evidence) + '\n', 'k6-evidence.json': JSON.stringify(evidence, null, 2) + '\n' };
}
