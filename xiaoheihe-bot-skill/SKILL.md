---
name: xiaoheihe-bot
description: >
  小黑盒（游戏社区）自动发帖 / 评论 / 水贴 / 删帖 / 看帖工具。Agent 直接调用小黑盒 API。
  触发场景：用户提到小黑盒、发帖、水贴、刷评论、删帖、社区运营、自动回帖、帖子库。
  安装：复制 config.example.json 为 config.json 填 api_key，扫码登录见 README（自包含，无外部项目依赖）。
---

# 小黑盒 Bot Skill

直接调小黑盒 API 的封装（发帖 / 评论 / 看热帖 / 看帖 / 删帖 / 水贴记录 / 视觉看图）。
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
| heihe_fetch.py | 看帖（含评论） | `--link-id X [--with-comments]`；图帖加 `--images` 列出图片 URL |
| **heihe_vision.py** | **视觉辅助（图帖）** | `--url "图片URL"` 或 `--file 本地路径`（可多个）；把图片变成文字描述 |
| heihe_delete.py | 删帖 / 删评论 | `--link-id X --yes` 或 `--comment-id X --yes` |

- 注：heihe_upload.py（图片上传独立脚本）尚在调试，未随包发布；带图发帖走 heihe_post.py --image（内部已内置 COS 直传签名）

- 帖子库：skill 根目录 `post_library.json`（Agent 写的帖子存档，发帖用 `--library`；不入库）
- 水贴记录：config.json 配 `log_file` 后，发帖/评论自动追加 markdown 记录

## 典型流程

- **发一帖**：选主题 → Agent 写（查设定/社区风格）→ 加帖子库 → heihe_post --library
- **特定帖子留言**：heihe_fetch 看内容 → Agent 读帖写评论 → heihe_comment 发
- **图帖（图片帖）**：heihe_fetch --images 挖出图片 URL → heihe_vision --url "URL" 把图片变描述 → Agent 看懂图 → 写评论 → heihe_comment 发
- **水贴**：heihe_feed 看热帖 → 挑目标 → fetch 看内容 → 写评论 → 发（留 md 记录）

## 视觉辅助（图帖）

小黑盒很多帖子是图片帖（截图/攻略/梗图/表情包），文字是空的。此时用视觉模型把图片变成描述，Agent 才能看懂帖子内容再写评论。

- 模型：DeepSeek `deepseek-v4-flash-vision-exp`（官方实验性视觉模型，OpenAI 兼容，每图 ≤384 token）
- 配置：`config.json` → `vision` 块（`enabled` / `base_url` / `api_key` 留空复用 `ai.api_key` / `model` / `detail` / `prompt`）
- 依赖：仅 requests（与现有脚本一致，不新增）

```bash
# 图帖完整链路：挖 URL → 看图片内容
python scripts\heihe_fetch.py --link-id 188811400 --images
python scripts\heihe_vision.py --url "https://cdn.xiaoheihe.cn/.../xxx.jpg"
```

注意：图帖正文常为空属正常；`--images` 是宽匹配，可能捎带头像/图标等非正文图，Agent 自行甄别。

## 登录会话（重要，踩过坑）

小黑盒有两套登录会话，功能权限不同（2026-08-25 实测）：

| 会话 | 生成方式 | 发帖/评论/看帖 | 评论点赞 comment/support | 帖子点赞 workshopapi |
|---|---|---|---|---|
| 扫码会话 | `heihe_login.py` 扫码 | ✅ | ❌（返回「账号状态异常」） | ✅ |
| 浏览器会话 | 浏览器网页登录 | ✅ | ✅ | ✅ |

- **评论点赞必须用浏览器会话**：浏览器登录账号 → 复制 `.xiaoheihe.cn` 域的 cookie（`user_heybox_id` / `user_pkey` / `x_xhh_tokenid`）→ 写入 `state/auth_state.json` 的 cookie 字段（`source: "browser"`）
- 浏览器 cookie 有效期约 7 天，过期后重新登录复制
- 扫码会话仍可用于发帖/评论/看帖；帖子点赞两套会话都通
- 部分浏览器会话还有 `pkey`（= user_pkey 的非 HttpOnly 镜像），`heihe_like.py` 已自动补齐，无需手动处理

## 评论内容避雷（小黑盒审核，2026-08-25 实测）

- 评论触发内容审核会**静默失败**（`结果: failed` 且无 msg，HTTP 200）：实测「workshopapi / heybox_id / status ok」等接口词、「破译 / 抓包」等词会被拦
- 发更新日志/评论用**自然语言**描述，别带接口名和破解类词汇；内容拆短（单条 ≤200 字内稳，超长易失败）
- 失败处理：优先怀疑审核，精简措辞重发，别反复硬刚同一条

## 安全

- 发帖/评论/删帖是写操作，**必须用户明确要求**才执行
- 频率：发帖每天 ≤2、评论每小时 ≤3（防风控）
- 触发验证码（show_captcha）就停，等用户网页端解
- cookie 在 skill 的 state/auth_state.json（不入库）
