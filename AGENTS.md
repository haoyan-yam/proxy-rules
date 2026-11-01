# 维护说明（给 Claude 和其他 Agent）

本仓库是 Roy 的 Stash（Mac）和 Shadowrocket（iPhone）共用的分流规则。两端从这里拉规则，任何改动都会同时影响两台设备。

## 架构

```
rulesets.yaml ──scripts/build.py──▶ shadowrocket.conf   （SR 订阅整份配置）
                                └─▶ stash.stoverride    （Stash 覆写：规则集 + 规则）
rules/personal_direct.list  个人直连（两端共用）
rules/personal_proxy.list   个人代理（两端共用）
tests.yaml                  分流回归测试
```

- 公共规则集来自 blackmatrix7/ios_rule_script：SR 用 `rule/Shadowrocket/`，Stash 用 `rule/Clash/`，两者内容同源。
- Stash 的节点和全部策略组（🚀 节点选择 / 🎯 全球直连 / 🍎 苹果服务 / 🛑 广告拦截 / 🐟 漏网之鱼）在 Roy 本地的基础配置里，**不在本仓库**。覆写里**不要**定义 proxy-groups：Stash 会报 duplicate proxy name。需要新增策略组时，让 Roy 在本地基础配置里加，SR 那边在 build.py 的 [Proxy Group] 里加。基础配置的规则只有 `MATCH,🐟 漏网之鱼` 一条，覆写里的规则会插到它前面。
- 本仓库文件走 jsDelivr（国内可直连），blackmatrix7 走 raw.githubusercontent.com（jsDelivr 对超过 50MB 的仓库返回 403；`githubusercontent.com` 已经在个人代理规则里）。

## 改动流程

1. 判断改哪里：
   - 某个域名或 IP 该直连还是该代理 → 改 `rules/personal_direct.list` 或 `rules/personal_proxy.list`
   - 加减公共规则集、调整顺序、改策略 → 改 `rulesets.yaml`，然后运行 `python3 scripts/build.py`
   - **不要手改** `shadowrocket.conf` 和 `stash.stoverride`，这两个是生成的
2. 在 `tests.yaml` 里给这次改动加一条期望结果。
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
