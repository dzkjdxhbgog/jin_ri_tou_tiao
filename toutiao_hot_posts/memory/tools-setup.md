# 工具与环境状态

## Mac 本机已安装
- Homebrew：✅ 已安装（2026-04-29）
- Node.js：✅ v25.9.0（via Homebrew）
- Bun：✅ v1.3.13（~/.bun/bin/bun）
- nvm：❌ 未安装（改用 Homebrew 安装 Node）

## claude-mem（跨会话记忆插件）
- 状态：⚠️ 部分安装
- 插件文件：`/Users/w7451/.claude/plugins/marketplaces/thedotmack/` ✅
- worker 自动启动：❌（需要 claude CLI 在 PATH 里才能注册 hooks）
- 替代方案：使用本 memory/ 目录做文件式记忆（当前方案）
- 如需完整安装：`npm install -g @anthropic-ai/claude-code` 后重新运行 `npx claude-mem install`

## Cowork 插件
- 当前无已安装插件（`list_plugins` 返回空）
- MCP 注册表搜索：无可用 memory MCP

## 已连接 MCP
- Claude in Chrome：✅（可控制浏览器）
- computer-use：✅（可截图/点击桌面，终端限 click 级别）
- workspace bash：✅（Linux 沙箱，仅可写 workspace 和 outputs）

## 应用访问权限
- Codex：✅ full 权限
- Google Chrome：✅ read 权限（需通过 Claude in Chrome MCP 操作）
- 终端：✅ click 权限（只能点击，不能输入）
