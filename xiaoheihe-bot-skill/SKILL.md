---
name: xiaoheihe-bot
description: >
  小黑盒（游戏社区）自动发帖 / 评论 / 水贴 / 删帖 / 看帖工具。Agent 直接调用小黑盒 API。
  触发场景：用户提到小黑盒、发帖、水贴、刷评论、删帖、社区运营、自动回帖、帖子库。
  安装：先按 README 准备依赖（heibox-comment-bot + 扫码登录），再复制 config.example.json 为 config.json 填 hb_project_path。
---

# 小黑盒 Bot Skill

直接调小黑盒 API 的封装（发帖 / 评论 / 看热帖 / 看帖 / 删帖 / 水贴记录）。
内容由 Agent 自己写（社区风格、查证设定），不走外部 LLM。

## 依赖

1. **requests**（唯一 Python 依赖）
2. **config.json**（本 skill 根目录）——复制 config.example.json 后填 `ai.api_key` / `ai.base_url` / `ai.model`（见 README）
3. **登录态**：`state/auth_state.json`（扫码登录生成——见 README「扫码登录」一节）

## 脚本（scripts/，用装了 requests 的 python 运行）

| 脚本 | 功能 | 用法 |
|---|---|---|
| heihe_login.py | 扫码登录 | `python heihe_login.py`（生成/更新 cookie） |
| heihe_post.py | 发帖（可带图） | `--title T --text X [--topic-id 20588] [--image "URL[,宽,高]"]` 或 `--library [索引]` / `--list` |
| heihe_comment.py | 评论 / 楼中楼回复 | `--link-id X --text "内容" [--reply-id 父评论id --root-id 根评论id]` |
| heihe_like.py | 评论点赞 | `--comment-id X` |
| heihe_feed.py | 看热帖 | `[--topic-id 7214] [--limit 10]` |
| heihe_fetch.py | 看帖（含评论） | `--link-id X [--with-comments]`（评论前先读帖） |
| heihe_delete.py | 删帖 / 删评论 | `--link-id X --yes` 或 `--comment-id X --yes` |
| heihe_upload.py | 图片上传（调试中） | 需服务端分配 key，见 CHANGELOG 已知遗留 |

- 帖子库：skill 根目录 `post_library.json`（Agent 写的帖子存档，发帖用 `--library`）
- 水贴记录：config.json 配 `log_file` 后，发帖/评论自动追加 markdown 记录

## 典型流程

- **发一帖**：选主题 → Agent 写（查设定/社区风格）→ 加帖子库 → heihe_post --library
- **特定帖子留言**：heihe_fetch 看内容 → Agent 读帖写评论 → heihe_comment 发
- **水贴**：heihe_feed 看热帖 → 挑目标 → fetch 看内容 → 写评论 → 发（留 md 记录）

## 安全

- 发帖/评论/删帖是写操作，**必须用户明确要求**才执行
- 频率：发帖每天 ≤2、评论每小时 ≤3（防风控）
- 触发验证码（show_captcha）就停，等用户网页端解
- cookie 在 skill 的 state/auth_state.json（不入库）
