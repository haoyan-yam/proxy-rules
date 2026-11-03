# proxy-rules

Roy 的 Stash（桌面）与 Shadowrocket（手机）统一分流规则。两端引用同一批业务规则源；直连域名使用国内 AliDNS DoH，默认 DNS 使用 Cloudflare DoH 经代理。两端按各自语法生成。

> **2026-11-03：启用国内／默认 DNS 分流。** 本次替代此前“直连域名也经代理解析”的方案，用于改善飞书等国内 CDN 访问。Stash 需 macOS 4.3+ / iOS 3.6+；Shadowrocket 以 **2.2.93** 为目标。配置和规则检查不等于设备实测；其他设备更新前请阅读下方行为差异、升级步骤与回退说明。

## 业务规则顺序（两端一致）

Stash 在业务规则之前有四条 DNS 服务器 IP 规则：Cloudflare `1.1.1.1/32`、`1.0.0.1/32` → `🚀 节点选择`；AliDNS `223.5.5.5/32`、`223.6.6.6/32` → `DIRECT`。均带 `no-resolve`，也会影响发往这四个 IP 的其他连接。

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

两端都从本仓库拉业务规则；国内上游由 `direct_dns` 共用，其他 DNS 分别由 `stash_dns` / `shadowrocket_dns` 生成，不能互相导入对方的配置文件：

- **Shadowrocket**：配置 → 添加 `https://cdn.jsdelivr.net/gh/haoyan-yam/proxy-rules@main/shadowrocket.conf`，设为默认。整份配置走云端更新；节点在 SR 里单独管理。
- **Stash**：基础配置（自建 VIRCS 配置或 WgetCloud 等机场订阅）+ 在「覆写」里从 URL 安装 `https://cdn.jsdelivr.net/gh/haoyan-yam/proxy-rules@main/stash.stoverride`。覆写接管全部分流规则及下述 DNS 字段；基础配置仍提供节点、4 个策略组（🚀 节点选择 / 🎯 全球直连 / 🍎 苹果服务 / 🐟 漏网之鱼）及其他未覆盖设置。更换基础配置后需重新检查 DNS 继承项。

## Stash DNS：行为、限制与升级

### 当前方案与边界

| 用途 | DNS | 查询出口 |
|---|---|---|
| 命中直连域名集合（如飞书、国内网站） | `https://223.5.5.5/dns-query`、`https://223.6.6.6/dns-query` | 直连 |
| 命中代理域名集合或未命中任何域名集合 | `https://1.1.1.1/dns-query`、`https://1.0.0.1/dns-query` | 🚀 节点选择 |
| Apple 域名集合 | 国内 AliDNS DoH | 直连，与 Apple 默认直连一致 |

- `nameserver-policy` 引用现有规则集合，按业务规则顺序生成；代理集合也明确列入，避免被后面的 China 集合覆盖。只依据集合中的域名条目判断，不把 IP/GEOIP 规则转换成域名规则。**只有解析后才命中国内 IP 的域名，仍可能使用默认 Cloudflare。**
- **DNS policy 不跟随策略组的手动选择。** Apple 按默认直连配置；如把 Apple 或「🎯 全球直连」切到代理，其 DNS 仍使用国内服务器。若要求这些域名的解析也经代理，需同步调整 DNS policy。将代理组切到 DIRECT 也会改变默认 DNS 的出口。
- `nameserver`、`nameserver-policy`、`fallback` 均用 `#!replace`：替换默认解析器和整个域名策略，清空基础配置的并发 fallback。已有公司内网等自定义 DNS policy 会被替换，需要显式补回；不要把内网域名交给公共 DNS 解析器并期待可用。
- `follow-rule: true` 配合最前面的四条 IP 规则控制 DNS 出口；`skip-cert-verify: false` 保留证书验证。国内 DNS 故障时，本 Stash 方案没有自动切到 Cloudflare 的备用链路。
- 国内解析器会看到交给它的域名和直连出口 IP。这是主动选择的分流，不意味着所有 DNS 都对国内不可见。代理域名意外送到国内、系统 DNS 或 App 自带 DNS 绕过预期路径，才需要按泄露问题排查。DoH 加密传输不代表对 DNS 服务商匿名。

### 国内访问速度

境外解析可能返回不适合本地网络的 CDN 地址。此前在上海网络对飞书公开页面两张约 0.8 MB 图片的临时指定地址对照中，Cloudflare 经当时代理出口返回的地址约需 10–12 秒，国内 DNS 返回的地址约需 0.06–0.10 秒。这只是当次网络样本，不是速度承诺，也不能代表 iPhone 群聊图片的实测。

本次将飞书等直连域名交给国内解析器，目的是改善 CDN 地址选择。客户端和 App 的 DNS、连接、图片缓存可能继续使用旧结果；需更新配置后重新测试。不要仅凭 DNS 检测网站的国家旗帜判断是否生效或泄露。

### 兼容性与继承项

- `rule-set:` DNS policy 要求 **Stash macOS 4.3+ / iOS 3.6+**。本机版本为 macOS 4.3.5；本次新增分流仍须检查设备实际加载与解析结果，不能把静态测试称为内核实测。旧版设备先升级再拉取。
- 基础配置的 `default-nameserver`、`proxy-server-nameserver`、Hosts、Fake-IP、IPv6 等继续继承，其他覆写也可能再次改写 DNS。更换基础配置后仍需检查。
- 使用域名节点时，应保证独立可用的节点引导解析，避免代理与 DNS 循环依赖；本次不统一更改这些引导项。本机此前核验的节点地址为 IP。
- 节点、策略组、业务规则顺序保持原状；仓库不包含订阅凭证、节点密码、设备密钥或个人日志。

### 更新步骤

1. 在 Stash 更新同一个「Roy 统一分流规则」远程覆写。预览应有 `nameserver-policy`、空 `fallback` 和最前面的四条 DNS IP 规则。
2. 如果还启用了旧的「Roy DNS 经代理」本地覆写，将其关闭，仅保留合并后的统一覆写；无需再安装第二份 DNS 覆写。
3. 检查最终生效配置，再测试飞书图片及常用代理网站。**不需要退出 Mac Stash**。其他设备各自更新；GitHub 发布不等于设备已经应用。
4. 若 CDN 尚未刷新，稍后更新或使用上方缓存刷新地址。公司内网使用者先核对自定义 DNS 策略。

### 回退

恢复此前“直连域名也使用 Cloudflare 经代理解析”的版本：
`https://cdn.jsdelivr.net/gh/haoyan-yam/proxy-rules@85521486fdf4b967a21de6c39007670818fe331a/stash.stoverride`

只启用一份统一覆写。旧版会重新继承基础配置的 DNS policy/fallback，国内 CDN 变慢也可能恢复；回退后仍需检查最终配置。固定版本不会收到后续更新。

参考：[Stash DNS 文档](https://stash.wiki/features/dns-server)、[覆写合并规则](https://stash.wiki/configuration/override)。

## Shadowrocket 2.2.93：iPhone / iPad

### DNS 行为

- `direct-dns-server` 使用国内 `https://223.5.5.5/dns-query`、`https://223.6.6.6/dns-query`，**不加 `#proxy`**，用于命中直连域名规则的解析。
- `dns-server` 和 `fallback-dns-server` 使用 Cloudflare 两个 IP 形式 DoH 地址，均带 `#proxy`，通过首页所选节点。直连 DNS 失败时可使用该备用；代理故障时备用也不可用。不填写 `system`，不留空备用，`dns-direct-system = false`。
- `always-ip-address = false` 保留代理域名由节点远端解析。**默认 DNS 配为 Cloudflare 不等于所有代理域名都由 Cloudflare 解析**；IP 规则判断所需的本地解析使用默认 DNS。与 Stash 统一的是分流目标，不是全部内核行为。
- `proxy-dns-server` 独立使用 AliDNS IP 形式 DoH 引导节点域名，不加 `#proxy`，避免循环。AliDNS 可看到这些节点域名；IP 节点无需这一步。
- 业务规则、Apple 默认直连、节点管理、IPv6 和旁路配置保持原状。App 自带 DNS、系统旁路或其他模块仍可能不遵循这些设置。

### 更新步骤（两台设备分别检查）

1. 更新前保留现用配置副本。已有配置使用下列同一订阅地址时，在「配置」页面更新该远程配置；更新节点订阅不能替代更新配置。
   `https://cdn.jsdelivr.net/gh/haoyan-yam/proxy-rules@main/shadowrocket.conf`
2. 将更新后的配置设为当前使用项，首页「全局路由」选择「配置」，选择一个可用节点。无需导入 Stash 的 `.stoverride`，也无需把节点密码写入仓库。
3. 在配置预览/纯文本中核对默认与备用 DNS 带 `#proxy`，直连 DNS 为 AliDNS 且不带 `#proxy`；备用项没有 `system`、`proxy-dns-server` 单独存在；检查额外模块、Host 指定 DNS 或本地自定义设置是否覆盖它们。
4. 在方便短暂断网时重新连接**该设备上的 Shadowrocket**，再分别检查网页、飞书图片和 DNS 日志。iPhone 可分别测试 Wi-Fi 与蜂窝数据，iPad 测试实际使用的网络；不需要关闭 Mac 上的 Stash。
5. 测试前若启用了 iCloud Private Relay/其他 DNS 描述文件，应记录其状态并区分来源，不要仅凭 DNS 服务器国家旗帜下结论。

### 验证边界与回退

验证包含生成一致性、DNS 配置约束、规则源下载、业务分流及 Stash 域名 DNS 分流回归检查；这不是 Shadowrocket 内核的解析测试，也不是 iOS/iPadOS 实测。2.2.93 为用户提供的目标版本；默认解析、旁路流量、App 自带加密 DNS、模块及其他系统设置仍需在设备上核对，不能承诺所有场景零泄露。

如果新配置导致网络异常，可切回保存的旧配置，或临时使用更新前固定版本：
`https://cdn.jsdelivr.net/gh/haoyan-yam/proxy-rules@85521486fdf4b967a21de6c39007670818fe331a/shadowrocket.conf`

该版本将直连域名也交给 Cloudflare 经代理解析，国内 CDN 变慢可能恢复。旧文件内 `update-url` 指向 main，如需停留在旧版，应在本地副本中改成上述固定版本 URL 或禁用该副本自动更新；固定版本不会收到后续修复。

配置语法参考：[官方群组关键词整理手册（非官方项目）](https://github.com/LOWERTOP/Shadowrocket#dns-over-proxy)、[其配置原文](https://github.com/LOWERTOP/Shadowrocket/blob/main/lazy.conf)。版本能力参考：[Shadowrocket 官方更新频道](https://t.me/s/ShadowrocketNews?before=1642)。

## 改什么文件

| 想改的 | 改哪里 | 之后 |
|---|---|---|
| 加/删某个域名、IP | `rules/personal_*.list` | `python3 scripts/check.py`，然后 push |
| 规则顺序、公共规则集、策略 | `rulesets.yaml` | `python3 scripts/build.py`，再 `check.py`，然后 push |
| 两端直连 DNS 上游 | `rulesets.yaml` 的 `direct_dns` | 同步 DNS 回归期望和 README，运行 build/check；两端分别更新 |
| Stash 常规 DNS 上游 | `rulesets.yaml` 的 `stash_dns` | 同步更新 `scripts/check.py` 的 DNS 回归期望，运行 build/check；仅更新 Stash 覆写 |
| Shadowrocket 网站 / 节点 DNS | `rulesets.yaml` 的 `shadowrocket_dns` | 同步更新 DNS 回归期望和 README，运行 build/check；iPhone/iPad 分别更新配置并验收 |
| 节点 | 各客户端本地 | 不经过仓库 |

push 后 GitHub Actions 会自动校验并刷新 jsDelivr 缓存。完整约定见 [AGENTS.md](AGENTS.md)。
