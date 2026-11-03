# 维护说明（给 Claude 和其他 Agent）

本仓库是 Roy 的 Stash（Mac）和 Shadowrocket（iPhone / iPad）共用的业务分流规则。共享规则会影响两端；国内 DNS 由 direct_dns 共用，其他 DNS 按客户端分别生成。

处理本项目任务前，先读取并遵循：`~/.codex/AGENTS.md`（若该设备存在此文件）。`stash_dns` 只影响 Stash；`shadowrocket_dns` 只影响 Shadowrocket，不要将两端语法混用。

## 架构

```
rulesets.yaml ──scripts/build.py──▶ shadowrocket.conf   （SR 订阅整份配置）
                                └─▶ stash.stoverride    （Stash 覆写：DNS + 规则集 + 规则）
rules/personal_direct.list  个人直连（两端共用）
rules/personal_proxy.list   个人代理（两端共用）
tests.yaml                  业务分流回归测试
dns-tests.yaml              Stash 域名 DNS 分流回归测试
```

- 公共规则集来自 blackmatrix7/ios_rule_script：SR 用 `rule/Shadowrocket/`，Stash 用 `rule/Clash/`，两者内容同源。
- Stash 的节点和全部策略组在 Roy 本地的基础配置里，**不在本仓库**。基础配置可能是自建的 VIRCS 配置，也可能是机场订阅（比如 WgetCloud，ACL4SSR 风格，有自己的上万条规则）。覆写对基础配置的唯一要求：必须有 `🚀 节点选择`、`🎯 全球直连`、`🍎 苹果服务`、`🐟 漏网之鱼` 这 4 个策略组。
- 覆写**不要**定义 proxy-groups：WgetCloud 自带「🍎 苹果服务」，重复定义会报 duplicate proxy name。
- 覆写的规则会插到基础配置规则的前面，并且以 `MATCH,🐟 漏网之鱼` 结尾，所以基础配置自带的规则永远不会被用到。换机场、换基础配置都不影响分流结果。
- 当前 DNS 策略经 Roy 选择：直连域名用国内 AliDNS DoH，默认 Cloudflare DoH 经代理。`direct_dns` 影响两端；其他上游分别在 `stash_dns` / `shadowrocket_dns`。
- Stash `nameserver-policy` 按业务规则集合顺序生成，代理集合也需显式列入。nameserver、policy、空 fallback 必须保留 `#!replace`。DNS 服务器四条 IP 规则放在最前；不能新增节点/策略组，也不统一修改引导 DNS。
- Stash DNS policy 不跟随手动策略组选择：Apple 默认国内 DNS，切到代理时需另调 policy。IP/GEOIP 才能判断的域名仍使用默认 DNS。要求 macOS 4.3+ / iOS 3.6+；不能默默支持旧版本。
- Shadowrocket 目标 2.2.93：直连 DNS 为国内 DoH 不加 #proxy；默认/备用 Cloudflare 加 #proxy，节点 DNS 独立引导。保留代理域名远端解析，不能声称所有代理域名均由 Cloudflare 解析。备用不可留空，避免隐式系统 DNS。
- 测试脚本下载实际规则源做域名匹配检查，不模拟整个内核、IP/GEOIP 或手动组选择，不代替手机/Mac 实测。报告需区分仓库已发布、设备已加载与请求路径已验证。
- 国内解析器能看到直连域名与出口 IP，属于有意选择；不承诺全场景零泄露。继承 Hosts/bootstrap 等及其他覆写仍需检查；旧内网 DNS policy 会被替换，升级和回退见 README。
- 本仓库文件走 jsDelivr（国内可直连），blackmatrix7 走 raw.githubusercontent.com（jsDelivr 对超过 50MB 的仓库返回 403；`githubusercontent.com` 已经在个人代理规则里）。

## 改动流程

1. 判断改哪里：
   - 某个域名或 IP 该直连还是该代理 → 改 `rules/personal_direct.list` 或 `rules/personal_proxy.list`
   - 加减公共规则集、调整顺序、改策略 → 改 `rulesets.yaml`，然后运行 `python3 scripts/build.py`
   - 两端直连 DNS → 改 `direct_dns`，同步 README、两端字段检查及 dns-tests.yaml
   - Stash DNS → 改 `rulesets.yaml` 的 `stash_dns` / `scripts/build.py`，同步 README 与 `check.py` 的 DNS 回归期望；保持 Shadowrocket 输出不变
   - Shadowrocket DNS → 改 `shadowrocket_dns` / `scripts/build.py`，同步 README 与 DNS 检查；保持业务规则与 Stash 有效配置不变。发布后通知 iPhone/iPad 更新配置，并说明实机验收状态
   - **不要手改** `shadowrocket.conf` 和 `stash.stoverride`，这两个是生成的
2. 业务分流变动更新 `tests.yaml`；DNS 变动更新 `dns-tests.yaml` 和字段约束。
3. 运行 `python3 scripts/check.py`，必须全部通过。
4. commit 后 push 到 main。GitHub Actions 会再跑一遍校验，并刷新 jsDelivr 缓存。
5. 告诉 Roy 需要在哪一端点更新：
   - 只改了 `rules/*.list`：两端规则集每 24 小时自动更新，要立刻生效就在客户端里手动更新规则集
   - 改了 `rulesets.yaml`：SR 更新配置，Stash 更新覆写

## 规则约定

- `rules/*.list` 每行一条，**不写策略**。只允许 DOMAIN / DOMAIN-SUFFIX / DOMAIN-KEYWORD / IP-CIDR / IP-CIDR6。
- IP 规则必须带 `,no-resolve`。不带的话，Stash 和 SR 会对每个域名提前做 DNS 解析，还会把解析到该网段的无关网站一起导走。
- 慎用 DOMAIN-KEYWORD。像 `gle` 这种短关键词会误伤大量域名，原配置里就出过这个问题。
- 个人规则排在公共规则前面，冲突时以个人规则为准。用它来纠正 blackmatrix7 的判断，不要用来重复它已经覆盖的内容。
- 同一条目不能同时出现在直连和代理两个列表里（check.py 会拦下来）。

## 已做过的决定（改之前先问 Roy）

- 兜底策略：国内 IP 直连，其余走代理。
- Apple 默认直连。App Store 的区域看 Apple ID，不看 IP；外区服务打不开时，由 Roy 手动把「🍎 苹果服务」切到代理。
- 不做广告拦截。
- 富途用的腾讯云 IP 段保留在个人代理里（带 no-resolve），用于匹配富途 App 直接按 IP 发起的连接。
