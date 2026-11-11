#!/usr/bin/env python3
"""从 rulesets.yaml 生成 shadowrocket.conf 和 stash.stoverride。用法：python3 scripts/build.py"""
import pathlib, re, yaml
from ipaddress import ip_address, ip_network
from urllib.parse import urlsplit

ROOT = pathlib.Path(__file__).resolve().parent.parent
ME = 'https://cdn.jsdelivr.net/gh/haoyan-yam/proxy-rules@main'
BM = 'https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule'
SR_POL = {'proxy': 'PROXY', 'direct': 'DIRECT', 'reject': 'REJECT', 'apple': '🍎 苹果服务'}
ST_POL = {'proxy': '🚀 节点选择', 'direct': '🎯 全球直连', 'reject': 'REJECT', 'apple': '🍎 苹果服务'}

def sources(rs):
    """返回 [(sr_type, sr_url, stash_id, stash_behavior, stash_format, stash_url)]"""
    n = rs['name']
    if rs['source'] == 'personal':
        u = f'{ME}/rules/{n}.list'
        return [('RULE-SET', u, n, 'classical', 'text', u)]
    out = []
    if rs.get('domain_set'):
        out.append(('DOMAIN-SET', f'{BM}/Shadowrocket/{n}/{n}_Domain.list',
                    f'{n.lower()}_domain', 'domain', 'yaml', f'{BM}/Clash/{n}/{n}_Domain.yaml'))
    out.append(('RULE-SET', f'{BM}/Shadowrocket/{n}/{n}.list',
                n.lower(), 'classical', 'yaml', f'{BM}/Clash/{n}/{n}_No_Resolve.yaml'))
    return out

def validate_doh(servers, label):
    if not isinstance(servers, list) or not servers or len(servers) != len(set(servers)):
        raise ValueError(f'{label} 必须为非空且不重复的列表')
    for server in servers:
        url = urlsplit(server)
        if (url.scheme != 'https' or url.username or url.password or not url.path
                or url.query or url.fragment):
            raise ValueError(f'{label} 必须使用不含凭证、查询参数或片段的 HTTPS URL')
        ip_address(url.hostname)  # 必须为 IP，不能依赖 DNS 解析自身

def connection_rule(rule, policy='DIRECT'):
    parts = rule.split(',')
    return ','.join(parts[:2] + [policy] + parts[2:])

def generated_files(settings):
    return ['shadowrocket.conf', 'stash.stoverride'] + [
        f'stash-{profile}.stoverride' for profile in settings.get('stash_interface_profiles', {})]

def main():
    settings = yaml.safe_load((ROOT / 'rulesets.yaml').read_text())
    cfg = settings['rulesets']
    tailnet_rules = settings['stash_tailnet_rules']
    direct_rules = settings.get('stash_direct_rules', [])
    profiles = settings.get('stash_interface_profiles', {})
    for profile, config in profiles.items():
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', profile):
            raise ValueError('Stash 设备标识只能使用小写字母、数字及中间连字符')
        if not re.fullmatch(r'utun[0-9]+', config['interface-name']):
            raise ValueError('Tailscale 接口必须为在该设备确认过的 utun 编号')
    for rule in tailnet_rules + direct_rules:
        parts = rule.split(',')
        if parts[0] in ('IP-CIDR', 'IP-CIDR6'):
            if len(parts) != 3 or parts[2] != 'no-resolve':
                raise ValueError('stash_direct_rules IP 规则必须带 no-resolve 且不带策略')
            net = ip_network(parts[1], strict=True)
            if net.version != (4 if parts[0] == 'IP-CIDR' else 6):
                raise ValueError('stash_direct_rules IP 规则类型与地址族不符')
            continue
        if (len(parts) != 2 or not parts[1]
                or parts[0] not in ('DOMAIN', 'DOMAIN-SUFFIX', 'DST-PORT')):
            raise ValueError('stash_direct_rules 仅支持域名、目标端口和带 no-resolve 的 IP 网段')
        if parts[0] == 'DST-PORT' and not (parts[1].isdigit() and 1 <= int(parts[1]) <= 65535):
            raise ValueError('stash_direct_rules 目标端口必须为 1–65535')
    dns_servers = settings['stash_dns']['nameservers']
    validate_doh(dns_servers, 'stash_dns.nameservers')
    magicdns = settings['stash_dns']['magicdns']
    suffix = magicdns['suffix']
    if not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.ts\.net', suffix):
        raise ValueError('stash_dns.magicdns.suffix 必须为具体的 tailnet.ts.net 后缀')
    if magicdns['nameserver'] != '100.100.100.100':
        raise ValueError('MagicDNS 必须使用本机 Tailscale 的 100.100.100.100')
    direct_servers = settings['direct_dns']['nameservers']
    validate_doh(direct_servers, 'direct_dns.nameservers')
    sr_dns = settings['shadowrocket_dns']
    validate_doh(sr_dns['nameservers'], 'shadowrocket_dns.nameservers')
    validate_doh(sr_dns['node_nameservers'], 'shadowrocket_dns.node_nameservers')
    sr_upstream = ', '.join(f'{server}#proxy' for server in sr_dns['nameservers'])
    sr_bootstrap = ', '.join(sr_dns['node_nameservers'])
    sr_direct = ', '.join(direct_servers)
    dns_rules = []
    for server in dns_servers:
        ip = ip_address(urlsplit(server).hostname)
        kind = 'IP-CIDR' if ip.version == 4 else 'IP-CIDR6'
        dns_rules.append(f'{kind},{ip}/{ip.max_prefixlen},🚀 节点选择,no-resolve')
    for server in direct_servers:
        ip = ip_address(urlsplit(server).hostname)
        kind = 'IP-CIDR' if ip.version == 4 else 'IP-CIDR6'
        dns_rules.append(f'{kind},{ip}/{ip.max_prefixlen},DIRECT,no-resolve')
    order = ' → '.join(r['label'] for r in cfg) + ' → GEOIP CN 直连 → 其余走代理'
    hdr = '# 自动生成：改 rulesets.yaml 后运行 scripts/build.py，不要手改本文件\n'

    sr = [hdr, '# 目标客户端：Shadowrocket 2.2.93（iOS/iPadOS）；需在设备更新后验收。',
          '# DNS 分流：直连域名用国内 DoH；默认/备用 Cloudflare DoH 经首页所选节点。',
          '# 代理域名仍保留远端解析；节点域名单独使用 AliDNS 引导。升级/回退见 README。',
          f'# 规则顺序：{order}', '[General]',
          'ipv6 = false', 'bypass-system = true',
          'skip-proxy = 192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12, fe80::/10, fc00::/7, localhost, *.local, *.lan, *.internal, e.crashlytics.com, captive.apple.com, sequoia.apple.com, seed-sequoia.siri.apple.com, *.ls.apple.com',
          'bypass-tun = 10.0.0.0/8,100.64.0.0/10,127.0.0.0/8,169.254.0.0/16,172.16.0.0/12,192.0.0.0/24,192.0.2.0/24,192.88.99.0/24,192.168.0.0/16,198.18.0.0/15,198.51.100.0/24,203.0.113.0/24,233.252.0.0/24,224.0.0.0/4,255.255.255.255/32,::1/128,::ffff:0:0/96,::ffff:0:0:0/96,64:ff9b::/96,64:ff9b:1::/48,100::/64,2001::/32,2001:20::/28,2001:db8::/32,2002::/16,3fff::/20,5f00::/16,fc00::/7,fe80::/10,ff00::/8',
          f'dns-server = {sr_upstream}',
          f'direct-dns-server = {sr_direct}',
          '# 不留空：备用 DNS 留空可能等同于 system。',
          f'fallback-dns-server = {sr_upstream}',
          'dns-direct-system = false',
          'always-ip-address = false',
          '# 仅解析代理节点自身的域名，不是网站查询的国内备用 DNS。',
          f'proxy-dns-server = {sr_bootstrap}',
          f'update-url = {ME}/shadowrocket.conf', '',
          '[Proxy Group]', '# 默认直连；外区服务打不开时在 SR 首页切到 PROXY',
          '🍎 苹果服务 = select,DIRECT,PROXY', '', '[Rule]']
    for r in cfg:
        sr.append(f"# {r['label']}")
        sr += [f'{t},{u},{SR_POL[r["policy"]]}' for t, u, *_ in sources(r)]
    sr += ['# 兜底', 'GEOIP,CN,DIRECT', 'FINAL,PROXY', '']
    (ROOT / 'shadowrocket.conf').write_text('\n'.join(sr))

    st = [hdr, 'name: Roy 统一分流规则',
          'desc: 统一分流 + MagicDNS / 直连域名国内 DoH / 默认 Cloudflare 经代理；升级见 README',
          '# 此文件仅供 Stash；Shadowrocket 的 DNS 在 shadowrocket.conf 中单独生成。',
          '# 合并版启用后关闭旧的「Roy DNS 经代理」本地覆写，避免重复。',
          '# MagicDNS 已合并；验证后关闭「Mini-Tailscale-MagicDNS」独立覆写。',
          '# DNS policy 按域名规则顺序匹配；Apple 按默认直连处理，不跟随策略组手动切换。',
          'dns:', '  follow-rule: true', '  skip-cert-verify: false',
          '  nameserver: #!replace']
    st += [f'    - {server}' for server in dns_servers]
    st += ['  # 清除基础配置的并发 fallback，避免旁路查询。',
           '  fallback: #!replace', '    []',
           '  # 完全替换旧 policy，防止继承的精确域名策略优先于本仓库集合。',
           '  nameserver-policy: #!replace']
    st += ['    # 具体 tailnet 域名优先于下方业务集合，避免交给公共 DNS。',
           f"    '+.{suffix}':", f"      - {magicdns['nameserver']}"]
    for r in cfg:
        servers = direct_servers if r['policy'] in ('direct', 'apple') else dns_servers
        for _, _, sid, *_ in sources(r):
            st.append(f"    'rule-set:{sid}':")
            st += [f'      - {server}' for server in servers]
    st += ['  # 数组默认前插合并，保留基础配置已有的 Fake-IP 排除项。',
           '  fake-ip-filter:', f"    - '+.{suffix}'"]
    st += ['', f'# 规则顺序：DNS 服务器 IP 指定出口 → Stash 专用直连 → {order}', '',
          '# 注意：覆写不定义策略组。基础配置（VIRCS 自建 / WgetCloud 等机场订阅）里已有同名组，重复定义会报 duplicate proxy name',
          'rule-providers:']
    for r in cfg:
        for _, _, sid, beh, fmt, u in sources(r):
            st += [f'  {sid}:', f'    behavior: {beh}', f'    format: {fmt}', f'    url: {u}', '    interval: 86400']
    st += ['', '# 覆写的规则会插到基础配置的规则之前，并以 MATCH 结尾：基础配置自带的规则（比如机场订阅里的上万条）不会再生效',
           '# 基础配置必须定义这 4 个策略组：🚀 节点选择 / 🎯 全球直连 / 🍎 苹果服务 / 🐟 漏网之鱼', 'rules:']
    st += ['  # 必须先于所有业务规则和 MATCH，确保 DNS 不依赖兜底组选择']
    st += [f'  - {rule}' for rule in dns_rules]
    st += ['  # Tailscale 内网 / MagicDNS、控制连接、STUN 与常用端口；不修改系统路由']
    st += ['  - ' + connection_rule(rule) for rule in tailnet_rules + direct_rules]
    for r in cfg:
        st.append(f"  # {r['label']}")
        st += [f'  - RULE-SET,{sid},{ST_POL[r["policy"]]}' for _, _, sid, *_ in sources(r)]
    st += ['  # 兜底', '  - GEOIP,CN,🎯 全球直连', '  - MATCH,🐟 漏网之鱼', '']
    (ROOT / 'stash.stoverride').write_text('\n'.join(st))
    for profile, config in profiles.items():
        proxy_name = f'Roy-Tailscale-{profile}'
        replacements = {'  - ' + connection_rule(rule):
                        '  - ' + connection_rule(rule, proxy_name) for rule in tailnet_rules}
        variant = [replacements.get(line, line) for line in st]
        variant[variant.index('name: Roy 统一分流规则')] = f'name: Roy 统一分流规则 · {profile}'
        variant[variant.index('dns:'):variant.index('dns:')] = [
            f'# 完整设备版，仅适用于 Tailscale 接口为 {config["interface-name"]} 的 {profile}。',
            '# 只启用此完整版本；关闭通用版与临时 MagicDNS / 接口绑定覆写，不依赖排序。',
            '# 重启或重连后请核对接口编号；不自动修改系统 DNS、路由或 Tailscale 开关。',
            'proxies:', f'  - name: {proxy_name}', '    type: direct',
            f'    interface-name: {config["interface-name"]}', '    benchmark-disabled: true', '']
        (ROOT / f'stash-{profile}.stoverride').write_text('\n'.join(variant))
    print('built: ' + ', '.join(generated_files(settings)))

if __name__ == '__main__':
    main()
