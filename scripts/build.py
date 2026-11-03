#!/usr/bin/env python3
"""从 rulesets.yaml 生成 shadowrocket.conf 和 stash.stoverride。用法：python3 scripts/build.py"""
import pathlib, yaml
from ipaddress import ip_address
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

def main():
    settings = yaml.safe_load((ROOT / 'rulesets.yaml').read_text())
    cfg = settings['rulesets']
    dns_servers = settings['stash_dns']['nameservers']
    if not dns_servers or len(dns_servers) != len(set(dns_servers)):
        raise ValueError('stash_dns.nameservers 不能为空或重复')
    dns_rules = []
    for server in dns_servers:
        url = urlsplit(server)
        if url.scheme != 'https' or url.username or url.password or not url.path:
            raise ValueError('Stash DNS 必须使用不含凭证的 HTTPS URL')
        ip = ip_address(url.hostname)  # 必须为 IP，不能依赖 DNS 解析自身
        kind = 'IP-CIDR' if ip.version == 4 else 'IP-CIDR6'
        dns_rules.append(f'{kind},{ip}/{ip.max_prefixlen},🚀 节点选择,no-resolve')
    order = ' → '.join(r['label'] for r in cfg) + ' → GEOIP CN 直连 → 其余走代理'
    hdr = '# 自动生成：改 rulesets.yaml 后运行 scripts/build.py，不要手改本文件\n'

    sr = [hdr, f'# 规则顺序：{order}', '[General]',
          'ipv6 = false', 'bypass-system = true',
          'skip-proxy = 192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12, fe80::/10, fc00::/7, localhost, *.local, *.lan, *.internal, e.crashlytics.com, captive.apple.com, sequoia.apple.com, seed-sequoia.siri.apple.com, *.ls.apple.com',
          'bypass-tun = 10.0.0.0/8,100.64.0.0/10,127.0.0.0/8,169.254.0.0/16,172.16.0.0/12,192.0.0.0/24,192.0.2.0/24,192.88.99.0/24,192.168.0.0/16,198.18.0.0/15,198.51.100.0/24,203.0.113.0/24,233.252.0.0/24,224.0.0.0/4,255.255.255.255/32,::1/128,::ffff:0:0/96,::ffff:0:0:0/96,64:ff9b::/96,64:ff9b:1::/48,100::/64,2001::/32,2001:20::/28,2001:db8::/32,2002::/16,3fff::/20,5f00::/16,fc00::/7,fe80::/10,ff00::/8',
          'dns-server = https://dns.alidns.com/dns-query, https://doh.pub/dns-query',
          'fallback-dns-server = system',
          f'update-url = {ME}/shadowrocket.conf', '',
          '[Proxy Group]', '# 默认直连；外区服务打不开时在 SR 首页切到 PROXY',
          '🍎 苹果服务 = select,DIRECT,PROXY', '', '[Rule]']
    for r in cfg:
        sr.append(f"# {r['label']}")
        sr += [f'{t},{u},{SR_POL[r["policy"]]}' for t, u, *_ in sources(r)]
    sr += ['# 兜底', 'GEOIP,CN,DIRECT', 'FINAL,PROXY', '']
    (ROOT / 'shadowrocket.conf').write_text('\n'.join(sr))

    st = [hdr, 'name: Roy 统一分流规则',
          'desc: 统一分流 + Cloudflare DNS 经节点选择（含国内域名）；国内 CDN 可能变慢，更新前阅读仓库 README',
          '# DNS 行为仅适用于 Stash；Shadowrocket 继续使用原有 DNS。',
          '# 合并版启用后关闭旧的「Roy DNS 经代理」本地覆写，避免重复。',
          '# 常规 DNS 走当前选中节点，不固定国家；国内网站连接仍按下方规则分流。',
          'dns:', '  follow-rule: true', '  skip-cert-verify: false',
          '  nameserver: #!replace']
    st += [f'    - {server}' for server in dns_servers]
    st += ['', f'# 规则顺序：DNS 服务器 IP 经代理 → {order}', '',
          '# 注意：覆写不定义策略组。基础配置（VIRCS 自建 / WgetCloud 等机场订阅）里已有同名组，重复定义会报 duplicate proxy name',
          'rule-providers:']
    for r in cfg:
        for _, _, sid, beh, fmt, u in sources(r):
            st += [f'  {sid}:', f'    behavior: {beh}', f'    format: {fmt}', f'    url: {u}', '    interval: 86400']
    st += ['', '# 覆写的规则会插到基础配置的规则之前，并以 MATCH 结尾：基础配置自带的规则（比如机场订阅里的上万条）不会再生效',
           '# 基础配置必须定义这 4 个策略组：🚀 节点选择 / 🎯 全球直连 / 🍎 苹果服务 / 🐟 漏网之鱼', 'rules:']
    st += ['  # 必须先于所有业务规则和 MATCH，确保 DNS 不依赖兜底组选择']
    st += [f'  - {rule}' for rule in dns_rules]
    for r in cfg:
        st.append(f"  # {r['label']}")
        st += [f'  - RULE-SET,{sid},{ST_POL[r["policy"]]}' for _, _, sid, *_ in sources(r)]
    st += ['  # 兜底', '  - GEOIP,CN,🎯 全球直连', '  - MATCH,🐟 漏网之鱼', '']
    (ROOT / 'stash.stoverride').write_text('\n'.join(st))
    print('built: shadowrocket.conf, stash.stoverride')

if __name__ == '__main__':
    main()
