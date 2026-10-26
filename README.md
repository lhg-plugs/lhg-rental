<!-- About 简介（推送后填写到仓库 About 栏）：
租房避坑助手：合同风险扫描、押金退还、纠纷应对，小白租房不踩坑 ｜ 一键安装：/plugin marketplace add lhg-plugs/lhg-rental
-->
<!-- topics（推送后打）：claude-code, claude-plugin, agent-skills, rental, contract-review, tenant-rights -->

# lhg-rental：租房避坑助手

> **一句话介绍**：给 AI 装上"租房避坑"能力——粘贴合同文本 10 秒扫出霸王条款（17 条确定性规则），黑中介/二房东识别清单、押金退还专项、纠纷应对话术全配齐，小白租房不踩坑。
>
> **一键安装**：在 Claude Code 里运行
> ```
> /plugin marketplace add lhg-plugs/lhg-rental
> /plugin install lhg-rental@lhg-plugs
> ```

> ⚠️ **非律师意见声明**：本插件输出为通用风险提示与流程建议，不是法律意见；各地租赁条例差异大，以当地最新规定为准，真涉诉请咨询执业律师。

## 它是什么

`lhg-rental` 是一个 Claude Code 插件（plugin 为主、skill 为辅）：

- **3 个命令**（小白入口）：`rental` 租房全流程避坑（合同扫描→中介核验→押金专项→避坑报告），`deposit` 押金退还专项，`dispute` 纠纷应对（协商/投诉/起诉）
- **3 个平台中立 skill**（方法论，可移植到豆包/Workbuddy 等）：合同风险审查、黑中介识别清单、纠纷应对工具箱
- **3 个专家 agent**：合同审查、找房防坑、纠纷教练
- **2 个硬门 hooks**：commit 前合同审计拦截、写入合同文本时提醒核对（均可一键豁免）
- **17 条确定性审计规则**：纯 Python、零第三方依赖，10 秒出结果

## 3 个命令用法

| 命令 | 作用 | 示例 |
|---|---|---|
| `/lhg-rental:rental` | 租房全流程：合同风险扫描→中介核验→押金专项→输出避坑报告 | `/lhg-rental:rental 合同.txt --city 北京` |
| `/lhg-rental:deposit` | 押金退还专项：退租自查→验收清单→扣款争议话术→投诉/起诉路径 | `/lhg-rental:deposit 6000 3000` |
| `/lhg-rental:dispute` | 纠纷应对：押金/维修/解约/跑路四类，L1-L4 分级行动模板 | `/lhg-rental:dispute 押金 "房东扣了2000不退"` |

## 目录结构

```
lhg-rental/
├── .claude-plugin/           # plugin.json + marketplace.json
├── commands/                 # 3 个命令（rental / deposit / dispute）
├── skills/                   # 3 个平台中立 skill
│   ├── rental-contract-scan/ # 合同风险审查：17 条规则+五维人工复核
│   ├── rental-trap-list/     # 黑中介/二房东/假房源识别清单
│   └── rental-dispute-kit/   # 纠纷应对：L1-L4 模板+证据链+时间线
├── agents/                   # 3 个专家 agent
├── hooks/                    # 2 个硬门（commit 拦截 / 合同写入提醒）+ 豁免说明
├── scripts/audit/            # 17 条确定性审计规则（零第三方依赖）
├── fixtures/                 # 冒烟测试用例（坏/好合同对照）
├── smoke_test.py             # 一键冒烟测试
├── ATTRIBUTION.md            # 灵感来源与许可声明
└── LICENSE                  # MIT
```

## 什么时候用 / 什么时候不用（FAQ）

**什么时候用：**

- 拿到房东/中介的合同准备签字，心里没底时 → `/lhg-rental:rental`，10 秒先扫一遍霸王条款
- 要退租了，怕押金被扣时 → `/lhg-rental:deposit`，从退租前 7 天自查到验收话术全包
- 已经和房东/中介吵起来了，不知道下一步干嘛时 → `/lhg-rental:dispute`，定级+证据+话术+时间线
- 帮朋友/家人看租房合同，想给专业意见时 → 审查报告可直接转发

**什么时候不用：**

- 你要的是打官司的正式法律意见 → 本插件是风险提示工具，真涉诉请找执业律师
- 你的城市有特殊租赁政策想一条一条对 → 插件给的是"多地通行做法"口径，具体条文以当地住建部门最新规定为准
- 你希望 AI 直接替你跟房东谈判 → 插件给话术模板，谈判得你自己上（对方只认你这个签字的人）

## lhg-plugs 插件矩阵

| 插件 | 一句话 | 安装 |
|---|---|---|
| [lhg-fullstack](https://github.com/lhg-plugs/lhg-fullstack) | 小白一句话 → 高质量全栈应用 | `/plugin install lhg-fullstack@lhg-plugs` |
| [lhg-video-edit](https://github.com/lhg-plugs/lhg-video-edit) | 一句话把口播素材剪成爆款短视频（+口播脚本子命令） | `/plugin install lhg-video-edit@lhg-plugs` |
| [lhg-wechat-article](https://github.com/lhg-plugs/lhg-wechat-article) | 公众号写作专家：选题到排版一气呵成 | `/plugin install lhg-wechat-article@lhg-plugs` |
| [lhg-xiaohongshu](https://github.com/lhg-plugs/lhg-xiaohongshu) | 小红书种草专家：卖点到爆款笔记一键生成 | `/plugin install lhg-xiaohongshu@lhg-plugs` |
| [lhg-resume](https://github.com/lhg-plugs/lhg-resume) | 简历优化专家：ATS诊断到模拟面试一条龙 | `/plugin install lhg-resume@lhg-plugs` |
| [lhg-ppt](https://github.com/lhg-plugs/lhg-ppt) | PPT制作专家：述职融资答辩一键成稿 | `/plugin install lhg-ppt@lhg-plugs` |
| [lhg-excel](https://github.com/lhg-plugs/lhg-excel) | 表格数据专家：清洗透视图表一条龙 | `/plugin install lhg-excel@lhg-plugs` |
| [lhg-thesis](https://github.com/lhg-plugs/lhg-thesis) | 毕业论文助手：开题到盲审的写作流水线 | `/plugin install lhg-thesis@lhg-plugs` |
| [lhg-miniprogram](https://github.com/lhg-plugs/lhg-miniprogram) | 小程序开发专家：一句话生成微信小程序 | `/plugin install lhg-miniprogram@lhg-plugs` |
| [lhg-contract](https://github.com/lhg-plugs/lhg-contract) | 合同审查助手：风险条款标红+修改建议 | `/plugin install lhg-contract@lhg-plugs` |
| [lhg-geo](https://github.com/lhg-plugs/lhg-geo) | AI搜索优化专家：品牌在AI回答里的可见度 | `/plugin install lhg-geo@lhg-plugs` |
| [lhg-poster](https://github.com/lhg-plugs/lhg-poster) | 海报设计专家：一句话生成手机端海报 | `/plugin install lhg-poster@lhg-plugs` |
| [lhg-shopify](https://github.com/lhg-plugs/lhg-shopify) | 独立站建站专家：高转化店铺一键搭建 | `/plugin install lhg-shopify@lhg-plugs` |
| [lhg-fiction](https://github.com/lhg-plugs/lhg-fiction) | 网文写作专家：大纲到逐章+人设一致性检测 | `/plugin install lhg-fiction@lhg-plugs` |
| [lhg-drama-script](https://github.com/lhg-plugs/lhg-drama-script) | 短剧剧本专家：分集大纲到单集剧本 | `/plugin install lhg-drama-script@lhg-plugs` |
| [lhg-lit-review](https://github.com/lhg-plugs/lhg-lit-review) | 文献综述专家：框架到引用校验一条龙 | `/plugin install lhg-lit-review@lhg-plugs` |
| [lhg-salary-talk](https://github.com/lhg-plugs/lhg-salary-talk) | 薪酬谈判专家：策略到话术演练 | `/plugin install lhg-salary-talk@lhg-plugs` |
| [lhg-biz-report](https://github.com/lhg-plugs/lhg-biz-report) | 商业分析专家：数据到图文报告一键生成 | `/plugin install lhg-biz-report@lhg-plugs` |
| [lhg-study-abroad](https://github.com/lhg-plugs/lhg-study-abroad) | 留学文书专家：PS推荐信多轮打磨 | `/plugin install lhg-study-abroad@lhg-plugs` |
| [lhg-meal-plan](https://github.com/lhg-plugs/lhg-meal-plan) | 营养食谱专家：测算到一周食谱+采购单 | `/plugin install lhg-meal-plan@lhg-plugs` |
| [lhg-competitor](https://github.com/lhg-plugs/lhg-competitor) | 竞品分析专家：五维框架+对比矩阵+SWOT+差异化建议报告 | `/plugin install lhg-competitor@lhg-plugs` |
| [lhg-social-ops](https://github.com/lhg-plugs/lhg-social-ops) | 社媒运营专家：定位→日历→分发策略→复盘，策略+复盘闭环 | `/plugin install lhg-social-ops@lhg-plugs` |
| [lhg-headline](https://github.com/lhg-plugs/lhg-headline) | 爆款标题专家：多平台标题公式生成+合规检测+点击率打分 | `/plugin install lhg-headline@lhg-plugs` |
| [lhg-logo](https://github.com/lhg-plugs/lhg-logo) | Logo设计专家：品牌概念→几何规范→多尺寸导出自检 | `/plugin install lhg-logo@lhg-plugs` |
| [lhg-ecom-design](https://github.com/lhg-plugs/lhg-ecom-design) | 电商视觉专家：卖点到高点击主图一键策划 | `/plugin install lhg-ecom-design@lhg-plugs` |
| [lhg-ecom-report](https://github.com/lhg-plugs/lhg-ecom-report) | 电商复盘专家：店铺数据到周/月复盘报告 | `/plugin install lhg-ecom-report@lhg-plugs` |
| [lhg-lesson-plan](https://github.com/lhg-plugs/lhg-lesson-plan) | 课程设计专家：课标对齐→教案课件→知识点覆盖校验 | `/plugin install lhg-lesson-plan@lhg-plugs` |
| [lhg-dashboard](https://github.com/lhg-plugs/lhg-dashboard) | 数据看板专家：指标体系→看板布局→图表规范校验 | `/plugin install lhg-dashboard@lhg-plugs` |
| [lhg-book-translate](https://github.com/lhg-plugs/lhg-book-translate) | 书籍翻译专家：术语锁定→章节翻译→一致性审计 | `/plugin install lhg-book-translate@lhg-plugs` |
| [lhg-infographic](https://github.com/lhg-plugs/lhg-infographic) | 信息图表专家：数据→图表选型→Canvas绘制→可读性审计 | `/plugin install lhg-infographic@lhg-plugs` |
| [lhg-live-script](https://github.com/lhg-plugs/lhg-live-script) | 直播话术专家：开播钩子到逼单成交，话术一次写完 | `/plugin install lhg-live-script@lhg-plugs` |
| [lhg-course-create](https://github.com/lhg-plugs/lhg-course-create) | 课程制作专家：大纲到试听课，一门课从 0 到可交付 | `/plugin install lhg-course-create@lhg-plugs` |
| [lhg-exam-maker](https://github.com/lhg-plugs/lhg-exam-maker) | 出题组卷专家：知识点→蓝图→组卷→覆盖率校验 | `/plugin install lhg-exam-maker@lhg-plugs` |
| [lhg-weekly-review](https://github.com/lhg-plugs/lhg-weekly-review) | 周报复盘专家：记录→结构化周报→亮点→风险预警 | `/plugin install lhg-weekly-review@lhg-plugs` |
| [lhg-money-plan](https://github.com/lhg-plugs/lhg-money-plan) | 理财规划助手：收支→预算→储蓄目标（非投资建议） | `/plugin install lhg-money-plan@lhg-plugs` |
| [lhg-finmodel](https://github.com/lhg-plugs/lhg-finmodel) | 财务建模专家：假设→三表搭建→勾稽校验→敏感性分析 | `/plugin install lhg-finmodel@lhg-plugs` |
| [lhg-mini-game](https://github.com/lhg-plugs/lhg-mini-game) | H5游戏专家：一句话生成可玩H5小游戏 | `/plugin install lhg-mini-game@lhg-plugs` |
| [lhg-browser-ext](https://github.com/lhg-plugs/lhg-browser-ext) | 浏览器插件专家：一句话想法生成MV3插件 | `/plugin install lhg-browser-ext@lhg-plugs` |
| [lhg-bp](https://github.com/lhg-plugs/lhg-bp) | 商业计划书专家：九章BP→投资人自检→路演版 | `/plugin install lhg-bp@lhg-plugs` |
| [lhg-survey](https://github.com/lhg-plugs/lhg-survey) | 问卷分析专家：清洗→统计→图表→结论报告 | `/plugin install lhg-survey@lhg-plugs` |
| [lhg-product-pick](https://github.com/lhg-plugs/lhg-product-pick) | 跨境选品专家：目标市场→五维打分表→供应链 checklist→风险清单 | `/plugin install lhg-product-pick@lhg-plugs` |
| [lhg-labor-rights](https://github.com/lhg-plugs/lhg-labor-rights) | 劳动维权助手：纠纷场景→仲裁流程指引→文书模板→证据清单 | `/plugin install lhg-labor-rights@lhg-plugs` |
| [lhg-pet-care](https://github.com/lhg-plugs/lhg-pet-care) | 宠物养护专家：建档→驱虫/疫苗/饮食时间表→健康 checklist | `/plugin install lhg-pet-care@lhg-plugs` |
| [lhg-oss-launch](https://github.com/lhg-plugs/lhg-oss-launch) | 开源冷启动专家：README→launch 素材→一键成片指引 | `/plugin install lhg-oss-launch@lhg-plugs` |
| [lhg-community](https://github.com/lhg-plugs/lhg-community) | 社群运营专家：定位→入群SOP→内容日历→转化话术→流失召回 | `/plugin install lhg-community@lhg-plugs` |
| [lhg-taobao](https://github.com/lhg-plugs/lhg-taobao) | 店铺运营专家：选品→上架→标题/主图优化→数据复盘 | `/plugin install lhg-taobao@lhg-plugs` |
| [lhg-sci-figure](https://github.com/lhg-plugs/lhg-sci-figure) | 学术图表专家：数据→期刊配图规范→图表生成→规范脚本校验 | `/plugin install lhg-sci-figure@lhg-plugs` |
| [lhg-sop](https://github.com/lhg-plugs/lhg-sop) | SOP沉淀专家：流程访谈→SOP文档→检查清单→版本管理 | `/plugin install lhg-sop@lhg-plugs` |
| [lhg-podcast](https://github.com/lhg-plugs/lhg-podcast) | 播客制作专家：选题→录制→剪辑→shownotes→分发，一期节目全流程 | `/plugin install lhg-podcast@lhg-plugs` |
| [lhg-motion-video](https://github.com/lhg-plugs/lhg-motion-video) | 动效视频专家：需求→导演brief→纯代码渲染→成片导出 | `/plugin install lhg-motion-video@lhg-plugs` |
| [lhg-user-growth](https://github.com/lhg-plugs/lhg-user-growth) | 用户增长专家：杠杆诊断→可执行实验清单→复盘 | `/plugin install lhg-user-growth@lhg-plugs` |
| [lhg-growth-lab](https://github.com/lhg-plugs/lhg-growth-lab) | 增长实验专家：假设→实验设计→显著性判定→复盘 | `/plugin install lhg-growth-lab@lhg-plugs` |
| [lhg-webscraper](https://github.com/lhg-plugs/lhg-webscraper) | 爬虫采集专家：合规方案→反爬应对→数据清洗（仅公开数据） | `/plugin install lhg-webscraper@lhg-plugs` |
| [lhg-sql](https://github.com/lhg-plugs/lhg-sql) | SQL取数专家：业务问题→SQL生成→方言适配→性能自检 | `/plugin install lhg-sql@lhg-plugs` |
| [lhg-api-integration](https://github.com/lhg-plugs/lhg-api-integration) | API对接专家：文档→鉴权→调用封装→重试限流→联调 | `/plugin install lhg-api-integration@lhg-plugs` |
| [lhg-email](https://github.com/lhg-plugs/lhg-email) | 邮件营销专家：用户分层→序列邮件→送达率checklist | `/plugin install lhg-email@lhg-plugs` |
| [lhg-ads](https://github.com/lhg-plugs/lhg-ads) | 广告投放专家：策略→素材清单→数据复盘（方法论非效果承诺） | `/plugin install lhg-ads@lhg-plugs` |
| [lhg-amazon-listing](https://github.com/lhg-plugs/lhg-amazon-listing) | 亚马逊运营专家：标题→五点→关键词→Listing评分 | `/plugin install lhg-amazon-listing@lhg-plugs` |
| [lhg-promo](https://github.com/lhg-plugs/lhg-promo) | 促销策划专家：玩法设计→利润测算→执行清单→复盘 | `/plugin install lhg-promo@lhg-plugs` |
| [lhg-user-research](https://github.com/lhg-plugs/lhg-user-research) | 用户调研专家：问卷/访谈提纲→回收分析→洞察报告 | `/plugin install lhg-user-research@lhg-plugs` |
| [lhg-insurance](https://github.com/lhg-plugs/lhg-insurance) | 保险配置助手：家庭保障缺口分析→四险种配置方案→条款坑点清单 | `/plugin install lhg-insurance@lhg-plugs` |
| [lhg-pr](https://github.com/lhg-plugs/lhg-pr) | PR发稿专家：事件→通稿三版本→媒体清单→发布节奏表 | `/plugin install lhg-pr@lhg-plugs` |
| [lhg-job-desc](https://github.com/lhg-plugs/lhg-job-desc) | JD撰写专家：岗位信息→评分→多版本，18条规则拦截歧视词 | `/plugin install lhg-job-desc@lhg-plugs` |
| [lhg-travel](https://github.com/lhg-plugs/lhg-travel) | 旅行规划专家：日行程→POI→预算表→打包清单，16条规则审计 | `/plugin install lhg-travel@lhg-plugs` |
| [lhg-rental](https://github.com/lhg-plugs/lhg-rental) | 租房避坑助手：合同风险扫描+押金退还+纠纷应对 | `/plugin install lhg-rental@lhg-plugs` |
| *（后续插件在此追加，保持表格格式一致）* | | |

## 自检与反馈

本插件自带质检：每次使用后可跑 `python3 smoke_test.py` 一键验证（JSON 合法、skill/command/agent 完整性、62 条规则、fixtures 命中、hooks 行为）。

发现 bug 或有改进建议，以 `[QC] <一句话问题>` 为标题提交到 https://github.com/lhg-plugs/lhg-fullstack/issues，正文写清"复现步骤 → 实际表现 → 期望表现"。

## 自检与反馈

本插件自带质检：每次使用后可跑 `python3 smoke_test.py` 一键验证（JSON 合法、skill/command/agent 完整性、17 条规则、fixtures 命中、hooks 行为）。

发现 bug 或有改进建议，以 `[QC] <一句话问题>` 为标题提交到 https://github.com/lhg-plugs/lhg-rental/issues，正文写清"复现步骤 → 实际表现 → 期望表现"。

## 出品：刘洪光

本插件由真人出镜 IP「刘洪光」（安徽合肥）出品，归属 [lhg-skills](https://github.com/lhg-skills)。

- GitHub 主页：https://github.com/lhg-skills —— 全部 skill 开源在此，欢迎 star
- 抖音：搜「刘老师讲AI实战」
- 微信：lhgsmsw
