#!/usr/bin/env python3
"""提交前校验。用法：python3 scripts/check.py [--offline]
1. 生成文件与 rulesets.yaml 一致（没人手改过）
2. 个人规则语法正确、无重复、直连/代理之间无冲突
3. 所有规则集 URL 可访问（--offline 跳过）
4. tests.yaml 里的域名分流结果符合预期（--offline 跳过）
"""
import pathlib, subprocess, sys, tempfile, shutil, urllib.request, yaml, configparser

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

# DNS 合并回归：普通 YAML 解析会丢弃 #!replace，必须同时检查原文。
st_text = (ROOT / 'stash.stoverride').read_text()
st = yaml.safe_load(st_text)
expected_servers = ['https://1.1.1.1/dns-query', 'https://1.0.0.1/dns-query']
expected_direct = ['https://223.5.5.5/dns-query', 'https://223.6.6.6/dns-query']
expected_dns_rules = ['IP-CIDR,1.1.1.1/32,🚀 节点选择,no-resolve',
                      'IP-CIDR,1.0.0.1/32,🚀 节点选择,no-resolve',
                      'IP-CIDR,223.5.5.5/32,DIRECT,no-resolve',
                      'IP-CIDR,223.6.6.6/32,DIRECT,no-resolve']
dns = st.get('dns', {})
if (dns.get('nameserver') != expected_servers or dns.get('follow-rule') is not True
        or dns.get('skip-cert-verify') is not False):
    err('Stash DNS 必须使用约定的 Cloudflare DoH、跟随规则并验证证书')
if '  nameserver: #!replace' not in st_text.splitlines():
    err('Stash nameserver 必须完全替换基础配置，不能与原 DNS 并发混用')
if st.get('rules', [])[:4] != expected_dns_rules:
    err('Stash DNS IP 规则必须排在最前，且带 no-resolve')
if dns.get('fallback') != [] or '  fallback: #!replace' not in st_text.splitlines():
    err('Stash 必须清空继承的并发 fallback')
if '  nameserver-policy: #!replace' not in st_text.splitlines():
    err('Stash 必须替换旧 nameserver-policy')
policies = dns.get('nameserver-policy', {})
rule_ids = [r.split(',')[1] for r in st['rules'] if r.startswith('RULE-SET,')]
if list(policies) != ['rule-set:' + sid for sid in rule_ids]:
    err('DNS policy 顺序必须与业务域名规则顺序一致')
domestic_ids = {'lan', 'personal_direct', 'apple_domain', 'apple', 'china_domain', 'china'}
for key, servers in policies.items():
    expected = expected_direct if key.removeprefix('rule-set:') in domestic_ids else expected_servers
    if servers != expected:
        err(f'{key} 使用了错误的 DNS 上游')
if 'proxy-groups' in st or 'proxies' in st:
    err('Stash 覆写不能定义节点或策略组')
if st['rules'][-1] != 'MATCH,🐟 漏网之鱼':
    err('Stash 必须保留 MATCH 兜底规则')
ok('Stash DNS 合并检查完成')

# Shadowrocket #proxy 是 URL 的一部分，不能按行内注释丢弃。
sr_text = (ROOT / 'shadowrocket.conf').read_text()
sr_config = configparser.ConfigParser(interpolation=None, inline_comment_prefixes=None)
sr_config.read_string(sr_text.split('[Proxy Group]')[0])
sr_general = sr_config['General']
expected_sr = [url + '#proxy' for url in expected_servers]
for key in ('dns-server', 'fallback-dns-server'):
    got = [v.strip() for v in sr_general.get(key, '').split(',')]
    if got != expected_sr:
        err(f'Shadowrocket {key} 必须为经默认节点的 Cloudflare DoH，不能回退系统 DNS')
if [v.strip() for v in sr_general.get('direct-dns-server', '').split(',')] != expected_direct:
    err('Shadowrocket 直连域名必须使用国内 DoH，不加 #proxy')
if sr_general.get('dns-direct-system') != 'false':
    err('Shadowrocket 不应对直连域名启用系统 DNS')
if sr_general.get('always-ip-address') != 'false':
    err('Shadowrocket 应保留代理域名的远端解析机制')
if [v.strip() for v in sr_general.get('proxy-dns-server', '').split(',')] != [
        'https://223.5.5.5/dns-query', 'https://223.6.6.6/dns-query']:
    err('节点域名必须使用独立 IP 形式 DoH 引导，不能依赖 #proxy')
if sr_general.get('update-url') != build.ME + '/shadowrocket.conf':
    err('Shadowrocket 必须保留可持续更新的订阅地址')
if not sr_text.rstrip().endswith('FINAL,PROXY'):
    err('Shadowrocket 必须保留 FINAL,PROXY 兜底')
ok('Shadowrocket DNS 配置检查完成（不替代实机验收）')

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
provider_domains = {}  # Stash 实际规则源中的域名项，用于独立检查 DNS policy
for r in cfg:
    rules = []
    for sr_type, sr_url, sid, beh, fmt, st_url in build.sources(r):
        if r['source'] == 'personal':
            text = (ROOT / 'rules' / f"{r['name']}.list").read_text()
            st_payload = text.splitlines()
        else:
            try:
                text = fetch(sr_url)
                st_text_source = fetch(st_url)
                st_payload = yaml.safe_load(st_text_source)['payload'] if fmt == 'yaml' else st_text_source.splitlines()
            except Exception as e:
                err(f'{r["label"]} 规则集无法访问：{e}')
                continue
        provider_domains[sid] = []
        for item in st_payload:
            item = str(item).strip()
            if not item or item.startswith('#'):
                continue
            if beh == 'domain':
                provider_domains[sid].append(('STDOMAIN', item.lower()))
            else:
                parts = item.split(',')
                if parts[0] in ('DOMAIN', 'DOMAIN-SUFFIX', 'DOMAIN-KEYWORD'):
                    provider_domains[sid].append((parts[0], parts[1].lower()))
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
    if t == 'STDOMAIN':
        if v.startswith('+.'): return h == v[2:] or h.endswith(v[1:])
        if v.startswith('.'): return h.endswith(v)
        return h == v
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

dns_tests = yaml.safe_load((ROOT / 'dns-tests.yaml').read_text())
for host, want in dns_tests.items():
    selected = dns['nameserver']
    for key, servers in policies.items():
        rules = provider_domains.get(key.removeprefix('rule-set:'), [])
        if any(match(host, t, v) for t, v in rules):
            selected = servers
            break
    got = 'domestic' if selected == expected_direct else 'cloudflare'
    if got != want:
        err(f'{host}: DNS 期望 {want}，实际 {got}')
ok(f'DNS 域名分流测试 {len(dns_tests)} 条完成（不模拟 IP/GEOIP 或策略组手动切换）')

print('\n全部通过' if not errors else f'\n{len(errors)} 个问题')
sys.exit(1 if errors else 0)
