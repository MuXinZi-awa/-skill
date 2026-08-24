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

1. **heibox-comment-bot**（签名/cookie 实现）——见 README 安装：
   `git clone https://github.com/2646617098/heibox-comment-bot`
   建 venv 装依赖后扫码登录（生成 state/auth_state.json）
2. **config.json**（本 skill 根目录）——复制 config.example.json 填 `hb_project_path`（heibox-comment-bot 的路径）

## 脚本（scripts/，用 heibox 项目的 venv python 运行）

| 脚本 | 功能 | 用法 |
|---|---|---|
| heihe_post.py | 发帖 | `--title T --text X [--topic-id 20588]` 或 `--library [索引]` / `--list` |
| heihe_comment.py | 评论 | `--link-id 181177992 --text "内容"` |
| heihe_feed.py | 看热帖 | `[--topic-id 7214] [--limit 10]` |
| heihe_fetch.py | 看帖 | `--link-id 188908465`（评论前先读帖） |
| heihe_delete.py | 删帖 | `--link-id X --yes` |

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
- cookie 在 heibox 项目的 auth_state.json（不入库）
