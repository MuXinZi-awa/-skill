# taobao-pipeline skill — scripts 自包含说明

本目录（scripts/）是**完全自包含**的 API 工具集——不依赖任何外部项目文件。

## 环境要求（唯一依赖）

- **Python**（任意带 playwright 的版本，如 F:\Python314）
- **Chrome**（系统安装）
- 首次运行会自动弹浏览器登录千牛（账号已内嵌），登录态存 `scripts/.profile`

## 快速开始

```bash
# 环境检查
python -c "import playwright; print('ok')"

# 商品搜索/抓 ID（第一个命令首次会登录）
cd scripts
python _mtop_api.py 39-01-2060          # 搜索商品 → itemId
python _grab_itemids_api.py 料号1 料号2  # 批量抓 ID → runtime/新品推广_待补.csv

# 万相台（出价）
python _adgroup_audit.py                 # 全量出价审计 → runtime/adgroup_bids.csv
python _batch_fix_bid.py                 # 批量改价（读 runtime/fix_bid_todo.json）
python _verify_bids.py                   # 改价读回验证
```

## 数据输出（都在 skill 内）

- `runtime/`：CSV/JSON 产物（待补 ID、审计、待改清单）
- `.profile/`：浏览器登录态（勿删——删了要重新登录）

## 注意

- `_batch_pipeline.py`（流水线总装）除外——它协调上品/推广脚本（在 推广一键跑 目录），
  属项目级工具；API 工具本身可独立运行。
- 写操作（改价/发布）低频使用，间隔 0.2-0.4s 防频控。
- 被 RGV587 拦截（"被挤爆啦"）时检查：请求必须走页面 evaluate fetch（credentials:include），
  且带当次会话 csrfId。

## 本副本说明（工作区版）

- 本 skill 物理目录在工作区（OH-WorkSpace\skills\taobao-pipeline）——单一事实源
- 系统技能池（.hanako\skills\taobao-pipeline）为 agent 加载入口（junction 指向本目录）
- .profile 登录态不入版本控制（46MB），首次运行自动生成
