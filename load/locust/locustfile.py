import os
import threading
import uuid

from locust import HttpUser, between, task, events
from locust.exception import StopUser

TARGET = int(os.getenv('DAR_LOAD_ROUNDS', '10000'))
SEED = os.getenv('DAR_LOAD_SEED', 'DAR-10K-B')
SHARD_INDEX = int(os.getenv('DAR_SHARD_INDEX', '0'))
SHARD_COUNT = int(os.getenv('DAR_SHARD_COUNT', '1'))

lock = threading.Lock()
started = 0
completed = 0
infra_failures = 0
invariant_failures = 0


def owns(index: int) -> bool:
    return index % SHARD_COUNT == SHARD_INDEX


class DarAuthorityUser(HttpUser):
    wait_time = between(0, 0.02)

    def on_start(self):
        r = self.client.get('/health', name='GET /health')
        if r.status_code != 200:
            raise RuntimeError(f'INCONCLUSIVE: /health={r.status_code}')
        data = r.json()
        if data.get('ok') is not True or data.get('persistence') != 'postgres':
            raise RuntimeError(f'INCONCLUSIVE: authority not postgres-ready: {data}')

    @task
    def race_round(self):
        global started, completed, infra_failures, invariant_failures
        with lock:
            index = started
            while index < TARGET and not owns(index):
                index += 1
            if index >= TARGET:
                raise StopUser()
            started += 1

        epoch = index + 1
        outcome = f'{SEED}-{index}'
        refusal_id = f'locust-refusal-{SEED}-{index}-{uuid.uuid4().hex}'
        idem_a = f'locust-commit-a-{SEED}-{index}-{uuid.uuid4().hex}'
        idem_b = f'locust-commit-b-{SEED}-{index}-{uuid.uuid4().hex}'

        # Locust's task is intentionally conservative: the two race requests are
        # issued in rapid succession; k6 remains the canonical true batch-race engine.
        refuse = self.client.post('/refuse', json={'outcome': outcome, 'epoch': epoch, 'refusal_id': refusal_id}, name='POST /refuse')
        fence = self.client.post('/fence', json={'outcome': outcome, 'epoch': epoch}, name='POST /fence')
        if refuse.status_code in (502, 503, 504) or fence.status_code in (502, 503, 504):
            with lock:
                infra_failures += 1
            raise StopUser()

        commit = None
        if fence.status_code == 200:
            commit = self.client.post('/commit', json={'outcome': outcome, 'epoch': epoch, 'idempotency_key': idem_a}, name='POST /commit')
            if commit.status_code in (502, 503, 504):
                with lock:
                    infra_failures += 1
                raise StopUser()

        state_response = self.client.get('/state', name='GET /state')
        if state_response.status_code in (502, 503, 504) or state_response.status_code != 200:
            with lock:
                infra_failures += 1
            raise StopUser()
        state = state_response.json()
        refused = outcome in state.get('refusals', {})
        committed = outcome in state.get('committed_outcomes', {})

        bypass_status = None
        if refused:
            bypass = self.client.post('/commit', json={'outcome': outcome, 'epoch': epoch, 'idempotency_key': idem_b}, name='POST /commit fresh-idempotency')
            bypass_status = bypass.status_code
            if bypass_status in (502, 503, 504):
                with lock:
                    infra_failures += 1
                raise StopUser()

        ok = (refused != committed) and ((not refused) or bypass_status == 409)
        if not ok:
            with lock:
                invariant_failures += 1
            raise AssertionError(f'DAR invariant failure: refused={refused} committed={committed} bypass={bypass_status}')

        with lock:
            completed += 1
            if completed >= TARGET:
                raise StopUser()


@events.test_stop.add_listener
def emit_evidence(environment, **kwargs):
    with lock:
        verdict = 'PASS' if completed == TARGET and infra_failures == 0 and invariant_failures == 0 else 'INCONCLUSIVE'
        evidence = {
            'evidence_type': 'external-authority-locust-concurrent-load-black-box',
            'rounds': TARGET,
            'completed_rounds': completed,
            'shard_index': SHARD_INDEX,
            'shard_count': SHARD_COUNT,
            'infrastructure_failures': infra_failures,
            'invariant_failures': invariant_failures,
            'seed': SEED,
            'verdict': verdict,
        }
    with open('locust-evidence.json', 'w', encoding='utf-8') as fh:
        import json
        json.dump(evidence, fh, indent=2, sort_keys=True)
        fh.write('\n')
    print(evidence)
