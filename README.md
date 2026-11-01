# proxy-rules

Roy 的 Stash（桌面）与 Shadowrocket（手机）统一分流规则。两端引用同一批规则源，改一处、两端同步。

## 规则顺序（两端一致）

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

## 客户端

两端都从本仓库拉规则，改一次两端同步：

- **Shadowrocket**：配置 → 添加 `https://cdn.jsdelivr.net/gh/haoyan-yam/proxy-rules@main/shadowrocket.conf`，设为默认。整份配置走云端更新；节点在 SR 里单独管理。
- **Stash**：本地导入基础配置（只含节点和基础策略组，不入库），再在「覆写」里从 URL 安装 `https://cdn.jsdelivr.net/gh/haoyan-yam/proxy-rules@main/stash.stoverride`。规则集和规则顺序来自覆写；策略组（含「🍎 苹果服务」）在本地基础配置里。

## 改什么文件

| 想改的 | 改哪里 | 之后 |
|---|---|---|
| 加/删某个域名、IP | `rules/personal_*.list` | `python3 scripts/check.py`，然后 push |
| 规则顺序、公共规则集、策略 | `rulesets.yaml` | `python3 scripts/build.py`，再 `check.py`，然后 push |
| 节点 | 各客户端本地 | 不经过仓库 |

push 后 GitHub Actions 会自动校验并刷新 jsDelivr 缓存。完整约定见 [AGENTS.md](AGENTS.md)。
