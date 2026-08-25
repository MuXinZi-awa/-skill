# 更新日志（Changelog）

## v0.3.3（2026-08-25 深夜）

**修复**
- `heihe_comment.py` 打印修正：`http_status` → `http_status_code`（之前永远显示 `HTTP ?`）

**经验（写入 SKILL.md「评论内容避雷」）**
- 小黑盒评论有内容审核，触发会静默失败（`结果: failed` 无 msg）：实测「workshopapi / heybox_id / status ok」等接口词、「破译 / 抓包」等词会被拦
- 发评论/更新日志用自然语言、拆短（单条 ≤200 字内稳）；失败优先精简重发

---

## v0.3.2（2026-08-25 深夜）

**破译/修复**
- **评论点赞（comment/support）最终定位**：扫码会话被拒（「账号状态异常」），**浏览器 web 会话可通**——同账号、同参数、同签名，仅 cookie 会话类型差异（2026-08-25 实测 `status: ok`）
- 默认登录态切换为**浏览器会话**（扫码会话备份为 `state/auth_state.json.qr_backup`）
- `heihe_like.py`：heybox_id 自动从 cookie 解析；自动补齐浏览器会话的 `pkey` 镜像 cookie

**经验（已写入 SKILL.md「登录会话」章节）**
- 两套会话（扫码/浏览器）权限差异表：评论点赞必须用浏览器会话；扫码会话仅发帖/评论/看帖；帖子点赞两套都通
- 浏览器 cookie 有效期约 7 天，过期重登复制

---

## v0.3.1（2026-08-25 深夜）

**新增**
- **帖子点赞实装**（`heihe_like.py --link-id`）：workshopapi `/bbs/app/profile/award/link` 破译成功——梓帆抓包（hkey=Y7YVS65）反推验证签名模式，现有 `get_keys` 直接命中；`heybox_id` 自动从 cookie（`user_heybox_id`）解析当前账号，不写死。实测 link 189024138 点赞返回 `status: ok`

**已知遗留**
- 评论点赞（comment/support）仍返回「账号状态异常」：已对齐梓帆抓包（补齐 heybox_id、去掉 _notip），签名验证通过（能到业务层），仍被拒——疑为账号侧风控（等级/设备标记），非参数问题；帖子点赞（workshopapi）同 cookie 可通，两接口风控策略不同

---

## v0.3.0（2026-08-25）

**新增**
- `heihe_vision.py`：**视觉辅助**——图帖图片（URL/本地文件）→ 视觉模型 → 文字描述。图帖不再被拒之门外
- `heihe_fetch.py` 新增 `--images`：递归挖出帖子原始数据里的图片 URL（不依赖具体字段名，宽匹配）
- `config.json` 新增 `vision` 配置块（模型：DeepSeek `deepseek-v4-flash-vision-exp`，api_key 留空自动复用 `ai.api_key`）

**修复**
- `config.example.json` 此前只有 2 个字段、与真实配置严重脱节，已补全为完整结构（含 vision 块，key 用占位符）
- 清理 `hb_project_path` 残留（v0.2.0 已自包含，该字段不再使用）
- SKILL.md frontmatter 安装说明残留 v0.1 的 heibox-comment-bot 依赖描述，已修正

**文档**
- SKILL.md / README.md 新增「视觉辅助（图帖）」章节与典型流程
- 脚本表补全 v0.2.x 遗漏（heihe_like / heihe_upload / fetch --with-comments）

---

## v0.2.2（2026-08-25 午后）

**新增**
- `heihe_like.py`：评论点赞（`--comment-id`，POST /bbs/app/comment/support，`support_type=1`，2026-08-25 抓包确认）
- **发图全链路破译并跑通**：token/v2（合法 key）→ 腾讯云 COS 直传（手写签名）→ imgheybox URL。用轻轨图实测：PUT 成功、URL 可访问（CDN 缓存带 `?x=1` 绕过）、已发出带图帖（link 188975073）

**修复**
- `heihe_post.py --image`：img 块**必须带 width/height**，否则服务端静默丢图（首帖踩坑）。支持 `--image "URL,宽,高"` 或自动下载解析尺寸
- `qcloud_cos_signer.py` 两处 bug：① header 签名时键大小写不匹配（content-type vs Content-Type，KeyError）；② key 前导斜杠导致 path 双斜杠（`//web/...`，COS 403）
- **发帖带图 URL 要用 COS 源站**（`{bucket}.cos.{region}.myqcloud.com`），不要用 imgheybox CDN（`max-c.com`）：CDN 按 URL 缓存旧图，覆盖源文件后 CDN 仍是旧缓存，带 `?x=1` 浏览器能绕过但小黑盒服务器抓图时不会带 → 帖子图会变成旧图（实测踩坑，link 188975073 已删重发 188975310）

**已知遗留**
- info/v2（分配 key）仍报"参数错误:1000"：抓包对比发现网页上传请求不带 heybox_id、参数与签名均已对齐，仍被拒；怀疑账号 web 上传权限/风控（新号等级 2），待观察或换号验证
- 帖子点赞接口（workshopapi.xiaoheihe.cn/bbs/app/profile/award/link）已抓包到 URL，Payload 待验证
- 取消点赞参数待验证（同一 URL，未知字段）

---

## v0.2.1（2026-08-25）

**新增/修复**
- `heihe_comment.py` 支持楼中楼：新增 `--reply-id` / `--root-id` 参数，回复某条评论时作为内嵌回复发出（对方能收到通知），不再只是独立顶层评论
- `heihe_delete.py` 支持删评论：新增 `--comment-id` 参数（POST /bbs/app/comment/delete，参数名 `comment_id`），删帖删评论二选一
- `heihe_post.py` 支持带图发帖：新增 `--image` 参数（可重复），正文以 text+img 块发送（img 的 url 可直接用 imgheybox 或外链图床）；帖子库条目也可带 `images` 字段
- 帖子库第四篇：《小黑盒评论bot v0.2.0：登录一条命令，签名内置》更新日志帖（已发布，link 188957001）
- **上传接口签名算法破译**（lib/custom_signer.py 新增 `get_upload_keys`）：与普通接口不同，str2 = path + '?' + 业务参数按字母序，且三字符串不排序（用抓包 hkey=37I1Y65 / P10Y042 双重验证）

**教训**
- 楼中楼是发评论互动的正确姿势：顶层评论收不到通知，也显得像自言自语
- 多端登录互顶：一个账号同时挂网页+手机+脚本，后登录的会把先登录的顶掉（表现为 token 报 relogin）

**已知遗留**
- 上传 key 由服务端分配（info/v2 返回），客户端不可自造；新号 info/v2 可能报"参数错误:1000"（权限/风控待观察）
- 点赞接口待探测实装

---

## 部署排坑（2026-08-25 整理）

给 fork/自部署的人看的常见坑：

1. **依赖**：`pip install requests qrcode`（qrcode 用于扫码登录时终端显示二维码）
2. **登录**：先跑 `python scripts/heihe_login.py` 扫码；cookie 存在 `state/auth_state.json`（已被 .gitignore 保护，不会入库）
3. **多端互顶**：同一账号多端登录会互相顶掉（网页/App/脚本任一新登录都可能让其他端 relogin）。测试时建议用独立小号，别用常用号
4. **脚本路径**：所有脚本用 `__file__` 定位（SKILL_DIR/LIB_DIR），任何目录下都能跑；但 `config.json` 必须留在 skill 根目录
5. **签名**：签名逻辑内置在 `scripts/lib/`，普通接口用 `get_keys`，上传类接口（qcloud/cos/upload/*）必须用 `get_upload_keys`（算法不同，用错会"验证参数错误"）
6. **频率限制**：发帖每天 ≤2、评论每小时 ≤3；超了会触发验证码或风控。评论建议串行发送（并发偶发失败）
7. **验证码**：响应出现 `show_captcha` 立即停手，去网页端手动解，别硬顶
8. **敏感文件**：`config.json`（含 API key）、`state/`、`qrcode*.png` 已被 .gitignore 保护；改 config 后 push 前先 `git status` 确认

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
