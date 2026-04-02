#!/usr/bin/env python3
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

WORKDIR = Path('/home/domk/.openclaw/workspace')
MODEL = 'local-qwen'
TIMEOUT = 180
ROUTE = 'local-qwen-bench'


def run_cmd(cmd):
    start = time.perf_counter()
    proc = subprocess.run(
        cmd,
        cwd=WORKDIR,
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
    )
    end = time.perf_counter()
    return {
        'cmd': cmd,
        'returncode': proc.returncode,
        'stdout': proc.stdout,
        'stderr': proc.stderr,
        'elapsed_s': end - start,
    }


def make_text(chars):
    base = 'QWENBENCH ' + ('абвгдежзийклмнопрстуфхцчшщъыьэюя ' * 20)
    chunks = []
    while len(''.join(chunks)) < chars:
        chunks.append(base)
    return ''.join(chunks)[:chars]


def build_prompt(size_chars, question):
    filler = make_text(size_chars)
    return (
        'Ты тестовая локальная модель.\\n'
        'Ниже длинный контекст. Игнорируй шум, но ответь точно на вопрос в конце.\\n\\n'
        f'{filler}\\n\\n'
        f'Контрольный вопрос: {question}\\n'
        'Ответь только финальным значением без объяснений.'
    )


def normalize_text(value):
    return ' '.join((value or '').strip().split())


def extract_response_text(stdout):
    raw = (stdout or '').strip()
    if not raw:
        return ''
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return raw

    if isinstance(parsed, str):
        return parsed.strip()
    if isinstance(parsed, dict):
        for key in ('answer', 'content', 'response', 'output', 'text', 'message'):
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        for key in ('data', 'result'):
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, dict):
                nested = extract_response_text(json.dumps(value, ensure_ascii=False))
                if nested:
                    return nested.strip()
        return raw
    if isinstance(parsed, list):
        for item in parsed:
            if isinstance(item, str) and item.strip():
                return item.strip()
            if isinstance(item, dict):
                nested = extract_response_text(json.dumps(item, ensure_ascii=False))
                if nested:
                    return nested.strip()
    return raw


def run_prompt(prompt):
    cmd = [
        'openclaw', 'agent',
        '--local',
        '--to', ROUTE,
        '--message', prompt,
        '--json',
        '--timeout', str(TIMEOUT),
    ]
    start = time.perf_counter()
    proc = subprocess.run(
        cmd,
        cwd=WORKDIR,
        capture_output=True,
        text=True,
        timeout=TIMEOUT + 30,
    )
    end = time.perf_counter()
    return {
        'returncode': proc.returncode,
        'stdout': proc.stdout,
        'stderr': proc.stderr,
        'elapsed_s': end - start,
        'cmd': cmd,
    }


def test_case(name, size_chars, expected):
    prompt = build_prompt(size_chars, expected)
    res = run_prompt(prompt)
    out = extract_response_text(res['stdout'])
    ok = res['returncode'] == 0 and normalize_text(out) == normalize_text(expected)
    return {
        'name': name,
        'size_chars': size_chars,
        'expected': expected,
        'ok': ok,
        'elapsed_s': round(res['elapsed_s'], 3),
        'returncode': res['returncode'],
        'stdout_preview': normalize_text(out)[:500],
        'stderr_preview': (res['stderr'] or '').strip()[:500],
        'cmd': ' '.join(res['cmd'][:-1]) + ' <prompt>'
    }


def speed_case(name, prompt, repeats=3):
    times = []
    samples = []
    for _ in range(repeats):
        res = run_prompt(prompt)
        times.append(res['elapsed_s'])
        samples.append({
            'returncode': res['returncode'],
            'stdout_preview': (res['stdout'] or '').strip()[:200],
            'stderr_preview': (res['stderr'] or '').strip()[:200],
            'elapsed_s': round(res['elapsed_s'], 3),
        })
    return {
        'name': name,
        'repeats': repeats,
        'min_s': round(min(times), 3),
        'max_s': round(max(times), 3),
        'avg_s': round(statistics.mean(times), 3),
        'samples': samples,
    }


def main():
    report = {
        'model': MODEL,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'context_tests': [],
        'speed_tests': [],
    }

    report['context_tests'].append(test_case('ctx_4k_chars', 4_000, '42'))
    report['context_tests'].append(test_case('ctx_20k_chars', 20_000, '31415'))
    report['context_tests'].append(test_case('ctx_80k_chars', 80_000, '271828'))
    report['context_tests'].append(test_case('ctx_160k_chars', 160_000, '65537'))

    report['speed_tests'].append(speed_case('speed_short', 'Ответь одним словом: ping', repeats=3))
    report['speed_tests'].append(speed_case('speed_medium', build_prompt(12_000, 'orange'), repeats=3))

    out_path = WORKDIR / 'qwen_local_benchmark_report.json'
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
