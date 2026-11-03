# proxy-rules

Roy 的 Stash（桌面）与 Shadowrocket（手机）统一分流规则。两端引用同一批业务规则源；DNS 设置按客户端分别管理。

> **2026-11-03：Stash 覆写现已包含 DNS。** 更新 `stash.stoverride` 后，常规 DNS 会经「🚀 节点选择」访问 Cloudflare，包括国内域名。国内 CDN 图片、下载或视频可能变慢。Shadowrocket 配置不变。其他设备拉取前请阅读下方升级说明。

## 业务规则顺序（两端一致）

Stash 在这些业务规则之前另有两条 DNS 服务器 IP 规则：`1.1.1.1/32`、`1.0.0.1/32` → `🚀 节点选择`，均带 `no-resolve`。它们也会影响发往这两个 IP 的其他连接，不仅限于 DNS。

| # | 规则集 | 策略 | 来源 |
|---|---|---|---|
| 1 | Lan | 直连 | blackmatrix7 |
| 2 | 个人直连 `rules/personal_direct.list` | 直连 | 本仓库 |
| 3 | 个人代理 `rules/personal_proxy.list` | 代理 | 本仓库 |
| 4 | OpenAI / Claude / Gemini | 代理 | blackmatrix7 |
| 5 | Apple News | 代理 | blackmatrix7 |
| 6 | Apple | 🍎 苹果服务（默认直连，可切到代理） | blackmatrix7 |
| 7 | Global | 代理 | blackmatrix7 |
| 8 | China | 直连 | blackmatrix7 |
| 9 | GEOIP CN | 直连 | — |
| 10 | 其余 | 代理 | — |

## 下载源

- 本仓库文件走 jsDelivr（国内可直连，保证首次加载能拉到个人规则）。
- blackmatrix7 规则走 raw.githubusercontent.com：jsDelivr 对超过 50MB 的仓库会返回 403。`githubusercontent.com` 已写进个人代理规则，所以这些更新会走代理。

## 日常维护

- 只改 `rules/personal_direct.list` 和 `rules/personal_proxy.list`。每行一条，不写策略，IP 段加 `,no-resolve`。
- 推送后 GitHub Actions 会自动刷新 jsDelivr 缓存。如果 Actions 没跑，可以手动打开下面的地址刷新：
  - https://purge.jsdelivr.net/gh/haoyan-yam/proxy-rules@main/rules/personal_direct.list
  - https://purge.jsdelivr.net/gh/haoyan-yam/proxy-rules@main/rules/personal_proxy.list
  - https://purge.jsdelivr.net/gh/haoyan-yam/proxy-rules@main/shadowrocket.conf
  - https://purge.jsdelivr.net/gh/haoyan-yam/proxy-rules@main/stash.stoverride

## 客户端

两端都从本仓库拉业务规则；以下 Stash DNS 变更不会同步到 Shadowrocket：

- **Shadowrocket**：配置 → 添加 `https://cdn.jsdelivr.net/gh/haoyan-yam/proxy-rules@main/shadowrocket.conf`，设为默认。整份配置走云端更新；节点在 SR 里单独管理。
- **Stash**：基础配置（自建 VIRCS 配置或 WgetCloud 等机场订阅）+ 在「覆写」里从 URL 安装 `https://cdn.jsdelivr.net/gh/haoyan-yam/proxy-rules@main/stash.stoverride`。覆写接管全部分流规则及下述 DNS 字段；基础配置仍提供节点、4 个策略组（🚀 节点选择 / 🎯 全球直连 / 🍎 苹果服务 / 🐟 漏网之鱼）及其他未覆盖设置。更换基础配置后需重新检查 DNS 继承项。

## Stash DNS：行为、限制与升级

### 当前方案

- `nameserver: #!replace` 完全替换基础配置的常规 DNS 列表，仅使用 `https://1.1.1.1/dns-query` 和 `https://1.0.0.1/dns-query`。不能去掉 `#!replace`，否则可能与原来的国内或明文 DNS 并发查询。
- `follow-rule: true`，两条 DNS IP 规则排在所有业务规则和 `MATCH` 之前，明确经「🚀 节点选择」出站；`skip-cert-verify: false` 保留证书验证。
- DNS 出口跟随当前节点，**不固定在美国**。应在「🚀 节点选择」里选可用代理；选择 DIRECT 就不会获得代理 DNS 出口。代理故障时，不能假设国内网站仍可正常解析。
- 国内网站命中直连规则后，网站连接仍直连，但它的常规 DNS 查询也走代理。本版本**没有加入国内域名 DNS 分流**。

### 国内访问速度的取舍

境外解析可能返回不适合本地网络的 CDN 地址。2026-11-03 在上海网络对飞书公开页面的两张约 0.8 MB 图片做过临时指定地址的对照：Cloudflare 经当时代理出口返回的地址约需 10–12 秒，国内 DNS 返回的地址约需 0.06–0.10 秒。该结果仅是当次网络样本，不是普遍测速承诺；差异主要发生在图片传输阶段，不只是 DNS 查询等待。

若更重视国内访问体验，可以另行设计国内域名 `nameserver-policy` + 国内加密 DNS 直连。本次合并未启用此策略，请勿把“所有 DNS 经代理”理解为适合所有网络的默认最优方案。

### 继承项与兼容性

- 已在 **Stash macOS 4.3.5** 验证当前行为；其他版本或平台需先确认支持 `follow-rule` 和 `#!replace`。本仓库不宣称已覆盖所有客户端测试。
- 此覆写只设置上述三个 DNS 字段。基础配置中的 `nameserver-policy`、`fallback`、`default-nameserver`、`proxy-server-nameserver`、Fake-IP 和 IPv6 等未被清空或统一配置；其他启用的覆写也可能改变最终结果。
- 特别是继承的 `nameserver-policy` / `fallback` 可能让部分查询使用其他 DNS；Bootstrap 和代理节点域名解析也有独立用途，不能把本覆写当作所有 DNS 都不泄露的保证。
- 本次验证的节点服务器地址均为 IP，DNS 上游也直接使用 IP。若其他设备使用域名节点，请保证节点域名有独立、可用的引导解析，避免代理与 DNS 相互依赖。不要未经检查就把引导 DNS 也强制走代理。
- 本仓库不包含订阅地址、节点密码或设备控制密钥。节点和策略组继续在各客户端本地管理。

### 已使用旧本地 DNS 覆写的设备

1. 在 Stash 更新远程「Roy 统一分流规则」覆写，确认预览中出现 `dns:` 和最前面的两条 DNS IP 规则。
2. 关闭旧的「Roy DNS 经代理」本地覆写，仅保留合并后的统一覆写；可暂时保留旧文件用于回退。
3. 检查最终生效配置及实际访问。不要只依据“更新成功”提示或 DNS 检测网站的国家旗帜判断。
4. 此次无需更新 Shadowrocket。已有用户继续拉取相同 Stash URL 即可，不需要另装第二份 DNS 覆写。若 CDN 缓存尚未刷新，稍后更新或使用上方缓存刷新地址。

### 回退

需要恢复合并前“仅业务分流”的远程覆写时，可临时改用固定版本：
`https://cdn.jsdelivr.net/gh/haoyan-yam/proxy-rules@036043f91d0ca4156ba802ca0361b9461995485f/stash.stoverride`

只启用一份统一分流覆写，不要新旧并行。旧版会重新继承基础配置 DNS，原有泄露风险也可能回来；若要恢复为此前的双覆写方案，可同时恢复原来的本地 DNS 覆写，并验证其两条规则位于兜底规则之前。固定版本不会收到后续覆写更新。

参考：[Stash DNS 文档](https://stash.wiki/features/dns-server)、[覆写合并规则](https://stash.wiki/configuration/override)。

## 改什么文件

| 想改的 | 改哪里 | 之后 |
|---|---|---|
| 加/删某个域名、IP | `rules/personal_*.list` | `python3 scripts/check.py`，然后 push |
| 规则顺序、公共规则集、策略 | `rulesets.yaml` | `python3 scripts/build.py`，再 `check.py`，然后 push |
| Stash 常规 DNS 上游 | `rulesets.yaml` 的 `stash_dns` | 同步更新 `scripts/check.py` 的 DNS 回归期望，运行 build/check；仅更新 Stash 覆写 |
| 节点 | 各客户端本地 | 不经过仓库 |

push 后 GitHub Actions 会自动校验并刷新 jsDelivr 缓存。完整约定见 [AGENTS.md](AGENTS.md)。
