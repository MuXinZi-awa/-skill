# 更新日志（Changelog）

## v0.2.1（2026-08-25）

**新增/修复**
- `heihe_comment.py` 支持楼中楼：新增 `--reply-id` / `--root-id` 参数，回复某条评论时作为内嵌回复发出（对方能收到通知），不再只是独立顶层评论
- `heihe_delete.py` 支持删评论：新增 `--comment-id` 参数（POST /bbs/app/comment/delete，参数名 `comment_id`），删帖删评论二选一
- 帖子库第四篇：《小黑盒评论bot v0.2.0：登录一条命令，签名内置》更新日志帖（已发布，link 188957001）

**教训**
- 楼中楼是发评论互动的正确姿势：顶层评论收不到通知，也显得像自言自语

---

## v0.2.0（2026-08-24）

**新增**
- 扫码登录脚本 `heihe_login.py`：自包含，不再依赖外部项目，一条命令扫码登录
- `scripts/lib` 内置签名/cookie 模块（config_loader / auth_manager / custom_signer / heybox_client / signer_base）
- `heihe_fetch.py` 新增 `--with-comments`：看帖时同时查看评论区（冲浪能看见盒友评论了）
- 帖子库第二篇：《给 AI 装了一双"小黑盒的眼睛"》安利帖（已发布，link 188926935）

**重构**
- 5 个脚本（发帖/评论/看帖/看热帖/删帖）改为**自包含**：不再依赖 heibox-comment-bot 项目路径，`config.json` 合并进本 skill

**文档**
- README 重写为自包含版（安装只需 `pip install requests qrcode`）
- SKILL.md 更新依赖说明 + 脚本表（新增登录行）

**安全**
- `config.json` / `state/` / `qrcode*.png` / 日志 均由 `.gitignore` 保护，不入库

---

## v0.1.0（2026-08-24）

**初始版本**（莉莉编写）
- 发帖 / 评论 / 看热帖 / 看帖 / 删帖 + 帖子库（post_library.json）+ 水贴记录
- 内容由 Agent 自己写（社区风格、查证设定），不走外部 LLM
