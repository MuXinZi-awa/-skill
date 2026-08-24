# 小黑盒 Bot Skill（xiaoheihe-bot-skill）

小黑盒（游戏社区）自动**发帖 / 评论 / 看热帖 / 看帖 / 删帖 / 水贴记录**的封装工具。
设计给 **AI Agent**（如 HanaAgent）或普通用户直接用命令行调用，内容由调用方自己写，不走额外 LLM 中转。

> ⚠️ 仅供学习交流。自动发帖/评论有**封号风险**，请低频使用、谨慎操作，后果自负。

## 功能

| 命令 | 说明 |
|---|---|
| `heihe_post.py` | 发帖（指定内容或从帖子库 `post_library.json` 发） |
| `heihe_comment.py` | 评论指定帖子 |
| `heihe_feed.py` | 看热门帖子（按话题筛选） |
| `heihe_fetch.py` | 看帖子全文（评论前先读帖） |
| `heihe_delete.py` | 删除自己的帖子（需 `--yes`） |

附带：**帖子库**（`post_library.json`，AI 写好的帖子存档）+ **水贴记录**（发帖/评论自动写 markdown 日志）。

## 安装

### 1. 克隆依赖项目（签名/cookie 实现）

```bash
git clone https://github.com/2646617098/heibox-comment-bot
cd heibox-comment-bot
python -m venv .venv
.\.venv\Scripts\Activate.ps1     # Windows；macOS/Linux 用 source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 扫码登录（生成 cookie）

```bash
python src/main.py --login-qr
```

手机小黑盒 App → 个人主页右上角扫码 → cookie 自动保存到 `state/auth_state.json`。
（如终端二维码溢出，把打印的 `login url` 用任意二维码工具转成图片再扫）

### 3. 配置本 skill

```bash
git clone https://github.com/你的用户名/xiaoheihe-bot-skill
cd xiaoheihe-bot-skill
Copy-Item config.example.json config.json
```

编辑 `config.json`：

```json
{
  "hb_project_path": "C:\\path\\to\\heibox-comment-bot",
  "log_file": ""
}
```

- `hb_project_path`：heibox-comment-bot 项目的绝对路径（必填）
- `log_file`：可选，水贴记录 md 的路径（留空不记录）

## 用法

所有脚本用 **heibox-comment-bot 的 venv python** 运行：

```bash
PY="C:\path\to\heibox-comment-bot\.venv\Scripts\python.exe"

# 发帖（直接指定）
$PY scripts\heihe_post.py --title "标题" --text "正文" --topic-id 20588

# 发帖子库第一篇（帖子库在 skill 根目录 post_library.json）
$PY scripts\heihe_post.py --library 0

# 看热帖（盒友杂谈）
$PY scripts\heihe_feed.py --topic-id 7214 --limit 10

# 看帖
$PY scripts\heihe_fetch.py --link-id 188908465

# 评论（先看帖再评论）
$PY scripts\heihe_comment.py --link-id 188908465 --text "评论内容"

# 删帖（不可逆，需 --yes）
$PY scripts\heihe_delete.py --link-id 188908465 --yes
```

### 话题 ID 参考

| 话题 | topic_id |
|---|---|
| 推荐流（默认） | 不传 |
| 盒友杂谈 | 7214 |
| 密教模拟器 | 20588 |

发帖时 `link_tag` 与分区绑定（密教模拟器=27，其他分区请抓包确认）。

## 给 AI Agent 用（HanaAgent）

本目录本身就是 **HanaAgent skill** 包：把整个仓库安装为 skill 后，Agent 读 `SKILL.md` 即可调用。
`SKILL.md` 里有完整流程说明（发帖/评论/水贴的典型链路）。

## 隐私

- 仓库**不含任何密钥/配置/cookie**——`config.json`、`state/`、日志均被 `.gitignore` 排除
- 登录态在 heibox-comment-bot 项目的 `auth_state.json`（该仓库自己的 .gitignore 已排除）
- 请勿把 `config.json`、`auth_state.json` 提交到任何仓库

## 免责声明

本项目仅用于学习交流。使用自动发帖/评论可能违反小黑盒社区规则，导致**账号风控、限制甚至封禁**。
请自行评估风险，低频使用，不要用于垃圾信息、营销刷量等用途。作者不对使用后果负责。
