import json
import math
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
next_index = SHARD_INDEX
completed = 0
infra_failures = 0
invariant_failures = 0
SHARD_TARGET = max(0, math.ceil((TARGET - SHARD_INDEX) / SHARD_COUNT))


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
        global next_index, completed, infra_failures, invariant_failures
        with lock:
            if completed >= SHARD_TARGET or next_index >= TARGET:
                raise StopUser()
            index = next_index
            next_index += SHARD_COUNT

        epoch = index + 1
        outcome = f'{SEED}-{index}'
        refusal_id = f'locust-refusal-{SEED}-{index}-{uuid.uuid4().hex}'
        idem_a = f'locust-commit-a-{SEED}-{index}-{uuid.uuid4().hex}'
        idem_b = f'locust-commit-b-{SEED}-{index}-{uuid.uuid4().hex}'

        refuse = self.client.post('/refuse', json={'outcome': outcome, 'epoch': epoch, 'refusal_id': refusal_id}, name='POST /refuse')
        fence = self.client.post('/fence', json={'outcome': outcome, 'epoch': epoch}, name='POST /fence')
        if refuse.status_code in (502, 503, 504) or fence.status_code in (502, 503, 504):
            with lock:
                infra_failures += 1
            raise StopUser()

        if fence.status_code == 200:
            commit = self.client.post('/commit', json={'outcome': outcome, 'epoch': epoch, 'idempotency_key': idem_a}, name='POST /commit')
            if commit.status_code in (502, 503, 504):
                with lock:
                    infra_failures += 1
                raise StopUser()

        state_response = self.client.get(f'/state?outcome={outcome}', name='GET /state?outcome')
        if state_response.status_code != 200:
            with lock:
                infra_failures += 1
            raise StopUser()
        state = state_response.json()
        refused = state.get('refused') is True
        committed = state.get('committed') is True

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
            if completed >= SHARD_TARGET:
                raise StopUser()


@events.test_stop.add_listener
def emit_evidence(environment, **kwargs):
    with lock:
        verdict = 'PASS' if completed == SHARD_TARGET and infra_failures == 0 and invariant_failures == 0 else 'INCONCLUSIVE'
        evidence = {
            'evidence_type': 'external-authority-locust-concurrent-load-black-box',
            'rounds': TARGET,
            'completed_rounds': completed,
            'shard_target': SHARD_TARGET,
            'shard_index': SHARD_INDEX,
            'shard_count': SHARD_COUNT,
            'infrastructure_failures': infra_failures,
            'invariant_failures': invariant_failures,
            'seed': SEED,
            'verdict': verdict,
        }
    with open('locust-evidence.json', 'w', encoding='utf-8') as fh:
        json.dump(evidence, fh, indent=2, sort_keys=True)
        fh.write('\n')
    print(evidence)
