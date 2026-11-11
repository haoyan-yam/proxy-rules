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

## Stash 与独立 Tailscale 客户端共存

### Mini 完整合并版：无需调整覆写顺序（2026-11-11）

Mini 上的实测发现：系统访问 Quad100 正常，Stash 普通 DIRECT 访问 Quad100 超时；单独接口测试覆写的规则落在统一版 MATCH 后，未能命中。因此新增一份由同一源文件生成的**完整设备版**，包含原有业务分流、MagicDNS 和指定接口出口：

`https://cdn.jsdelivr.net/gh/haoyan-yam/proxy-rules@main/stash-mini.stoverride`

1. 在 Mini 的 Stash「覆写」页面从上述 URL 安装「Roy 统一分流规则 · mini」。
2. 关闭原通用版「Roy 统一分流规则」、临时 MagicDNS、接口绑定测试和旧 DNS 覆写，只启用这一份完整版本。无需拖动排序。
3. 保持独立 Tailscale 运行、Use Tailscale DNS settings 关闭。核对生效规则：Quad100、自己的 tailnet 域名、`100.64.0.0/10` 和 `fd7a:115c:a1e0::/48` 应命中 `Roy-Tailscale-mini`，位于业务规则与 MATCH 前。
4. 检查 Stash 解析和系统解析返回真实 `100.x` 地址，再测试在线内网服务、普通国内网站和代理网站。仓库检查通过不代表设备已加载或访问已恢复。

`Roy-Tailscale-mini` 是无密码的 direct 出口，绑定本机 2026-11-11 确认的 Tailscale 接口 `utun10`。仅内层连接使用它；公网 `tailscale.com`、3478、41641 保留普通 DIRECT。公共 DNS 出口和所有业务规则继承通用版。本方案不修改系统 resolver、路由或 Tailscale 开关。

**此地址只给这台 Mini 使用。** 重启或重连后接口编号可能变化；若失效，用 `route -n get 100.100.100.100` 核对 `interface`，再更新 `rulesets.yaml` 的 `stash_interface_profiles.mini.interface-name` 并重新生成。其他 Mac 继续使用通用订阅，接口需各自确认。回退时停用 Mini 版、重新启用原通用版；这也会恢复普通 DIRECT 的已知限制。

本机验收（2026-11-11，Stash 4.3.5）：仅启用 Mini 完整版后，运行规则确认 Quad100 命中 `Roy-Tailscale-mini`；Stash 解析 API 从 Quad100 返回 Node 与 Muse 的真实内网地址，Node 服务通过域名、IP 和显式 Stash HTTP 代理均返回 HTTP 200，百度与 Google 返回 HTTP 200。系统 `dig` / `dscacheutil` 仍返回 Fake-IP，清理 Stash DNS 缓存后新查询也如此，不能归因于旧缓存。因此目前确认的是解析上游与实际访问恢复，**尚未确认应用侧真实 IP 返回**，不要以系统仍显示 `198.18.*` 单独判定访问失败。Muse SSH 端口另有拒绝连接现象，不在这次 DNS 修复的成功范围内。

语法参考：[Stash 指定接口的直连出口](https://stash.wiki/proxy-protocols/proxy-types#direct-with-specified-interface)。

### MagicDNS 已合并到统一覆写（2026-11-11）

适用于独立 Tailscale 客户端连接到 `tail2bea5.ts.net` 的 Mac。Tailscale 保持运行，客户端的 **Use Tailscale DNS settings 保持关闭**，tailnet 的 MagicDNS 保持开启；普通网站继续使用原有 Stash DNS 分流。

统一覆写直接包含 `+.tail2bea5.ts.net → 100.100.100.100` 的 `nameserver-policy`，并将该后缀加入 `fake-ip-filter`，用于获取真实内网地址；前提是 Stash 能访问 Quad100，Mini 的接口问题见上节。Fake-IP 排除列表使用数组合并，保留基础配置的其他排除项。只处理自己的 tailnet；共享设备使用其他后缀时需另行配置。该后缀来自 `rulesets.yaml` 的 `stash_dns.magicdns`。

此前单独启用「Mini-Tailscale-MagicDNS」并放在统一覆写之前，会被统一覆写的 `nameserver-policy: #!replace` 覆盖。合并后不再依赖两份覆写的顺序，也不应通过移除 `#!replace` 来继承其他未知 DNS policy。

更新步骤：

1. 更新现有「Roy 统一分流规则」远程覆写，URL 不变；确认预览及生效配置同时含上述 tailnet policy 和 Fake-IP 排除项。
2. 关闭临时的「Mini-Tailscale-MagicDNS」/「Mini Tailscale MagicDNS」覆写，仅保留统一覆写。不要停用独立 Tailscale 客户端。
3. 在 macOS 执行 `dscacheutil -q host -a name muse-1.tail2bea5.ts.net`，预期为 `100.83.152.73`，而非 `198.18.x.x`。若仍返回旧结果，先检查运行配置是否已加载，再按需清理 Stash 和系统 DNS 缓存。
4. 用 `dig @100.100.100.100 muse-1.tail2bea5.ts.net A` 检查 MagicDNS 本身，再分别验证在线设备的实际服务、普通国内网站及代理网站。解析成功不代表设备在线或业务端口可达。

关闭 Stash 时，以上 Stash policy 不再生效；若需要此时仍解析完整 tailnet 域名，可在该 Mac 单独配置 `/etc/resolver/tail2bea5.ts.net` 指向 `100.100.100.100` 并验证。短设备名的搜索域也需要额外配置。本仓库不写系统 resolver、不切换 DNS 开关、不修改路由。

本次合并前的 Mac 实测确认：Quad100 能返回内网地址，而旧 Stash policy 解析失败。仓库回归检查不等于合并后设备已加载或端到端访问已恢复。关闭接受 DNS 后，Quad100 对普通网站可能返回 SERVFAIL，不能将它设为全局上游，也不能据此推断开启接受 DNS 时的故障原因。

若需回退本次 MagicDNS 合并，可使用[合并前固定版本](https://cdn.jsdelivr.net/gh/haoyan-yam/proxy-rules@5043a4d28a163f499174e476d82a89bd8ead3f4e/stash.stoverride)。旧版本不包含 MagicDNS 分流，需要另行安排内网解析。不要依赖界面上下位置推断最终规则顺序，应检查运行配置。固定版本不会自动获得后续修复。

参考：[Tailscale 手动配置 MagicDNS](https://tailscale.com/docs/reference/faq/dns-resolv-conf)、[Stash DNS](https://stash.wiki/features/dns-server)。

### Tailscale 连接规则

Stash 统一覆写已包含以下固定直连规则，位于四条 DNS 服务器 IP 规则之后、所有业务规则之前：

```yaml
- IP-CIDR,100.100.100.100/32,DIRECT,no-resolve
- DOMAIN-SUFFIX,tail2bea5.ts.net,DIRECT
- IP-CIDR,100.64.0.0/10,DIRECT,no-resolve
- IP-CIDR6,fd7a:115c:a1e0::/48,DIRECT,no-resolve
- DOMAIN-SUFFIX,tailscale.com,DIRECT
- DST-PORT,3478,DIRECT
- DST-PORT,41641,DIRECT
```

这些规则让 tailnet 内层连接与 Quad100 固定直连，并避免 Tailscale 控制域名、STUN 和常用直连端口被通用代理规则接管。端口规则不限进程或协议，会让发往这两个目标端口的其他连接也直连；NAT 映射到其他端口的连接不由这两条端口规则覆盖。四条公共 DNS IP 规则仍具有更高优先级。内层 DIRECT 不保证外层 peer/DERP 连接直连，也不代表系统路由一定正确。

规则只在 Stash 生成，Shadowrocket 配置与两端共享个人列表保持不变。手机内置 Tailscale 与 Mac 独立客户端的处理方式不同，不将 Mac 的修复直接套到手机。

更新与验证：

1. 在每台 Mac 更新现有「Roy 统一分流规则」远程覆写，URL 不变。GitHub 发布不代表设备已加载。
2. 确认运行中的规则已包含上面七条，再关闭重复的「Mini Tailscale 直连测试」或「MacBook Air Tailscale 直连」本地覆写。验证前可先保留旧覆写；仅有文件预览不代表已有 UDP 会话已采用新规则。
3. 若使用 Stash TUN 与独立 Tailscale，检查目标 `100.x` 的系统路由是否交给 Tailscale。若「跳过 TUN」中的 `100.64.0.0/10` 导致它被送往物理网关，需在该设备单独修正；本覆写不会修改此设置。不要复制另一台 Mac 的 `utun` 编号或路由命令。
4. 可用公网 IPv6 有助于建立直连，但由实际网络提供；本覆写不启用路由器 IPv6、不强制中继地区，也不保证一定打洞成功。更新后测试 Tailscale 路径及常用国内/代理网站；需要重连时由设备使用者操作。

此前的三条控制域名/端口规则已在一台 Mac 与手机的场景中使用，IPv6 直连依赖另行启用的家中 IPv6。公司 Mac、其他网络及更新后的合并覆写仍需分别验收。回退本次规则合并可使用[更新前固定版本的 Stash 覆写](https://cdn.jsdelivr.net/gh/haoyan-yam/proxy-rules@1a3dc28802718f306bee57e58500a8bd75d2cfb7/stash.stoverride)；不要为撤回这三条规则改动手机配置或关闭已验证有效的路由修复。

## Stash DNS：行为、限制与升级

### 当前方案与边界

| 用途 | DNS | 查询出口 |
|---|---|---|
| `tail2bea5.ts.net` 及其子域名 | `100.100.100.100` | 本机独立 Tailscale 客户端 |
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
- 基础配置的 `default-nameserver`、`proxy-server-nameserver`、Hosts、Fake-IP 其他排除项、IPv6 等继续继承（本覆写仅增加 tailnet 的 Fake-IP 排除），其他覆写也可能再次改写 DNS。更换基础配置后仍需检查。
- 使用域名节点时，应保证独立可用的节点引导解析，避免代理与 DNS 循环依赖；本次不统一更改这些引导项。本机此前核验的节点地址为 IP。
- 节点、策略组、业务规则顺序保持原状；仓库不包含订阅凭证、节点密码、设备密钥或个人日志。

### 更新步骤

1. 在 Stash 更新同一个「Roy 统一分流规则」远程覆写。预览应有 `nameserver-policy`、空 `fallback` 和最前面的四条 DNS IP 规则。
2. 如果还启用了旧的「Roy DNS 经代理」本地覆写，将其关闭；同样关闭临时 MagicDNS 覆写，仅保留合并后的统一覆写；无需再安装第二份 DNS 覆写。
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
| Stash MagicDNS | `rulesets.yaml` 的 `stash_dns.magicdns` 与 `stash_tailnet_rules` | 同步 DNS/连接边界测试；仅更新 Stash 覆写并关闭临时 MagicDNS 覆写 |
| Mini 的 Tailscale 接口 | `rulesets.yaml` 的 `stash_interface_profiles.mini.interface-name` | 先核对本机接口，再生成并检查；仅更新 Mini 完整覆写 |
| Stash 常规 DNS 上游 | `rulesets.yaml` 的 `stash_dns` | 同步更新 `scripts/check.py` 的 DNS 回归期望，运行 build/check；仅更新 Stash 覆写 |
| Shadowrocket 网站 / 节点 DNS | `rulesets.yaml` 的 `shadowrocket_dns` | 同步更新 DNS 回归期望和 README，运行 build/check；iPhone/iPad 分别更新配置并验收 |
| 节点 | 各客户端本地 | 不经过仓库 |

push 后 GitHub Actions 会自动校验并刷新 jsDelivr 缓存。完整约定见 [AGENTS.md](AGENTS.md)。
