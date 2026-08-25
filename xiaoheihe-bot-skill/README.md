# 小黑盒 Bot Skill（xiaoheihe-bot-skill）

小黑盒（游戏社区）自动**发帖 / 评论 / 看热帖 / 看帖 / 删帖 / 点赞 / 带图发帖 / 扫码登录 / 视觉看图 / 水贴记录**的封装工具。
**自包含**：签名 / cookie / 客户端 / 登录逻辑全部内置（`scripts/lib/`），不依赖任何外部项目。
设计给 **AI Agent**（如 HanaAgent）或普通用户直接用命令行调用，内容由调用方自己写，不走额外 LLM 中转。

> ⚠️ 仅供学习交流。自动发帖/评论有**封号风险**，请低频使用、谨慎操作，后果自负。

## 功能

| 命令 | 说明 |
|---|---|
| `heihe_login.py` | 扫码登录（生成/更新 cookie） |
| `heihe_post.py` | 发帖（支持带图，或从帖子库 `post_library.json` 发） |
| `heihe_comment.py` | 评论 / 楼中楼回复（`--reply-id` / `--root-id`） |
| `heihe_like.py` | 评论点赞 |
| `heihe_feed.py` | 看热门帖子（按话题筛选） |
| `heihe_fetch.py` | 看帖子全文 / 评论区（评论前先读帖；图帖加 `--images` 挖图片 URL） |
| `heihe_vision.py` | **视觉辅助**：图帖图片（URL/本地文件）→ 文字描述（DeepSeek 视觉模型） |
| `heihe_delete.py` | 删除自己的帖子 / 评论（需 `--yes`） |

> 注：独立图片上传脚本（heihe_upload.py）尚在调试未随包发布；带图发帖走 `heihe_post.py --image`（内部已内置 COS 直传签名）

附带：**帖子库**（`post_library.json`，AI 写好的帖子存档）+ **水贴记录**（发帖/评论自动写 markdown 日志）。

## 安装

只需 Python 3 + `requests`（登录扫码需要 `qrcode`）：

```bash
pip install requests qrcode
```

（也可以用 venv：`python -m venv .venv` → 激活 → 装上面两个）

## 扫码登录（生成 cookie）

登录态保存在本 skill 的 `state/auth_state.json`。用自带的登录脚本：

```bash
python scripts\heihe_login.py
```

终端会显示二维码（或保存 `qrcode.png`），手机小黑盒 App → 个人主页右上角扫码 → 登录态自动保存到 `state/auth_state.json`。登录过期时重跑一次即可。

> 登录脚本使用 `scripts/lib` 内置的签名/cookie 实现，**完全自包含**，不需要任何外部项目。

## 配置

复制模板：

```bash
Copy-Item config.example.json config.json
```

编辑 `config.json` 关键字段：

- `ai.base_url` / `ai.api_key` / `ai.model`：OpenAI 兼容接口（如 DeepSeek：`https://api.deepseek.com/v1` + 你的 key + `deepseek-chat`）
- `vision`：视觉辅助配置（`enabled` / `base_url` / `api_key` / `model` / `detail` / `prompt`）。模型用 DeepSeek 官方 `deepseek-v4-flash-vision-exp`；`api_key` 留空自动复用 `ai.api_key`
- `request.default_query.heybox_id` / `device_id`：一般不用动（cookie 登录后自动带）
- `log_file`：可选，水贴记录 md 的路径（留空不记录）

> ⚠️ `config.json` 含 api_key，已被 `.gitignore` 排除，**不要提交到任何仓库**。

## 用法

用装了 requests 的 python 运行（venv 或系统 python 均可）：

```bash
# 发帖（直接指定）
python scripts\heihe_post.py --title "标题" --text "正文" --topic-id 20588

# 发帖子库第一篇（帖子库在 skill 根目录 post_library.json）
python scripts\heihe_post.py --library 0

# 看热帖（盒友杂谈）
python scripts\heihe_feed.py --topic-id 7214 --limit 10

# 看帖（含评论区）
python scripts\heihe_fetch.py --link-id 188908465 --with-comments

# 图帖：挖图片 URL → 看图片内容（视觉辅助）
python scripts\heihe_fetch.py --link-id 188811400 --images
python scripts\heihe_vision.py --url "https://cdn.xxx/1.jpg" [--url ...] [--file 本地路径]

# 评论（先看帖再评论）
python scripts\heihe_comment.py --link-id 188908465 --text "评论内容"

# 删帖（不可逆，需 --yes）
python scripts\heihe_delete.py --link-id 188908465 --yes
```

### 话题 ID 参考

| 话题 | topic_id |
|---|---|
| 推荐流（默认） | 不传 |
| 盒友杂谈 | 7214 |
| 密教模拟器 | 20588 |

发帖时 `link_tag` 与分区绑定（密教模拟器=27，其他分区请抓包确认）。

## 视觉辅助（图帖）

小黑盒大量帖子是图片帖（游戏截图 / 攻略图 / 梗图 / 表情包），正文文字为空，纯看文本会被「拒之门外」。`heihe_vision.py` 把图片喂给 DeepSeek 视觉模型（`deepseek-v4-flash-vision-exp`），输出图片内容描述，Agent / 用户就能看懂图帖再写评论。

- 图片输入：外部 URL（自动下载）或本地文件，支持多张，支持 JPEG/PNG/GIF/WebP
- 成本：每张图缩放后 ≤384 token，`detail: low` 再省一笔（512×512 缩放）
- 不新增依赖：只需 requests（与现有脚本一致）

```bash
# 典型图帖链路：fetch 挖 URL → vision 看图 → 写评论
python scripts\heihe_fetch.py --link-id 188811400 --images
python scripts\heihe_vision.py --url "https://cdn.xiaoheihe.cn/bbs/app/.../photo.jpg"
python scripts\heihe_comment.py --link-id 188811400 --text "看完图了，这猫回头的角度确实有点东西"
```

> `--images` 是启发式宽匹配（找所有像图片 URL 的字段），可能捎带头像/图标，Agent 使用时自行甄别正文图。

## 给 AI Agent 用（HanaAgent）

本目录本身就是 **HanaAgent skill 包**：把整个仓库安装为 skill 后，Agent 读 `SKILL.md` 即可调用。
`SKILL.md` 里有完整流程说明（发帖/评论/水贴/图帖的典型链路）。

## 隐私

- 仓库**不含任何密钥/配置/cookie**——`config.json`、`state/`、日志、帖子库均被 `.gitignore` 排除
- 登录态在 `state/auth_state.json`（已忽略，不入库）
- 请勿把 `config.json`、`auth_state.json` 提交到任何仓库

## 免责声明

本项目仅用于学习交流。使用自动发帖/评论可能违反小黑盒社区规则，导致**账号风控、限制甚至封禁**。
请自行评估风险，低频使用，不要用于垃圾信息、营销刷量等用途。作者不对使用后果负责。
