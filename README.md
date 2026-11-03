# proxy-rules

Roy 的 Stash（桌面）与 Shadowrocket（手机）统一分流规则。两端引用同一批业务规则源；DNS 设置按客户端分别管理。

> **2026-11-03：两端 DNS 分别更新。** Stash 常规 DNS 经「🚀 节点选择」访问 Cloudflare；Shadowrocket 的常规/直连/备用 DNS 使用 `#proxy` 经首页所选节点，代理域名保留远端解析。国内 CDN 图片、下载或视频可能变慢。Shadowrocket 以 **2.2.93** 为目标，尚待 iPhone/iPad 实机验收；其他设备拉取前请阅读各自的升级说明。

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

两端都从本仓库拉业务规则；DNS 分别由 `stash_dns` / `shadowrocket_dns` 生成，不能互相导入对方的配置文件：

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
4. 已有用户继续拉取相同 Stash URL 即可，不需要另装第二份 DNS 覆写。Shadowrocket 另按下节更新；若 CDN 缓存尚未刷新，稍后更新或使用上方缓存刷新地址。

### 回退

需要恢复合并前“仅业务分流”的远程覆写时，可临时改用固定版本：
`https://cdn.jsdelivr.net/gh/haoyan-yam/proxy-rules@036043f91d0ca4156ba802ca0361b9461995485f/stash.stoverride`

只启用一份统一分流覆写，不要新旧并行。旧版会重新继承基础配置 DNS，原有泄露风险也可能回来；若要恢复为此前的双覆写方案，可同时恢复原来的本地 DNS 覆写，并验证其两条规则位于兜底规则之前。固定版本不会收到后续覆写更新。

参考：[Stash DNS 文档](https://stash.wiki/features/dns-server)、[覆写合并规则](https://stash.wiki/configuration/override)。

## Shadowrocket 2.2.93：iPhone / iPad

### DNS 行为

- `dns-server`、`direct-dns-server`、`fallback-dns-server` 都使用 `https://1.1.1.1/dns-query#proxy` 与 `https://1.0.0.1/dns-query#proxy`。`#proxy` 指首页默认节点，不是名为「🚀 节点选择」的 Stash 策略组，也不固定国家。
- `dns-direct-system = false`；备用 DNS 显式填写代理 DoH，不再填写 `system`，也不留空。两个上游和备用均依赖代理可用，代理失效时国内域名也可能无法解析；这里没有自动降级到国内网站 DNS。
- `always-ip-address = false` 保留代理域名由远端解析的机制。因此**不能保证检测网站只显示 Cloudflare**：代理服务器所用的解析器也可能出现。本配置与 Stash 的隐私目标一致，但解析机制并不相同。
- 节点域名通过 `proxy-dns-server` 单独使用 `https://223.5.5.5/dns-query`、`https://223.6.6.6/dns-query` 引导，不附加 `#proxy`，避免循环依赖。AliDNS 因而可以看到节点域名；这不是把普通网站查询交给国内 DNS。使用 IP 节点时无需这一步域名解析。
- 业务分流、节点管理、Apple 默认直连、IPv6 和旁路设置保持原有配置。直连网站的 DNS 仍可能受到境外 CDN 调度影响；本次没有启用国内网站 DNS 分流。

### 更新步骤（两台设备分别检查）

1. 更新前保留现用配置副本。已有配置使用下列同一订阅地址时，在「配置」页面更新该远程配置；更新节点订阅不能替代更新配置。
   `https://cdn.jsdelivr.net/gh/haoyan-yam/proxy-rules@main/shadowrocket.conf`
2. 将更新后的配置设为当前使用项，首页「全局路由」选择「配置」，选择一个可用节点。无需导入 Stash 的 `.stoverride`，也无需把节点密码写入仓库。
3. 在配置预览/纯文本中核对上述三个 DNS 项均带 `#proxy`、备用项没有 `system`、`proxy-dns-server` 单独存在；检查额外模块、Host 指定 DNS 或本地自定义设置是否覆盖它们。
4. 在方便短暂断网时重新连接**该设备上的 Shadowrocket**，再分别检查网页、飞书图片和 DNS 日志。iPhone 可分别测试 Wi-Fi 与蜂窝数据，iPad 测试实际使用的网络；不需要关闭 Mac 上的 Stash。
5. 测试前若启用了 iCloud Private Relay/其他 DNS 描述文件，应记录其状态并区分来源，不要仅凭 DNS 服务器国家旗帜下结论。

### 验证边界与回退

已通过生成一致性、DNS 配置约束、规则源下载及业务分流回归检查；这不是 Shadowrocket 内核的解析测试，也不是 iOS/iPadOS 实测。2.2.93 为用户提供的目标版本；默认解析、旁路流量、App 自带加密 DNS、模块及其他系统设置仍需在设备上核对，不能承诺所有场景零泄露。

如果新配置导致网络异常，可切回保存的旧配置，或临时使用更新前固定版本：
`https://cdn.jsdelivr.net/gh/haoyan-yam/proxy-rules@d556e68395f1b4031dae964d93527bf1115f3442/shadowrocket.conf`

该版本仍采用国内 DNS 和系统备用 DNS，原有风险也会恢复。旧文件内 `update-url` 指向 main，如需停留在旧版，应在本地副本中改成上述固定版本 URL 或禁用该副本自动更新；固定版本不会收到后续修复。

配置语法参考：[官方群组关键词整理手册（非官方项目）](https://github.com/LOWERTOP/Shadowrocket#dns-over-proxy)、[其配置原文](https://github.com/LOWERTOP/Shadowrocket/blob/main/lazy.conf)。版本能力参考：[Shadowrocket 官方更新频道](https://t.me/s/ShadowrocketNews?before=1642)。

## 改什么文件

| 想改的 | 改哪里 | 之后 |
|---|---|---|
| 加/删某个域名、IP | `rules/personal_*.list` | `python3 scripts/check.py`，然后 push |
| 规则顺序、公共规则集、策略 | `rulesets.yaml` | `python3 scripts/build.py`，再 `check.py`，然后 push |
| Stash 常规 DNS 上游 | `rulesets.yaml` 的 `stash_dns` | 同步更新 `scripts/check.py` 的 DNS 回归期望，运行 build/check；仅更新 Stash 覆写 |
| Shadowrocket 网站 / 节点 DNS | `rulesets.yaml` 的 `shadowrocket_dns` | 同步更新 DNS 回归期望和 README，运行 build/check；iPhone/iPad 分别更新配置并验收 |
| 节点 | 各客户端本地 | 不经过仓库 |

push 后 GitHub Actions 会自动校验并刷新 jsDelivr 缓存。完整约定见 [AGENTS.md](AGENTS.md)。
