#!/usr/bin/env python3
"""提交前校验。用法：python3 scripts/check.py [--offline]
1. 生成文件与 rulesets.yaml 一致（没人手改过）
2. 个人规则语法正确、无重复、直连/代理之间无冲突
3. 所有规则集 URL 可访问（--offline 跳过）
4. tests.yaml 里的域名分流结果符合预期（--offline 跳过）
"""
import pathlib, subprocess, sys, tempfile, shutil, urllib.request, yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import build

errors = []
def err(msg): errors.append(msg); print('✗', msg)
def ok(msg): print('✓', msg)

# 1. 生成文件是否最新
before = {f: (ROOT / f).read_text() for f in ('shadowrocket.conf', 'stash.stoverride')}
build.main()
for f, txt in before.items():
    if (ROOT / f).read_text() != txt:
        err(f'{f} 与 rulesets.yaml 不一致（已重新生成，请一并提交）')
ok('生成文件检查完成')

# 2. 个人规则语法
TYPES = {'DOMAIN', 'DOMAIN-SUFFIX', 'DOMAIN-KEYWORD', 'IP-CIDR', 'IP-CIDR6'}
seen = {}
for f in sorted((ROOT / 'rules').glob('*.list')):
    for i, line in enumerate(f.read_text().splitlines(), 1):
        s = line.strip()
        if not s or s.startswith('#'):
            continue
        p = s.split(',')
        where = f'{f.name}:{i}'
        if p[0] not in TYPES:
            err(f'{where} 不支持的类型 {p[0]}')
        elif p[0].startswith('IP-CIDR'):
            if p[2:] != ['no-resolve']:
                err(f'{where} IP 规则必须写成 IP-CIDR,<段>,no-resolve 且不带策略')
        elif len(p) != 2:
            err(f'{where} 域名规则只能有两段（类型,值），不要写策略')
        key = ','.join(p[:2]).lower()
        if key in seen:
            err(f'{where} 与 {seen[key]} 重复')
        seen[key] = where
ok(f'个人规则 {len(seen)} 条检查完成')

if '--offline' in sys.argv:
    sys.exit(1 if errors else 0)

# 3. URL 可达 & 4. 下载 SR 版本做分流模拟
cfg = yaml.safe_load((ROOT / 'rulesets.yaml').read_text())['rulesets']
def fetch(u):
    req = urllib.request.Request(u, headers={'User-Agent': 'proxy-rules-check'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode()
chain = []  # (policy, rules)
for r in cfg:
    rules = []
    for sr_type, sr_url, _, _, _, st_url in build.sources(r):
        if r['source'] == 'personal':
            text = (ROOT / 'rules' / f"{r['name']}.list").read_text()
        else:
            try:
                text = fetch(sr_url)
                fetch(st_url)
            except Exception as e:
                err(f'{r["label"]} 规则集无法访问：{e}')
                continue
        for l in text.splitlines():
            l = l.strip()
            if not l or l.startswith('#'):
                continue
            if sr_type == 'DOMAIN-SET':
                rules.append(('DSET', l.lower()))
            else:
                p = l.split(',')
                if len(p) >= 2:
                    rules.append((p[0], p[1].lower()))
    chain.append((r['policy'], r['label'], rules))
ok('规则集下载完成')

def match(h, t, v):
    if t == 'DSET':
        return h == v.lstrip('.') or (v.startswith('.') and h.endswith(v))
    if t == 'DOMAIN': return h == v
    if t == 'DOMAIN-SUFFIX': return h == v or h.endswith('.' + v)
    if t == 'DOMAIN-KEYWORD': return v in h
    return False

def route(h):
    for pol, label, rules in chain:
        for t, v in rules:
            if match(h, t, v):
                return pol, f'{label} ({t},{v})'
    return 'fallback', '兜底'

tests = yaml.safe_load((ROOT / 'tests.yaml').read_text())
for host, want in tests.items():
    got, why = route(host)
    if got != want:
        err(f'{host}: 期望 {want}，实际 {got}，命中 {why}')
ok(f'分流测试 {len(tests)} 条完成')

print('\n全部通过' if not errors else f'\n{len(errors)} 个问题')
sys.exit(1 if errors else 0)
