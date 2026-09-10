# 每日开发日志

> 此文档用于跨 agent 同步当日改动。仅保留最近 3 天的记录，每次在对应日期中末尾写入日志。

## 2026-09-10

### 设置面板管线页合并 + 运行窗口重做 + 杂项落位（三提交）

**问题/需求：** 承接 2026-09-09 的调研结论：管线四页靠硬编码下标往基础布局里插杂项，四页骨架不一致（翻译页四个附加块全堆在 Parameters 标题上方、检测页复选框挤在模块下拉同一行、修复页附加项在参数下方）。用户拍板的方向：管线页**合并成一页**、页内用标签切换；模块选择交给底部栏（设置面板不再放）；常用管线开关搬进「运行」窗口（对齐上游「启用模块」网格）；搬剩的杂项并入 General 的 App 页。

**改动要点：**

- **管线页合并（`52d2d40`）**：`ui/configpanel.py::_build_pipeline_page` 用 `QTabBar` + `QStackedWidget` 承载四阶段，Modules 组导航 6 项 → 3 项（Module Actions / Pipeline / LLM Profile），全站 12 页 → 10 页。四个阶段面板**对象与信号链原样保留**（底部栏、`module_manager`、画布修复工具面板都持有引用），只经 `ui/module_parse_widgets.py::set_module_selector_visible(False)` 隐藏模块选择行、改为只读引擎名（`engine_label`）。`module_combobox` 只隐藏不删除——它仍是真值源。合并页整体不套 `_wrap_page`（否则标签栏随内容滚走），各标签内容单独 `_wrap_page` 并去掉左右留白。`focusOnDetect/OCR/Inpaint/Translator` 改为「选中 Pipeline + 切对应标签」，底部栏四个齿轮路径不变。删掉修复页 `showEvent`/`hideEvent` 往返搬运模块下拉的 hack；画布侧 `ui/drawingpanel.py::InpaintPanel` / `RectPanel` 改为在 `showEvent` 里显式点亮借来的下拉（不做显式隐藏——切工具时新面板的 show 可能先于旧面板的 hide）。
- **运行窗口重做（`74b58b1`）**：内联在 `ui/mainwindow.py::run_imgtrans` 的约 400 行对话框抽成 `ui/run_pipeline_dialog.py`，按上游同名文件的形态重做——上半「启用模块」网格（每阶段 = 图标开关 + 模块下拉），下半各阶段折叠选项区（`ExpandingToolButton`）。阶段强调色取主题的 `@accentDetect`/`@accentOCR`/`@accentInpaint`/`@accentTranslate`（与 LLM Profile 徽章同一套），不移植上游硬编码调色板。模块下拉写回底部栏选择器（唯一真值源），不新增 ModuleManager 接口。搬入的选项：检测＝Keep Existing Lines、修复＝Skip simple cases、翻译＝源/目标语言 + 单块翻译模式 + LLM 上下文/术语表整块。保留 Render Only 批量渲染、页码 RangeSlider + All Pages、术语表状态指示、Run without update textstyle、清空二次确认。**刻意不移植**：无边框外壳与 `DialogCloseButton`、每阶段 hover 齿轮（运行窗口是模态的，无法在其上拉起设置浮层；底部栏齿轮已承担该入口）、上游 `page_range_progress`。资源补 4 个图标 + `RunPipeline*` QSS。`InpainterBase.check_need_inpaint` 初值改由 `module_manager` 从 pcfg 直接推入；翻译器异步加载完成后经 `_sync_run_dialog_translator` 刷新语言下拉。
- **杂项落位（本提交）**：从管线页搬出的两项直接并入 General 的 **App 页**，不单设暂存页——`Misc` 这种名字会自己招来下一条无家可归的选项。App 页成为 Updates / External Editor / Workbench / Export Config / Import Config 五节，General 组 7 → 6 页、全站 10 → 9 页。Photoshop 路径（从修复页搬来，`ConfigPanel.ps_path_edit`）归 App 的 External Editor 节，工作台确认开关（从翻译页搬来，`ConfigPanel.confirm_costly_checker`）归 Workbench 节；`ui/drawingpanel.py` 的「未找到 Photoshop」提示同步改指 `Settings → App → Photoshop Path`。导航首项 `Module Actions` → `Models`（与该页自己的 `PanelGroupBox` 标题一致）。新增 `tests/test_settings_app_page.py`。
- **i18n**：新增 `RunPipelineDialog` 上下文 33 条（译文复用既有条目）、ConfigPanel/DrawingPanel 补 11 条，清掉移出产生的 41 条孤儿，qm 重编。
- **测试**：新增 `tests/test_pipeline_page_merge.py`（8 例）、`tests/test_run_pipeline_dialog.py`（13 例）、`tests/test_settings_app_page.py`（6 例）；冒烟测试补 `RunPipelineDialog` 实例化。`verify.py --full` 全绿。

**涉及文件：** `ui/configpanel.py`、`ui/module_parse_widgets.py`、`ui/run_pipeline_dialog.py`（新）、`ui/drawingpanel.py`、`ui/mainwindow.py`、`ui/module_manager.py`、`config/stylesheet.css`、`icons/text_disabled.svg` 等 4 个图标（新）、`translate/zh_CN.ts`、`translate/zh_CN.qm`、`tests/test_pipeline_page_merge.py`（新）、`tests/test_run_pipeline_dialog.py`（新）、`tests/test_settings_app_page.py`（新）、`tests/test_startup_imports.py`、`AGENTS.md`、`docs/技术实现/设置面板概述.md`、`docs/基础速查/设置面板排版思路.md`

### 设置面板普查整理 + 运行窗口字号对齐（三提交）

**问题/需求：** 用户实机验收三提交后反馈「运行界面的拓展管线功能项的**字号**需要对上游」，并要求在继续下一步前先改掉；随后要求对设置面板做**一次全面普查**，据此判断如何整理与编排。

**改动要点：**

- **运行窗口字号对齐**：折叠区内的标签与折叠头本来就在 QSS 里钉了上游的 12px，但区内的下拉落到了全局 `QComboBox` 的 14px，比同一行标签大一圈；复选框与数值框则未显式钉住，靠应用字体 9pt 凑巧对齐。补一组 `QWidget#RunPipelineSettingsSection` 规则（下拉 12px 且收到 20px 高、复选框 12px + 12px 指示器、数值框 12px），对齐上游同名规则。**顺带修一个离屏渲染才暴露的真 bug**：`ui/run_pipeline_dialog.py::_build_translate_options` 把「Source」标签 `addWidget` 到了整页布局而不是它自己那一行，实际渲染成 Translation 折叠区下方一行孤立的 Source；已改回 `lang_layout`，并补回归测试（断言页布局里没有裸 `QLabel`、Source 标签与下拉同行）。
- **普查结论**（用户实机验收第一批后要求对设置面板做一次全面普查）：页面骨架本身是对的，问题集中在——Typesetting/App 有三处手写 `setContentsMargins` 没走 `ConfigFormRow`；另有三个死/错项（见后两条提交）。**明确不搬**：设置在面板外的大批持久项（画笔粗细/裁剪比例/搜索选项/暗色模式等）就地调整更自然，收进设置页只会把一次点击变成「开面板→找页→改→关」，违背本分支「交互路径越短」。设置面板只收「配置一次、之后不常改」的项——这条是持久取向。
- **子行排版归一 + 清死项**：子选项缩进统一到一个写法（`ConfigFormRow("", 控件)` 套 24px 缩进 wrapper，Interface 页既有做法），替换 Typesetting 与 App 页各一处手写的 `QHBoxLayout` + 写死 158/134；App 页 Developer channel 行删掉与常显 `⚠` 行逐字重复的 `?` 备注；Typesetting 的 `Quick insert characters` 独立成「Quick Symbol Palette」节。清项：删零引用字段 `pcfg.expand_font_format_panel`（`nested_dataclass` 忽略多余键，旧 config.json 不受影响）、修两处把工作台确认开关指向已不存在的「翻译器页」的注释、补上术语面板「不再提示」后回写设置页复选框的同步（`ConfigPanel.setupConfig` 只在启动跑一次，不回写会停在旧值）。
- **审计登记表新增 `dormant_symbols`**：普查发现 `ui/context_menu_config.py` 的右键菜单自定义对话框全仓无实例化（用户拍板本轮不接线也不删）。原有 `suspended` 是**文件级**契约，登记不了活文件里的一个符号，于是新增第三类（键 `路径::符号`）：文件里必须仍定义该符号，且定义文件之外全仓不得引用——一旦有人接线，检查失败并要求撤销登记，与 `deprecated` 的「残留引用必须清零」互为镜像。

**涉及文件：** `ui/run_pipeline_dialog.py`、`ui/configpanel.py`、`ui/drawingpanel.py`、`ui/glossary_agent_panel.py`、`ui/module_parse_widgets.py`、`utils/config.py`、`config/stylesheet.css`、`translate/zh_CN.ts`、`translate/zh_CN.qm`、`scripts/check_audit.py`、`scripts/audit_registry.json`、`.agents/skills/audit-docs/SKILL.md`、`tests/test_run_pipeline_dialog.py`、`tests/test_settings_app_page.py`（新）、`docs/技术实现/设置面板概述.md`、`docs/基础速查/设置面板排版思路.md`

---

## 2026-09-09

### 设置面板 LLM Profile 页改卡片式（A 方案·精简版）

**问题/需求：** 用户反馈设置面板开始堆屎山：LLM 页加入在线修复后比上游麻烦、管线页杂项排布乱。调研发现上游 1.5.14 走的是相反方向——管线合并成一页、LLM Profile 独立成卡片列表页（能力徽章 + 折叠详情 + 声明式分节），而 fork 是「下拉框 + 一张常显大表单」，所以每加一种能力页面必然变长。本批只做 LLM 页，形态对齐上游。

**改动要点：**

- **新增 `ui/llm_profile_cards.py`**：`LLMProfileListWidget`（工具栏 + 卡片列表）/ `LLMProfileCardWidget`（摘要 + 折叠详情）/ `LLMProfileDetailsWidget`（通用参数 + 三个能力分节，每节一个 `ParamWidget`）/ `LLMProfileBadge`（点击切换 `vision_support` / `image_support`）。参数定义走 `PROFILE_COMMON_PARAM_DEFS` / `PROFILE_SECTION_PARAM_DEFS`（镜像上游同名常量），写回类型转换走 `PROFILE_FIELD_TYPES`。
- **数据层不动**：`utils/profile_manager.py` 退为纯数据/服务层，保留 dict 模型、`model_profiles` JSON 字符串、name 作主键与全部消费者；不移植上游的 `LLMProfile` dataclass / SecretStore / id 主键。保存时机保持「增删 / 恢复内置 / Fetch 成功 / 离开页面才落盘」，避免敲键即触发 `module_manager` 重建参数面板。
- **删死代码**：`ProfileManagerDialog`（约 629 行，全仓无实例化）、`ProfileManagerWidget`（被新页取代）、`save_profile` / `delete_profile`（无调用者）与随之失效的导入；网络辅助改名公开（`NetWorker` / `probe_connection` / `probe_model_list`）供新 UI 复用。
- **接线**：`ui/configpanel.py` 换用 `LLMProfileListWidget`，注入 `_run_modal_dialog`（顺带修掉 profile 子对话框打开时 scrim 可点关整面板的旧问题）；`focusOnLLMProfile(name)` 现在会展开并滚动到对应卡片。
- **资源**：从上游拷 `icons/text.svg`、`eye.svg`、`image.svg`、`llm_key_ok.svg`、`llm_key_missing.svg`（上游禁用态与激活态形状相同，故只取 5 个，颜色改由 `render_svg_pixmap(override_fill=…)` 按主题与模态强调色着色）；`config/stylesheet.css` 追加 `LLMProfile*` 规则。
- **i18n**：删 `ProfileManagerDialog`（66 条）与 `ProfileManagerWidget`（69 条）两个 context，新增 `LLMProfileCardWidget`（58 条）/ `LLMProfileListWidget`（7 条）；中文译文复用 git 历史里旧 context 的既有术语并补齐余项，qm 重编。
- **测试**：`tests/test_startup_imports.py` 改为实例化 `LLMProfileListWidget`；新增 `tests/test_llm_profile_cards.py`（9 例：卡片数 / 初始折叠 / 徽章门控分节 / 字段写回与类型转换 / 内置禁删 / `hideEvent` 发信号 / 新增唯一名；写盘被 patch 掉以免污染真实 `config.json`）。

**涉及文件：** `ui/llm_profile_cards.py`（新）、`utils/profile_manager.py`、`ui/configpanel.py`、`config/stylesheet.css`、`icons/text.svg` 等 5 个图标（新）、`translate/zh_CN.ts`、`translate/zh_CN.qm`、`tests/test_startup_imports.py`、`tests/test_llm_profile_cards.py`（新）、`AGENTS.md`、`docs/技术实现/设置面板概述.md`、`docs/基础速查/设置面板排版思路.md`

### LLM 页模型切换对齐上游 + 上游 v1.5.13→v1.5.15 底层修复移植

**问题/需求：** 用户审查卡片页后反馈「单供应商切模型体验不好，上游做得到位」。调研上游 v1.5.15 的机制：每个 profile 持久化一份模型清单（`PROVIDER_DEFAULTS` 预置供应商模型表），摘要行常驻模型下拉 + 增删按钮，底部模块栏还能一键切模型；上游**没有** Fetch Models。用户拍板：吸收上游的清单 + 下拉，保留 fork 的 Fetch Models 并升级为多选添加，**不维护固化的模型表**（清单只由抓取或手填产生）。同批按「底层性能/实现优先服从上游」的原则，把 v1.5.13→v1.5.15 的底层修复移植过来。

**改动要点：**

- **模型清单（无内置表）**：profile 增 `model_options` / `image_model_options` 两个字段（`utils/profile_manager.py::PROFILE_FIELDS`、`SAMPLE_PROFILES` 全空）；`utils/profile_manager.py::normalize_model_options` 在 `load_profiles` 时规整清单并把当前值补进列表，`utils/profile_manager.py::remember_model_option` 负责去重追加。存储格式与消费者（仍读 `profile["model"]`）不变。
- **摘要行模型下拉**：新增 `ui/llm_profile_cards.py::_ModelSelector`（`ConfigComboBox` 拉伸模式 + `+` 手填 / `−` 删当前），文本模型常显、图像模型随 `image_support` 显隐；`model` / `image_model` 从详情参数里移除（不再有双入口），`_rebuild_details` 随之删除。切模型 / 增删是离散操作，立即落盘（`ui/module_manager.py::_on_profiles_changed` 只刷新类级选项，代价小）。
- **Fetch Models 多选**：`utils/profile_manager.py::FilterableListDialog` 增 `multi_select`（`ExtendedSelection` + `selected_items`）；`ui/llm_profile_cards.py::_pick_model` 把选中项全部入清单、首个设为当前模型并落盘——网络只用于刷新清单，之后切模型完全离线。
- **控件库**：`ui/custom_widget/combobox.py::ConfigComboBox` 增 `stretch` 参数（不做宽度分级锁定，交给布局横向拉伸）；`config/stylesheet.css` 补 `LLMProfileModelRow` / `LLMProfileFieldLabel` / `LLMProfileModelAddButton` / `LLMProfileModelRemoveButton` 规则。
- **上游底层修复移植**：①效果栈瓦片——`ui/text_engine/rendering/raster.py::plan_effect_raster` 补取整余量（`-1`）与随缩放分层的 `tile_tier`，`ui/text_engine/effects/renderer.py::_draw_tiled_effects` 整块 staging 超光栅策略时不再抛错丢弃，改为逐瓦片裁剪直接绘制（大窗口 / 大描边半径下效果不再整块消失，上游 9b34135 + e88c655）；②LaMa 预处理改「补边对齐」而非重采样（`modules/inpaint/base.py`，上游 b36210b，保住网点与遮罩边缘）；③16-bit 灰度 PNG 读入取高字节（`utils/io_utils.py::imread`，上游 afad9f5）；④`ParamLineEditor` 的 `QDoubleValidator` 固定 C locale（`ui/module_parse_widgets.py`，上游 73741cf）；⑤Ctrl+C/V/X 改 `QKeySequence.StandardKey` 匹配（`ui/canvas.py`、`ui/text_engine/item.py`，上游 a86ebb1）；⑥水平排版单个空格软换行不再跳动（`ui/text_engine/horizontal_layout.py::_trailing_space_layout`，上游 595f6fd）。
- **画笔粗细**：`ui/custom_widget/slider.py::Slider` 抽出 `_value_to_position_ratio` / `_position_ratio_to_value` 两个映射钩子（默认线性，groove 绘制与命中测试都走它）；`ui/drawingpanel.py::_BrushThicknessSlider` 重载为对数映射（小笔头不再挤在左端，数值仍是精确像素），`ui/drawingpanel.py::_create_thickness_control` 给两个画笔面板配 `NoArrowsSpinBox` 精确输入（双向同步，滑块程序化 setValue 也同步输入框）。
- **未移植**：合成粗体（用户不感兴趣，此前已决定删除该特性）、上游 LLM 上下文/记忆/全页 OCR/PS Bridge/HayaiOCR/多语言 ts（依赖上游 `LLMProfile` 数据模型或方向相反）。
- **测试**：`tests/test_llm_profile_cards.py` 扩到 18 例（清单只有当前值 / 下拉写回 / 手填追加 / 删当前选邻居 / Fetch 多选全入列 / 图像行随徽章显隐 / 数据层归一与对话框多选）；新增 `tests/test_image_io.py`（16-bit PNG）、`tests/test_effect_raster_policy.py`（瓦片余量 + tier 分层）、`tests/test_brush_thickness.py`（对数映射 + 精确输入框）。verify.py --full 全绿。

**涉及文件：** `ui/llm_profile_cards.py`、`utils/profile_manager.py`、`ui/custom_widget/combobox.py`、`ui/custom_widget/slider.py`、`ui/drawingpanel.py`、`ui/text_engine/effects/renderer.py`、`ui/text_engine/rendering/raster.py`、`ui/text_engine/horizontal_layout.py`、`ui/text_engine/item.py`、`ui/canvas.py`、`ui/module_parse_widgets.py`、`modules/inpaint/base.py`、`utils/io_utils.py`、`config/stylesheet.css`、`translate/zh_CN.ts`、`translate/zh_CN.qm`、`tests/test_llm_profile_cards.py`、`tests/test_image_io.py`（新）、`tests/test_effect_raster_policy.py`（新）、`tests/test_brush_thickness.py`（新）、`docs/技术实现/设置面板概述.md`、`docs/基础速查/设置面板排版思路.md`

### LLM 页与修复面板实机反馈五修

**问题/需求：** 上一批落地后实机验收提出五处：①摘要行模型下拉横向拉满整行，看着空且怪；②主机地址 / API Key 埋在杂项参数里不够显眼，图像修复端口也应并到一处；③画笔粗细的精确输入框挤占了滑条，滑条太短；④AI 修图页的比例提示被横向裁掉，且长句不如表格；⑤生图模型需要可手动输入（中转站可用性检查常误报）。

**改动要点：**

- **模型下拉按内容自适应**：`ui/llm_profile_cards.py::_ModelSelector` 去掉 `stretch`，改 `ConfigComboBox(fix_size=False)` + `AdjustToContents`（受分级上限兜底），`+` / `−` 紧跟其右并留尾部空白。
- **连接信息块**：新增 `ui/llm_profile_cards.py::_ConnectionBlock`（`CONNECTION_PARAM_KEYS` 定序 `api_host` / `api_key` / `image_base_url`），标签在上 + 整行加高输入框（`LINEEDIT_FIXHEIGHT`），容器带强调左边条（`LLMProfileConnectionBlock` QSS）；`image_base_url` 随 `image_support` 显隐（`set_section_visible("image", …)` 同步）。这三个字段从 `PROFILE_COMMON_PARAM_DEFS` / 图像分节移出，详情页改为「连接信息 + 生成参数 + 三能力分节」。
- **画笔粗细滑条恢复原长**：`ui/drawingpanel.py::_create_thickness_control` 改为 `(slider, spinbox, row_layout)`，数值框（宽 56）放进标签列右端、标签可省略（`_ElidedToolNameLabel`），滑条独占其余宽度——实测 86px → 166px（与加精确输入前一致）。
- **AI 修图页比例支持表 + 裁剪修复**：面板最小宽从 388px 降到 253px（可用约 326px）。三处根因：`CropControls` 把「裁剪模式」复选框和比例下拉挤在同一行（改为独立一行）；`QComboBox` 默认把**最长条目宽度**算进 `minimumSizeHint`，长 profile / 模型名把面板顶宽——新增 `ui/drawingpanel.py::_shrinkable_combo`（`AdjustToMinimumContentsLengthWithIcon` + `minimumContentsLength(0)`）处理面板内所有下拉；整句比例说明换成 `InpaintAspectTable` 紧凑表格（模型 / 支持比例两列 + 其它模型脚注），比例单元格 `setWordWrap(True)` 窄栏换行而非撑宽。
- **生图模型栏**：`ui/drawingpanel.py::AIConfigPanel` 在 Profile 下新增可编辑下拉（清单取所选 profile 的 `image_model_options`，`activated` / `editingFinished` 才提交），`_commit_image_model` 写回该 profile 的 `image_model` 并记进清单（`save_all_profiles`）。跨页写同一 profile，故 `ui/llm_profile_cards.py::LLMProfileListWidget.showEvent` 在 `pcfg.module.model_profiles` 与上次落盘值不一致时重载，避免旧副本在 `hideEvent` 覆盖。
- **i18n**：新增 `Connection` / `Generation` / `Model` / `Ratios` / `Other models follow the Nano Banana set.` / `Image Model` / `Model name` 七条（中文：连接信息 / 生成参数 / 模型 / 支持比例 / 其它模型按 Nano Banana 的比例集处理。/ 生图模型 / 模型名称），删掉旧整句比例说明的孤儿条目，qm 重编。
- **测试**：`tests/test_llm_profile_cards.py` 扩到 23 例（模型下拉非拉伸且有上限 / 连接块承载 host+key / 连接块写回 / 图像端口随徽章显隐 / `showEvent` 重载外部改动）；`tests/test_brush_thickness.py` 补「数值框在标签列内、滑条独占其余宽度」断言；新增 `tests/test_ai_inpaint_panel.py`（6 例：模型清单 / 手输与点选写回 profile / 比例表内容 / 比例单元格换行 / 面板最小宽 ≤ 326）。

**涉及文件：** `ui/llm_profile_cards.py`、`ui/drawingpanel.py`、`config/stylesheet.css`、`translate/zh_CN.ts`、`translate/zh_CN.qm`、`tests/test_llm_profile_cards.py`、`tests/test_brush_thickness.py`、`tests/test_ai_inpaint_panel.py`（新）、`docs/技术实现/设置面板概述.md`、`docs/基础速查/设置面板排版思路.md`

### 修复面板实机反馈收尾：数值框去单位 + 按钮内边距 + 对齐普查

**问题/需求：** 五修验收后用户反馈三点：①粗细数值框里的 `20 px` 被裁成 `20 p`，干脆去掉单位；②「修复 / 清除遮罩」按钮字紧贴边框；③顺带看看还有没有边距不合适或该对齐没对齐的地方。

**改动要点：**

- **数值框去单位**：`ui/drawingpanel.py::_create_thickness_control` 去掉 `setSuffix(" px")`（宽度 56 不变，够显示 4 位数）。
- **按钮内边距**：stylesheet 新增 `DrawingPanel QPushButton { padding: 0 12px; }`——全局 `QPushButton` 无内边距，中文两字按钮的 sizeHint 就等于文字宽（实测 30px 宽装 28px 文字）。
- **对齐普查**（实测离屏渲染 + 真实字号/译文逐控件量 x）：①内嵌体（画笔体 / 框选体 / `CropControls`）的布局 margins 归零，原来默认 9px 让这一组比上方字段整体右移；②粗细滑条行不再自设 `spacing(10)`，沿用父布局 14px，滑条起点与同栏下拉框同列（原来差 4px）；③`_shrinkable_combo` 统一锁高 `CONFIG_COMBOBOX_HEIGHT`（默认 29 vs 26 参差），修复工具下拉框（属设置页控件）在 `DrawingPanel` 构造时补锁一次；④框选页 `box_layout` 行距 8 → 14，与画笔 / AI 页同节奏。
- **测试**：`tests/test_brush_thickness.py` 断言改为「无后缀」；`tests/test_ai_inpaint_panel.py` 补 2 例（滑条与下拉同列 / 面板按钮有内边距，含 `DrawingPanel` 类名一致性守卫）。

**涉及文件：** `ui/drawingpanel.py`、`config/stylesheet.css`、`tests/test_brush_thickness.py`、`tests/test_ai_inpaint_panel.py`、`docs/基础速查/设置面板排版思路.md`

---


## 2026-09-08

### 效果栈滤镜批收尾 + 实机验收反馈批（渲染错乱四修 / 描边卡退役 / 取色器换 fork 控件 / 行距类型并入轮廓行）

**问题/需求：** 上午批（滤镜族落地 + 滤镜输出被未滤镜原文字叠回修复，见效果栈移植计划文档状态段）之后，用户实机验收反馈四项：①按钮等处渲染错乱 + 吸色器仍走 win 原生；②行距类型下拉移到轮廓行同一行、移植的独立描边卡删除（实现重复）；③渐变卡缺少选色交互（附截图）；④噪点/颗粒滤镜无效果（用户核对上游同样如此）。全部处理完毕并实机验收通过。

**改动要点：**

- **渲染错乱根因（离屏截图台逐卡实锤，`tmp/panel_visual.py` 法）**：Fill 行 Fill 类型选择器（`Ignored` 伸缩策略）与 stretch=1 色块同行被压成 0 宽静默消失——`ui/text_engine/effects/cards.py::_set_effect_selector_width` 加 72px 下限；描边卡色块永不渲染（唯一漏调 `paint_button.set_paint` 的卡，随卡退役消失）；"Fill" 漏翻英文 = mixin 里 `self.tr('Fill'/'Solid'/'Gradient')` 运行时上下文是各卡类名、提取器按物理位置归 `_EffectCardMixin`，词条两边永不相交——按项目惯例改 `QCoreApplication.translate('TextEffectPanel', …)` 显式上下文（ts 三词条迁移 + qm 重编）。
- **渐变卡选色交互**：`ui/text_engine/effects/cards.py::TextFillEffectCard` 的 `InlineLinearGradientEditor` 被 `_connect_gradient_editor` 末尾统一 `hide()` 且无人再 show，编辑器（停点条/停点色块/加减停点/角度缩放）永久隐藏——渐变卡内改为常显。
- **取色器换 fork 自研**：效果卡 solid 色块（`ui/text_engine/effects/cards.py::_on_paint_clicked`）与渐变停点色块（`ui/text_engine/effects/gradient_editor.py::_choose_stop_color`）从 `QColorDialog` 换 `ui/custom_widget/color_picker.py::ColorPickerDialog`（PS 式 + 屏幕吸色管）；停点色实时预览经 `colorChanging` 信号，accept/reject 对应 commit/cancel，预览-提交语义不变；`_build_paint_row` 的 dialog title 参数随之清理。
- **独立描边卡退役**（用户拍板与主面板轮廓行重复）：删 `StrokeEffectCard` 类、panel Add 菜单 'stroke' 项、`ui/text_engine/effects/edit_session.py::add_effect` stroke 构造分支、描边图标 SVG（登记 audit_registry deprecated）。栈内 `StrokeEffect` 仍是活模型——轮廓行经 legacy 视图读写、渲染不变；`_rebuild_effect_cards` 对 'stroke' 键跳过建卡。
- **行距类型并入轮廓行**：`ui/text_panel.py` 撤销 Row 3.5 独立行，行距类型下拉并入描边行右端（轮廓 [宽度][色块] 行距类型 [比例˅]）。
- **噪点/颗粒「无效果」诊断**：机制实锤——两者只改字形内部像素，修复前的完成正面契约下未滤镜原文字精确盖回输出（剩余 129/76 个边缘像素不可感知），模糊/光晕有字形外光晕故「有效」；与用户「上游同样如此」吻合（上游同结构）。**已随上午的 `ui/text_engine/effects/renderer.py::_renders_completed_foreground` 修复（enabled Filter 计入拥有正面）一并解决**，当前树实机验收可见；新增 `tests/test_text_effects_filter.py::test_in_glyph_filters_replace_native_foreground` 钉住（>1000 像素变化阈值，防仅边缘残留的假绿）。
- ts 清理 16 条孤儿（StrokeEffectCard 上下文整块/废弃 dialog title）+ 补 2 条；verify/pytest 全绿。

**涉及文件：** `ui/text_engine/effects/cards.py`、`ui/text_engine/effects/panel.py`、`ui/text_engine/effects/edit_session.py`、`ui/text_engine/effects/gradient_editor.py`、`ui/text_panel.py`、`ui/text_engine/effects/renderer.py`（上午批）、`icons/text-effect-stroke.svg`（删）、`scripts/audit_registry.json`、`translate/zh_CN.ts`、`translate/zh_CN.qm`、`tests/test_text_effects_filter.py`、`docs/技术实现/效果栈移植与窄栏图标重绘_计划.md`

### 效果栈二批：描边只走栈 + 全卡渐进披露 + 三轮实机反馈修复

**问题/需求：** 用户先提「常驻轮廓行管外形 + 效果卡管顺序」的双视图方案，调研后改为上游单卡模式（描边只走栈，顺序与位置/混合等高级参数都要卡片承载）。视觉减法要求做渐进披露：高频参数常显、低频项收进默认收起的「高级」子层、展开状态不记忆。随后三轮实机验收反馈全部处理完毕并验收通过。

**改动要点：**

- **描边只走栈**：删右栏常驻描边行（`ui/text_panel.py::FontFormatPanel` 宽度框/取色器，行距类型下拉独立成行）与 `stroke_width_presets` 预设配置；`StrokeEffectCard` 从 git 取回并接回 Add 菜单/分发/构造器，描边取色即置 `stroke_color_custom`（`edit_session.py::TextEffectEditSession`），避免被自动反色冲掉。
- **渐进披露机制**：`cards.py::_AdvancedDisclosure`（20px 折叠行，chevron + 「高级」+ 非默认值圆点）；mixin `_build_advanced_section` 把低频参数网格包进默认收起容器，卡片 `geometry_changed` 接 `TextEffectPanel._sync_content_height` 重算量程。分层：描边=宽度/位置/颜色常显；阴影/发光=类型/几何/颜色常显；渐变卡=渐变条常显；滤镜卡无折叠行。
- **第一轮修复**：渐变停点取色崩溃（移植漏 `_replaced_selected_stop`，编辑器此前永久隐藏故未暴露）；色块压住 Fill 下拉（`Ignored` 策略向布局上报零宽度，改 `Preferred`）；下拉双箭头（自绘 chevron 的控件补关原生 `::down-arrow`/`::menu-indicator`）。
- **第二轮修复**：折叠栏隐藏按钮退役（`view_panel.py::ExpandLabel` 加 `hide_button`，变换面板同款老 hack 一并删）；旧字段活体写入不再凭空建 0 宽描边卡（`utils/fontformat.py::FontFormat` 的 `srgb`/`stroke_width=0` 分支）；Add 菜单白名单补 `'stroke'`；效果卡数值框改 Blender 式箱体拖拽（`cards.py::EffectNumericControl` 自装事件过滤器复用 DRAG_PREVIEW 状态机，实时预览与单次提交不变；`transforms/panel.py::TransformDragLabel` 加 `drag_enabled` 让标签退为纯描述）；无单位效果参数上限统一 `utils/text_effects.py::EFFECT_MAGNITUDE_LIMIT=1.0`（校验上限仍 10 以兼容旧工程，滤镜补 ` px` 后缀并用测试钉住不变量）。
- **第三轮修复**：取色器加 `alpha=True` 模式（纵向 alpha 滑条 + A 数值 + 棋盘底），渐变停点不透明度改由取色器 alpha 承担（`gradient_editor.py` 停点色块铺棋盘底）；描边自动反色由「改字色实时联动」改为「添加描边时取一次反色后保持手动」（`TextBlkItem.setFontColor` 的实时分支移除，设置面板文案同步）。
- **验证**：`tests/test_text_effects_cards.py`（15 条）、`tests/test_text_effects_stroke_follow.py`（4 条）、`tests/test_screen_picker.py` alpha 用例；`verify.py --full` 全绿（649 passed / 1 skipped）。

**涉及文件：** `ui/text_engine/effects/cards.py`、`ui/text_engine/effects/panel.py`、`ui/text_engine/effects/edit_session.py`、`ui/text_engine/effects/gradient_editor.py`、`ui/text_engine/effects/filters/filter_grain.py`、`ui/text_engine/transforms/panel.py`、`ui/custom_widget/view_panel.py`、`ui/custom_widget/combobox.py`、`ui/custom_widget/color_picker.py`、`ui/text_engine/item.py`、`ui/text_panel.py`、`ui/configpanel.py`、`utils/fontformat.py`、`utils/text_effects.py`、`utils/config.py`、`config/stylesheet.css`、`icons/text-effect-stroke.svg`、`scripts/audit_registry.json`、`translate/zh_CN.ts`、`translate/zh_CN.qm`、`tests/test_text_effects_cards.py`、`tests/test_text_effects_stroke_follow.py`、`tests/test_screen_picker.py`、`AGENTS.md`、`docs/技术实现/效果卡渐进披露_验收清单.md`、`docs/技术实现/效果栈移植与窄栏图标重绘_计划.md`

### 控件样式展示台升级为「控件地图」+ 覆盖门禁 + 闪退修复

**问题/需求：** 用户要求把已有的 `scripts/style_showcase.py`（原生 vs 封装对照 + 控件一览）继续完善成「排列展示项目用到的所有控件、方便查找和指定优化」的工具。讨论后拍板四项：①展示范围扩到应用层复合控件；②每行 `路径::符号` + 一键复制、搜索框 + 目录跳转、样式来源标注、亮暗主题 + 状态矩阵；③加静态覆盖校验。实施后用户实机验收时点开关闪退，一并修复并补一键启动 bat。

**改动要点：**

- **范围与分区**：72 行控件，除 `ui/custom_widget` 全量（补齐此前缺的 `ComboBox`/`FlowLayout`/`SizeControlLabel`/`SmallSizeControlLabel`/`ScrollBar`）外纳入应用层复合控件，按「用在哪个面板」分区：配置面板（`ui/configpanel.py::ConfigSubBlock` 等）、模块参数表单（`ui/module_parse_widgets.py::ParamWidget` 族）、文本格式面板（`ui/style_format_editor.py::FieldEditor`）、变换面板（`ui/text_engine/transforms/panel.py::CommittedTransformControl`）、效果栈（`ui/text_engine/effects/cards.py::StrokeEffectCard` 等）、样式管理器与饼菜单。无法离线实例化的进 `EXCLUDED` 字典，渲染成「未纳入展示」分区并写原因。
- **指定优化能力**：每行右侧固定簇 = 样式来源徽章（`_style_source()` 自动判定 类名/objectName/自绘/内联/全局兜底/无规则，决定改 QSS 还是改代码）+ `路径::符号`（可省略中段、tooltip 全量）+ 一键复制；工具栏含搜索、样式来源筛选、亮暗主题切换、状态矩阵（`_grab_state()` 用 `WA_DontShowOnScreen` 宿主 + `setFocus()` 抓悬停/聚焦态，按 sizeHint 自然尺寸渲染，2×2 网格排布）。
- **闪退根因（用户实机点开关触发）**：`_grab_state` 必须 `processEvents()`，重建耗时期间再点「状态矩阵」/切主题会**重入** `rebuild()`——内层 `scroll.setWidget()` 删掉外层已登记区块，外层 `_rebuild_index()` 拿到已析构 QWidget → `RuntimeError: wrapped C/C++ object ... has been deleted`。修法=重入守卫（`_rebuilding`/`_rebuild_pending`，重入只记待办、当前重建结束后补跑一次）+ `_rebuild_index` 加 RuntimeError 防御。
- **零痕迹保护**：切主题走 `reverse_icon=True` 会就地重写 `icons/*.svg`；启动快照全部 svg 原始字节，`aboutToQuit` 逐字节还原（不用「按主题色反推」——`icons/text-effect-stroke.svg` 的提交态填充色与其他图标不一致，映射会留 diff）。同时调用 `utils/safe_qt.py::install_qt_warning_filter` 屏蔽「字号<=0」良性噪音。
- **覆盖门禁**：新增 `scripts/check_showcase.py`（纯 AST，比对 `ui/custom_widget/__init__.py` 导出清单 vs 展示/`EXCLUDED` 登记，漏登/重复/陈旧即失败），并入 `scripts/verify.py` 每次执行；`tests/test_showcase_coverage.py` 复用同一 `find_problems()`。
- **顺带修两处文档漂移**：`docs/基础速查/打包控件功能使用说明.md` 速查表删除幽灵条目 `FadeLabel`（`ui/custom_widget/label.py` 已无此类，裸符号名 check_docs 查不到）；展示台 EXCLUDED 曾把 `ScrollBar` 误标「旧版遗留」，实际 `ui/canvas.py`/`ui/textedit_area.py` 在用，改为展示行。
- **一键启动**：`scripts/style_showcase.bat`（优先便携解释器，退回 `py`/`python`，非零退出码才 pause；仓库根/scripts 内/任意目录绝对路径三种调用方式均已实测）。**批处理必须纯 ASCII**——cmd 按 ANSI 解析 .bat，中文注释在 `chcp 65001` 生效前就乱码并吞掉下一行 `set`。

**验证：** `scripts/style_showcase.py --selftest` 72 行 0 失败；`scripts/verify.py` 全绿（含新增「展示台覆盖」步骤）；`tests/test_showcase_coverage.py` 通过；暗色/亮色/搜索过滤/状态矩阵/各分区逐屏截图核对，横向溢出消除。

**涉及文件：** `scripts/style_showcase.py`、`scripts/check_showcase.py`（新）、`scripts/style_showcase.bat`（新）、`scripts/verify.py`、`scripts/README.md`、`tests/test_showcase_coverage.py`（新）、`docs/基础速查/打包控件功能使用说明.md`、`docs/项目概述.md`、`scripts/audit_registry.json`、`AGENTS.md`

### 效果块框选：闪原生小窗 + 掉帧两项修复

**问题/需求：** 用户报告：文本框带特效时，画布左键拖拽多选扫过该块会不断闪出秒关闭的 Win 原生小窗（补充：不出现在任务栏，形态像设置面板）；修复后弹窗消失，但带样式的块框选仍明显掉帧（无特效的块选很多个都不卡）。两项均已实机验收通过。

**改动要点：**

- **闪窗根因**：`ui/text_engine/effects/panel.py::TextEffectPanel._clear_effect_cards` 对**处于显示状态**的卡片直接 `setParent(None)`——Qt 会把可见控件变成顶层窗口并 show 出来，直到随后的 `deleteLater()` 才销毁，于是框选每步重建卡片都闪一排原生小窗。修法=先 `hide()` 再摘父级再 `deleteLater()`；`ui/text_engine/transforms/panel.py::TextTransformPanel._clear_transform_panels` 同款隐患一并修（它未暴露是因为浮层常关着，`isVisible()` 为 False）。
- **掉帧根因**：`ui/canvas.py::Canvas.apply_box_selection` 每步 `clearSelection` + 全量重选 → 一步 2–4 次 `selectionChanged` → `ui/text_panel.py::FontFormatPanel.set_textblk_item` → 效果卡整组重建（5 张卡约 30 个控件，含按钮菜单与渐变编辑器）。真实工程 40 步扫掠实测：无特效 10.5→4.9 ms/步，带特效 22.9→5.4 ms/步；带特效块的 `paint` 仅 +0.4 ms/步，瓶颈在面板重建而非渲染。
- **修复**：新增 `ui/canvas.py::Canvas._box_select_panel_sync_paused`，拖拽期间在 `ui/canvas.py::Canvas.on_selection_changed` 压住 `incanvas_selection_changed`，松手在 `ui/canvas.py::Canvas.hide_rubber_band` 补发一次，`ui/canvas.py::Canvas.updateCanvas` 复位防卡死；单击选中仍即时同步。
- **护网**：`tests/test_text_effects_cards.py::test_clear_effect_cards_hides_before_detaching`（打桩 `setParent` 断言摘父级时已隐藏）；`tests/test_box_select.py` 两条（拖拽期间不发信号 + 松手补发一次、单击仍即时）。
- 两项均记入 `docs/基础速查/经验教训.md` §3.4/§3.5。

**验证：** `scripts/verify.py` 全绿；pytest 661 passed / 1 skipped。

**涉及文件：** `ui/canvas.py`、`ui/text_engine/effects/panel.py`、`ui/text_engine/transforms/panel.py`、`tests/test_box_select.py`、`tests/test_text_effects_cards.py`、`docs/基础速查/经验教训.md`、`docs/daily_log.md`

---

## 2026-09-06

### 撤销体系阶段 4 第三批落地：图像修复并入全局撤销栈（3a 同区域聚合 + 3b 单一栈双视图）+ 修复区历史入口窄栏化

**问题/需求：** 用户实测第三批前状态：修复区改动在文本区历史面板不可见、须跳修复区撤销、切页丢历史。按计划 §五实施：3a（同区域连续修复聚合，随 cd2e364 先行提交）+ 3b（修复命令并入全局栈）。3b 实机验收两轮反馈：①点击修复区历史图标闪退；②入口占工具行激活态且图标不齐，用户建议改窄边侧栏。全部验收通过。

**改动要点：**

- **修复命令入全局栈**：`ui/drawing_commands.py::InpaintUndoCommand` 类标记 `image_history=True`，`ui/canvas.py::push_undo_command` 先于模式分流到 `push_image_command`；涂鸦留页级绘制栈（可推翻点）。undo/redo 补页代数自守卫（僵尸无操作）。
- **图像代数独立计数**：`utils/proj_imgtrans.py::page_image_generation`/`bump_page_image_generation` 与文本代数分开（共享计数器会互相误杀）；`ui/textedit_commands.py::command_page_stale` 按属性分支比对。bump 点：检测/修复管线直写（`ui/module_manager.py`）、切页/重渲离页时图像侧仍脏（`ui/mainwindow.py`；条件保存成功不触发——磁盘重载精确复现保存点，跨页往返历史存活）。
- **图像脏记账**：第二对计数器 `num_imgstep`/`saved_imgstep`（不变量=全局栈 [0,index) 图像命令数），驱动 `draw_change_unsaved`（修复图/遮罩落盘门语义不变）；`push_image_command` 处理 undoLimit 截断平移（公式 `index0 + 1 - 新 count`，恰好隔离前端截断）。
- **撤销路由**：绘制模式涂鸦栈可动则涂鸦栈、否则回退全局栈（跨模态）；右键菜单 enabled 判定（`ui/context_menu_config.py`）与历史 toast（`_active_history_stack`）同路由。
- **修复区历史入口（验收返工定稿）**：DrawingPanel 左缘 `ui/panel_rail.py::PanelRail` 窄栏图标 + `RailDockPanel` 惰性创建（构造期 rail.window() 不可靠），开合记忆 `pcfg.inpaint_history_dock_open`（已声明+进启动清名单）；切文本区浮层随隐保留状态、切回恢复。初版工具行图标 + FloatDropPanel 闪退根因：构造期 toolboxlayout 未上树 → `anchor.parentWidget()` 为 None → `_place` 对 None.mapTo 抛 AttributeError（PyQt6 槽内未捕获异常 qFatal）；`ui/custom_widget/float_drop_panel.py` 补 `_edge` 惰性解析（GlobalSearchWidget 仍用其）。
- **历史面板过滤视图**：`ui/history_panel.py::HistoryPanel` 新增 `image_filter` 模式——只显示当前页修复命令、顶部跨页提示；行号=全局栈位置，绘制模式跳转强制 `_text_undo_step/_text_redo_step`（涂鸦优先路由会截胡）。
- **侧栏浮层拖拽三向化（验收反馈）**：`ui/custom_widget/rail_dock_panel.py` 删左下角斜纹手柄图标，改左缘/下缘/左下角三向隐形拖拽区（专用子控件承载事件——面板本体被 body 子控件覆盖，边缘事件到不了 self；光标形状即提示）。
- **历史条目悬停修复（验收反馈）**：hover 从未生效的根因=自定义 paint 短路了 QSS `::item:hover`；delegate 补 `@hoverBackgroundColor` 悬停底色，当前位行 Highlight 底色上加粗。
- **护网**：`tests/test_undo_inpaint_global.py`（新 10 条）；`tests/test_inpaint_undo_merge.py` 迁移到全局栈路由；`tests/test_panel_rail.py` 手柄测试改三向拖拽；演练台场景验证入口开合/随隐/恢复全链路。

**涉及文件：** `ui/drawing_commands.py`、`ui/canvas.py`、`ui/textedit_commands.py`、`utils/proj_imgtrans.py`、`ui/module_manager.py`、`ui/mainwindow.py`、`ui/context_menu_config.py`、`ui/drawingpanel.py`、`ui/history_panel.py`、`ui/text_panel.py`、`utils/config.py`、`ui/custom_widget/float_drop_panel.py`、`ui/custom_widget/rail_dock_panel.py`、`config/stylesheet.css`、`translate/zh_CN.ts`、`tests/test_undo_inpaint_global.py`（新）、`tests/test_inpaint_undo_merge.py`、`tests/test_undo_group_confirm.py`、`tests/test_panel_rail.py`、`docs/技术实现/撤销体系阶段4计划.md`

---

### 挂账清理批次：加粗拖拽残留 / 攸望竹竖排撑爆 / 饼菜单灰显 / PSD 导出删除 / face 元组崩溃 / 历史面板自开

**问题/需求：** 记忆挂账批量清理 + 用户实机新报两 bug。全部经实机验收。

**改动要点：**

- **设置面板导航加粗拖拽残留**：`ui/configpanel.py::ConfigTable.selectionChanged` 以 `currentIndex()` 作加粗目标，但 Qt 按住拖拽路径下 select 信号先于 current 更新发出（滞后一拍），旧项被清粗体后又被重新加粗且无后续清理路径。改用本次真正选中的项（`selected.indexes()[0]`）。
- **攸望竹带体竖排撑爆（方案 B）**：`ui/text_engine/layout.py::get_punc_rect` 加 `_rect_is_sane` 防护——DirectWrite 对零 advance 字形返回近 1e5 哨兵矩形，超字号 50 倍判退化回退 `boundingRect`，缓存层生效横竖排全覆盖。新增 `tests/test_punc_rect_sentinel.py`（mock 哨兵，offscreen 无法真复现）。
- **饼菜单 used 灰显恢复**：2026-08-16 因实机不生效下线的视觉已恢复——`[used="true"]` QSS 规则加回 `ui/pie_menu_editor.py::CommandPalette.set_commands`，且不再单靠后代选择器刷新（当年实机根因）：`_CommandCard.set_used` 对 name_label 内联直接套 disabled_clr + 卡片及子控件一并 unpolish/polish。实机确认生效。
- **PSD 导出功能整体删除**：JSX 路线实机问题无法收敛，等更强的 AI 修复能力再重启。删 11 文件（utils/psd_* 7 个 + font_mapping + ui/psd_export_dialog + 两个测试），连带清 mainwindow/mainwindowbars/io_thread 死线程/text_style_dock 提示/ts 条目/manifest 重生成；技术状态存档 `docs/技术实现/PSD导出_存档.md`（重启凭据=git fd90b31）；全部登记 audit_registry deprecated。`FONT_PS_NAMES` 保留（一键精简别名补录消费）。原技术文档已于 09-02 先行删除，存档文档为重启唯一凭据。
- **face_resolver 元组崩溃（实机报错）**：`utils/face_resolver.py::resolve_face` 多候选并列兜底分支 `min(candidates, key=...)` 返回整个 `(名,字重,斜体)` 元组而非 `f[0]` 名字，写入 `_style_name` 后下游 `findText(tuple)` 崩。补 `[0]`；`utils/fontformat.py::__post_init__` 加非 str 归一（防已落盘的 JSON 数组残留）；回归测试入 test_face_resolver。
- **历史面板启动自开**：`ui/mainwindow.py` 启动清 `*_dock_open` 清单漏了阶段 4 新增的 `history_dock_open`，上次会话的开合记忆复活。补入清单。
- **ConfigComboBox(options=) 构造参数**：原只支持「先构造再 addItems」，构造期传 `options=` 直接 TypeError。`ui/custom_widget/combobox.py` 构造函数接受 `options=`（等价构造后 addItems）。回归测试 `tests/test_config_combobox_options.py`（新）。
- **杂项清理**：删 `.git/backup-stale/`（08-13 仓库损坏事件的 88MB 残留包，远端恢复早已验证）；AGENTS.md/项目概述清掉「scene_textlayout.py 已废弃待删」过时描述（实际已随 a629ca5 删除）。

**涉及文件：** `ui/configpanel.py`、`ui/text_engine/layout.py`、`tests/test_punc_rect_sentinel.py`（新）、`ui/pie_menu_editor.py`、`scripts/pie_menu_test.py`、`utils/face_resolver.py`、`utils/fontformat.py`、`tests/test_face_resolver.py`、`ui/mainwindow.py`、PSD 批次（`utils/psd_*.py`×7、`utils/font_mapping.py`、`ui/psd_export_dialog.py`、`tests/test_psd_*.py`×2、`ui/io_thread.py`、`ui/mainwindowbars.py`、`ui/text_style_dock.py`、`utils/shared.py`、`tests/test_font_scan.py`、`docs/技术实现/PSD导出_存档.md`（新）、`docs/项目概述.md`、`docs/技术实现/反向移植_规范.md`、`scripts/audit_registry.json`、`manifest.json`、`translate/zh_CN.ts`）

---

### 撤销体系阶段 4 第二批落地：跨页批量组化 + 撤销确认弹窗（含 GC 悬空闪退修复）+ MainWindow 在线演练台

**问题/需求：** 三批节奏的第二批（决策 4）：整理换行/高级对齐等跨页批量命令撤销前弹确认框。用户另拍板两事：修复历史并入全局栈定稿（第三批方案，单一栈双视图+端点快照）、不常用功能工具箱收纳另立规划。本批已实机验收。

**改动要点：**

- **组化标记**：`ui/textedit_commands.py::NormalizeBreaksCommand` 与 `ui/mainwindow.py::_PointAlignCommand` 暴露 `group_undo_summary()`（页名→块数）+ `group_page_generations` 构造期多页代数快照——任一涉及页被管线重写即整组僵尸化（此前只查标签页，跨页端点快照会写错块）；`command_page_stale` 对组化命令逐页比对。
- **撤销确认门**：`ui/canvas.py::_confirm_group_undo`——跨页组命令 undo 前弹确认框（标题=操作名、每页块数明细、勾选「同时重渲染」）；拒绝则本步不执行。豁免三路：僵尸步、历史面板跳转（auto_cross_page）、仅影响当前页；redo 不设确认。
- **「同时重渲染」保留撤销历史**：`_rerender_dirty_pages` 加 `clear_history` 参数，组化撤销路径传 False（数据未变仅重渲，清栈会丢 redo 能力）；既有调用方不变。
- **标脏补缺**：两条组化命令 redo/undo 对非当前涉及页 `mark_page_needs_rerender`（此前改他页数据不标脏）；**`_PointAlignCommand` 补齐锚点化**（item 引用改 blk 身份，执行期 `resolve_blk_item` 重解析——原实现重放到场景重建后的隐形 item）。
- **闪退修复（实机验收发现，GC 悬空 AV）**：确认弹窗复选框无父构造传 `setCheckBox` 不留引用 → PyQt6/Qt6.11 下被 GC 回收 → 悬空指针 access violation 无声闪退，AV 行号随 GC 时机漂移极难定位。修复=构造期挂父 `QCheckBox(text, box)`。完整教训入经验教训 §3.3（PyQt6 所有权陷阱 + 竞态排查纪律：每配置 ≥4 轮，单轮结论不可信）。
- **MainWindow 在线演练台常驻化**：`scripts/mw_repro.py`——拉真实主窗口（必须窗口模式）跑预设场景（`--scenario group-undo` 组化撤销全链路，自动点确认弹窗 ≥200ms）或 `--project` 只读打开真实工程；faulthandler+看门狗常开。登记 scripts/README 与 AGENTS 测试流程第 8 步。
- **规划记录**：第三批定稿（修复并入全局栈：单一栈双视图+端点快照+页代数扩展图像侧+3a/3b 分步）与工具箱收纳规划回填计划文档；新立 `docs/技术实现/不常用功能工具箱_规划.md`（无排期）。
- **护网**：`tests/test_undo_group_confirm.py`（新，11 条：摘要/多页代数僵尸/确认拒绝与放行/auto 豁免/单页豁免/标脏/blk 锚点重解析/面板摘要）；i18n 补 Canvas/HistoryPanel 上下文 6 条。

**涉及文件：** `ui/canvas.py`、`ui/textedit_commands.py`、`ui/mainwindow.py`、`ui/history_panel.py`、`tests/test_undo_group_confirm.py`（新）、`translate/zh_CN.ts`、`scripts/mw_repro.py`（新）、`scripts/README.md`、`AGENTS.md`、`docs/技术实现/撤销体系阶段4计划.md`、`docs/技术实现/不常用功能工具箱_规划.md`（新）、`docs/基础速查/经验教训.md`

---

### 侧栏批次①排版打磨 + 行距类型回退 + 窄栏浮层改版立项定稿

**问题/需求：** 用户反馈右栏格式区「太潦草」，讨论定稿紧凑行式打磨；实施后用户四点反馈中行距类型下拉被否决归位右栏（不常用 + 英文文案过长右栏放不下），整体回退原位。另立窄栏浮层内容件改版计划并完成形态定稿。批次①实机验收通过。

**改动要点：**

- 间距/宽度/对齐统一：格式区行距统一横 8 纵 6、字号/行距/字距三数字框统一 80px 成列、图标行左对齐、预设区下加 1px 分隔线（`_hsep`）；字距并回字号/行距同行，描边独占一行。
- 裸控件换封装类：FontFamilyComboBox/FontStyleComboBox 基类从 QComboBox 换 `ui/custom_widget` 封装 ComboBox（含 `WidePopupComboMixin` 弹出列表撑宽、闭合态宽度稳定）。
- 窄栏分组：`ui/panel_rail.py::PanelRail.add_group_gap` 在选中级（注解/着重号）与块级（变换/样式/历史）之间插入组间距，`ui/scenetext_manager.py` 调用。
- 行距类型下拉留在旧文本样式浮层原位（`ui/text_style_dock.py`），首版归位右栏经实机反馈回退（ts 条目同步回滚、qm 重编译）。
- **顺手修存量崩溃**：`tests/test_page_list_dirty_click.py` 的 _FakeCanvas 缺 3b 图像计数器 `saved_imgstep`/`num_imgstep`，槽内 AttributeError → exit 127（HEAD 即崩，与批次①无关）；修复后全量 626 passed。
- **窄栏浮层改版计划**：`docs/技术实现/窄栏浮层面板改版_计划.md`（新）——五浮层内容件统一对齐 `ui/text_engine/transforms/panel.py::TransformParameterPanel` 规范（标签右对齐 | 22px 输入框行式网格、封装类控件）；形态已拍板：连字区四行规范式、着重号两行标签|下拉、注解/着重号保持分开、注音读音保留应用/移除显式按钮；逻辑零改动纯换皮。顺序：批次②效果栈重移植 → 本改版 → 批次③描边行退役+闪现弹窗排查。

**涉及文件：** `ui/text_panel.py`、`ui/text_style_dock.py`、`ui/panel_rail.py`、`ui/scenetext_manager.py`、`tests/test_page_list_dirty_click.py`、`docs/技术实现/窄栏浮层面板改版_计划.md`（新）、`docs/项目概述.md`

---

### 撤销体系计划文档清理归档

**问题/需求：** 撤销体系重构与阶段 4 三批已全部实机验收收官，计划类文档失去活文档价值，标记完成并清理。

**改动要点：**

- 删除三份计划/普查文档：`撤销体系重构计划.md`、`撤销体系阶段4计划.md`、`撤销调用点普查.md`，全部登记 `scripts/audit_registry.json` deprecated（白名单放行 daily_log）。
- `撤销体系人工验收场景.md` 更新头部状态为「重构与阶段 4 三批均已实机验收收官」，成为回归参考唯一存档；正文两处对已删计划文档的引用改为「已随阶段 4 第 X 批落地并实机验收」。
- 代码残留引用清零：`ui/canvas.py`、`ui/textedit_commands.py` 注释及六个测试文件 docstring 改指验收场景文档/测试自身。
- `docs/项目概述.md` 索引同步（删两行、验收场景行改述）。

**涉及文件：** `docs/技术实现/撤销体系人工验收场景.md`、`docs/项目概述.md`、`scripts/audit_registry.json`、`ui/canvas.py`、`ui/textedit_commands.py`、`tests/test_inpaint_undo_merge.py`、`tests/test_render_sync.py`、`tests/test_undo_cross_page.py`、`tests/test_undo_group_confirm.py`、`tests/test_undo_inpaint_global.py`、`tests/test_undo_safety_net.py`

---

### Blender 式拖拽数值输入框 + 效果栈配置错位清理（含启动修复）

**问题/需求：** 复刻 Blender 输入框交互：无箭头、按住横向拖拽调值、单击进键盘编辑。实装后借此清理全仓库数值交互（箭头 QSS、拖拽标签、原生残留）。另修复并行代理（频繁中断输出致代码质量问题）埋下的两处启动崩溃。

**改动要点：**

- **拖拽混入**：`ui/custom_widget/spinbox.py::DragAdjustMixin`——悬停 ↔、按住横拖连续调值（5px/步，Shift 精调 ×0.1）、位移 <4px 视为单击进编辑（全选）；`NoArrowsSpinBox`/`NoArrowsDoubleSpinBox`/`SizeComboBox` 全挂载。Qt5/Qt6 全局坐标（`shared.FLAG_QT6`）兼容。
- **提交时序**：`SizeComboBox` 拖拽中静默刷新、`drag_finished` 才发一次 `param_changed`（对齐旧标签 btn_released 语义，避免撤销条目逐帧膨胀）；灵敏度经 `drag_step_provider` 钩子（行距 Distance 类型 0.5/其它 0.05）。`changeByDelta` 现无调用方，保留为公共 API。
- **清理**：删 `config/stylesheet.css` 箭头 QSS 规则（改代码 `ButtonSymbols.NoButtons`）；`style_format_editor::_spin`、`merge_dialog` 原生 spinbox 转封装；`gradient_editor.py::GradientValueEditor` 改继承封装去重；按「有文案标签降级静态说明、纯手柄整删」退役约 15 处拖拽标签（`text_panel`/`formatting/panel`/`formatting/advanced`/`gradient_editor`）。`transform/panel.py::TransformDragLabel`（X/Y 位置语义）保留。
- **启动修复一（active_format=None）**：`text_panel.py` 行距灵敏度原在构造期读 `C.active_format.line_spacing_type`（None），改惰性方法 `_line_spacing_drag_step` 运行时取 + None 守卫；`formatting/panel.py` 同法。
- **启动修复二 + 效果栈配置错位**：并行代理效果栈入参 `text_effects_panel`/`expand_teffects_panel`（带 s）与 config.py 声明 `show_text_effect_panel`/`expand_teffect_panel` 三处不咬合，致 `setupRegisterWidget` 读未声明字段崩溃；`TextEffectPanel` 是像 `text_transform_panel` 一样的按需浮层（非 View 菜单持久面板），统一对齐声明字段 + 加入 View 菜单 pop 清单，`set_expend_area` 读 `pcfg.expand_teffect_panel` 不再炸。静态清扫确认全部 `config_name`/`config_expand_name` 与 ProgramConfig 字段一一对应。

**涉及文件：** `ui/custom_widget/spinbox.py`、`ui/custom_widget/combobox.py`、`ui/style_format_editor.py`、`ui/merge_dialog.py`、`ui/text_engine/effects/gradient_editor.py`、`ui/text_panel.py`、`ui/text_engine/formatting/panel.py`、`ui/text_engine/formatting/advanced.py`、`config/stylesheet.css`、`scripts/style_showcase.py`、`AGENTS.md`、`utils/config.py`（字段声明已存）、`docs/daily_log.md`

---

## 2026-09-05

### 撤销体系阶段 4 第一批落地：跨页编辑历史 + 历史面板二期（按页分组/紧凑化/PS 式操作名）

**问题/需求：** 撤销主重构（0→3b）收官后的阶段 4 演进：跨页历史（决策 3）、批量组化（决策 4）、修复瘦身（决策 5）分三批实施。用户三拍板：跨页边界体验=「再按一次才继续」、全局替换保持快照分治不并入栈、先做跨页历史。计划文档 `docs/技术实现/撤销体系阶段4计划.md` 入库。本批为第一批，已实机验收（含两项 UI 细化反馈当场落地）。

**改动要点：**

- **命令 blk 锚点化**：活文本命令不再持 `TextBlkItem`/widget 引用（切页重建后 Python 对象仍活但脱离场景，重放会静默写隐形对象），改持 `(pagename, TextBlock 对象)` 锚点 + 快照，undo/redo 前按 blk 身份从 `ui/scenetext_manager.py` 场景列表重解析 live item/配对面板（`ui/textedit_commands.py::resolve_blk_entry`；键入/格式/几何/替换/粘贴/管线运行命令全量改造）。原「RuntimeError 僵尸防御」实际防不住脱离场景的活对象，重解析是根治。
- **切页不清文本栈**：`ui/mainwindow.py` 两处切页改 `commit_edit_sessions()`（旧页会话落账）+ `ui/canvas.py::prepare_page_switch`（仅清页级绘制栈）；清栈语义重定义——切页/翻译回填/当前页重载只作废该页历史，工程重载/txt 导入/批量重渲仍整栈 clear。
- **页屏障双通道**：检测管线整体换 blk_list → `utils/proj_imgtrans.py::bump_page_generation`（页代数计数，命令入栈捕获、执行期不一致=僵尸）；原地整页重写（整页翻译回填 `updateTranslation`、txt 导入非当前页）→ `ui/canvas.py::invalidate_text_history_for_page` 显式标记。僵尸命令保留栈位置、undo/redo 无操作 + 「已跳过」toast + 面板灰显。
- **armed 跨页撤销门**：`ui/canvas.py::_gate_cross_page`——下一命令所属页非当前页时第一按只 toast 提示、第二按经 `page_jump_requested` 信号 → `ui/mainwindow.py::on_undo_page_jump_requested` 走完整切页链路后续撤（一次按键=跳页+撤一步）；僵尸步不拦不跳页；历史面板行点击走 `auto_cross_page=True` 直接跳页（显式意图）。跳页链路可能落账旧页 transform 提交：门内重查下一栈位，已变则交还下次按键（线性序不被打破）。
- **项目级保存点**：cleanIndex 语义升级为「此位置前所有页编辑均已保存」，与切页条件保存/项目落盘天然对齐；越 cleanIndex 撤销即正确转脏。
- **历史面板二期**：QUndoStack 无公开列表模型（QUndoView 走私有模型不可分组），`ui/history_panel.py` 重写为自定义 `QAbstractListModel`——页头分组行 + 命令状态行 + 首行原始状态，行号=栈位置；紧凑行高/小字号/176px 默认宽/超长省略；保存点圆点、僵尸灰显加「已过期」后缀。
- **PS 式操作名**：格式化手势落账对比前后 FontFormat 字段归组，行名细化为「格式化：字号/字体/字重/颜色/描边宽度/对齐/文字样式/行距/字距/不透明度/阴影/渐变/变换/效果/排版细节」，多组=「格式化（多项）」，纯逐字符改动回退笼统「格式化」；`ui/text_engine/editing/commands.py::SetTextTransformCommand` 补「变换」名（原空名）。
- **存量测试修复**（HEAD 即失败，独立提交 54ca468）：test_base_styles 期望对齐 bold→font_weight 真值化语义；test_rail_docks 桩补 history launcher/dock 属性（`_iter_docks` 五键清单扩容后缺属性在 `__new__` 桩上 RuntimeError 并中断整条 pytest）。
- **测试**：新增 `tests/test_undo_cross_page.py` 9 条（页标签/代数捕获、armed 二次确认、redo 对称、僵尸跳过、代数失效、切页保栈、场景重建重解析、面板分组）；test_history_panel/test_page_list_dirty_click 适配；`verify.py --full` 全绿。

**涉及文件：** `utils/proj_imgtrans.py`、`ui/textedit_commands.py`、`ui/canvas.py`、`ui/drawing_commands.py`、`ui/mainwindow.py`、`ui/scenetext_manager.py`、`ui/module_manager.py`、`ui/history_panel.py`、`ui/text_engine/editing/commands.py`、`tests/test_undo_cross_page.py`（新）、`tests/test_history_panel.py`、`tests/test_page_list_dirty_click.py`、`tests/test_base_styles.py`、`tests/test_rail_docks.py`、`translate/zh_CN.ts`、`docs/技术实现/撤销体系阶段4计划.md`（新）、`docs/技术实现/撤销体系人工验收场景.md`

---

### 全局替换静默空转修复（3a 回归：保存路径广播 textstack_changed）+ 当前页脏标记语义定稿

**问题/需求：** 3a 人工验收抽查 S18-3 发现：全局搜索替换确认后无任何效果——文本不替换、不产生脏页、无回滚条。离线复现（真实 MainWindow + 两页项目）定位：`on_replace` 的 prepare 阶段同步落盘经 `ui/canvas.py::update_saved_undostep`，3a 重写该方法（clean 机制）时在末尾调 `on_textstack_changed()` 无条件广播 `textstack_changed`，主窗口接收槽误判"文档变更"调 `set_document_edited()`，把 `searched_pattern` 在收集前抹成 None → 收集器零命中走"无改动"分支静默返回。副作用不止替换：每次项目保存都会清空全局搜索结果面板。3a 前该方法只被动记账不广播，属回归。

**改动要点：**

- `ui/canvas.py`：拆出私有 `_refresh_save_state()`（脏判定计算）；`on_textstack_changed` = 刷新 + 广播；`update_saved_undostep`（保存路径）只刷新保存状态、不再广播——保存不改文档内容。
- **当前页脏标记语义定稿（用户决策）**：全局替换后当前页不标脏、不进重渲询问——`utils/proj_imgtrans.py::mark_page_needs_rerender` 的当前页排除语义维持（画布文本实时更新、结果图随保存/切页重渲）；删除 `ui/mainwindow.py::on_global_replace_finished` 里对当前页的无效标记调用（被排除语义吞掉的死代码）。决策记录补入验收文档附录第 7 条。
- **回归测试**：`tests/test_format_gesture_undo.py` 增 `test_update_saved_undostep_does_not_emit_textstack_changed`（保存不广播、真实栈变更如 undo 仍广播）。
- 验证：端到端离线复现脚本（真实 MainWindow + 两页项目）修复前复现、修复后替换落到画布/面板/数据/JSON 且脏页/回滚条正常；`verify.py` 全绿；test_format_gesture_undo / test_undo_safety_net / test_global_replace_commit / test_render_sync 全过；实机已验收。

**涉及文件：** `ui/canvas.py`、`ui/mainwindow.py`、`tests/test_format_gesture_undo.py`、`docs/技术实现/撤销体系人工验收场景.md`

---

### 撤销体系 3b 落地：文档栈全面禁用 + 旧机制删除（单栈快照命令制收官）

**问题/需求：** 按《撤销体系重构计划》执行阶段 3b——文档私有栈已无存在意义（3a 起撤销/重放全走 text_undo_stack 快照命令），全面禁用并删除旧排水/记账/joint 机制，消除双栈并存的心智负担与内存开销。

**改动要点：**

- **文档栈禁用**：`ui/text_engine/item.py::TextBlkItem.__init__` 与 `ui/textedit_area.py::SourceTextEdit.__init__`（覆盖 TransTextEdit 子类）构造时即 `setUndoRedoEnabled(False)`——所有写入路径（键入/粘贴/程序写入/HTML 装载）天然覆盖；F 清单四处暂存文档（注解装载/剪贴板 MIME/描边克隆/字形测量/全局替换暂存）核实不冲突（保存旧值恢复或独立文档）。
- **C 排水口删除**：item 与面板编辑器的文档级 `undo()`/`redo()` 方法（`document().undo()/redo()` + 步数回读）整体删除——活代码已无调用方（Ctrl+Z 走 `undo_signal` → canvas）。
- **D 步数记账删除**：`old_undo_steps` 读写点、`updateUndoSteps` 方法（item/面板两侧）、`ui/textedit_commands.py::_refresh_undo_steps` 全删；`_suppress_change_sync` 的 `in_redo_undo` 抑制旗保留（重放守卫仍用）。信号签名瘦身：`push_undo_stack` 去步数参数、`propagate_user_edited` 去 `joint_previous` 参数，四个分接 handler（`ui/scenetext_manager.py`）同步改签名。
- **E joint 链删除**：`ui/textedit_commands.py::sync_text_by_diff` 删 `joint_previous` 参数与 `joinPreviousEditBlock` 分支（对账恒为独立编辑块），删水位回写。
- **H 观察项核实**：`setPlainTextAndKeepUndoStack` 的「保留文档历史」语义自然消解，调用方只依赖「全文替换保留区外字符格式」效果，名字保留。
- **测试适配**：test_undo_safety_net / test_format_gesture_undo / test_render_sync / test_global_replace_format 按新信号签名更新布线；全部通过。
- 验证：`verify.py` 全绿（含启动链冒烟）；**剩余：3b 实机人工验收（重点中文 IME 输入）**。

**涉及文件：** `ui/text_engine/item.py`、`ui/textedit_area.py`、`ui/textedit_commands.py`、`ui/scenetext_manager.py`、`tests/test_undo_safety_net.py`、`tests/test_format_gesture_undo.py`、`tests/test_render_sync.py`、`tests/test_global_replace_format.py`、`docs/技术实现/撤销调用点普查.md`、`docs/技术实现/撤销体系重构计划.md`

---

### 技术文档清理：已完成计划/作废文档 3 篇删除 + 索引与状态同步

**问题/需求：** 全量审计 `docs/技术实现/` 中「疑似计划而非技术记录」的文档，按 148483ca 先例清理已完结/作废的计划文档，同步索引与状态行，未决项集中盘点。

**改动要点：**

- **删除 3 篇**：《文本面板选中态与字重失效_修复计划》（阶段 1–5 已于 2026-09-04 全部落地）、《文本面板选中态与字重失效_问题分析》（根因已消化）、《反向移植_i18n补充计划》（2026-09-03 已作废，结论早已记录在反向移植规范 §10 记录表）。有长期价值的内容压缩沉淀：Qt styleName/字重关键事实与 face 派生架构、面板选中态语义 → `docs/基础速查/经验教训.md` 新增 §7「字体与文本渲染」。
- **索引同步**（`docs/项目概述.md` §四）：删 2 行、改 2 行陈旧状态（撤销体系重构计划「待评审」→ 代码层完成剩余 3b 实机验收；查找替换设计方案标注已完结归档），补登记此前缺索引的 `撤销调用点普查.md` 与 `撤销体系人工验收场景.md`。
- **状态回填**：查找替换设计方案 §8 阶段 3/4 行的「待实机目视验收」——阶段 3 与状态头对齐（已实机验收）；阶段 4 注明全局替换链路 2026-09-05 实机端到端复验、格式条件 UI 未单独目视验收。
- **死链清理**：`docs/技术实现/反向移植_规范.md` §10 i18n 补充行删指向已删文档的引用；`ui/textitem.py` 与 2 个测试文件的注释中指向已删修复计划的「见 docs/...」指针摘除（正文说明自洽保留）。
- 保留不动：撤销体系三篇（3b 验收进行中）、效果栈计划（挂起待重启基线）、翻译 agent 化/术语工作台（活交接）、其余记录类。

**涉及文件：** `docs/项目概述.md`、`docs/基础速查/经验教训.md`、`docs/技术实现/反向移植_规范.md`、`docs/技术实现/查找替换与样式管理器重构_设计方案.md`、`ui/textitem.py`、`tests/test_fontfamily_style.py`、`tests/test_selection_state_panel.py`；删除 `docs/技术实现/文本面板选中态与字重失效_修复计划.md`、`docs/技术实现/文本面板选中态与字重失效_问题分析.md`、`docs/技术实现/反向移植_i18n补充计划.md`

---

### 收尾决策回填 + CUSTOM_FONT_FAMILIES 死常量清理

**问题/需求：** 技术文档审计收尾：用户对遗留问题逐项拍板——① 查找替换格式条件 UI 已实机检视，验收关账；② 样式管理器与查找替换查询入口重叠问题暂无好方案，搁置；③ 上游 font_registry 字重选择器经评测不如本 fork 的 face 派生设计，不移植、缝关闭；④ 效果栈（阶段 D 重启 + §7.1 效果组缝）等有空处理；⑤ `CUSTOM_FONT_FAMILIES` 可选清理项按审计意见执行。

**改动要点：**

- **决策回填**：查找替换设计方案状态头改「已完结归档并实机验收」、§7.2 判定改「不移植（保留 face 派生设计）」、§7.3 移植顺序更新（效果组缝保留，指向效果栈计划文档）、§8 阶段 4 验收补检视确认、§10 观察项标搁置；项目概述索引行同步。
- **死常量清理**：`utils/shared.py::CUSTOM_FONT_FAMILIES` 恒空且全库无写入点（`ALL_FONT_FAMILIES` 于 `utils/shared.py::init_font_list` 一次合并写入），删除该常量及两处死分支——`ui/text_panel.py::apply_fontfamily` 的「CUSTOM 归并映射」前置分支（条件恒 False）与 `ui/mainwindow.py::load_textstyle_from_proj_dir` 的 `only_custom` 参数分支（无任何调用方传 True，走该分支会得到空字体列表）。
- 验证：pytest（fontfamily_style / selection_state_panel / font_exclude_dialog / font_scan / global_search_fontstyle）通过；`verify.py` 全绿。

**涉及文件：** `utils/shared.py`、`ui/text_panel.py`、`ui/mainwindow.py`、`docs/技术实现/查找替换与样式管理器重构_设计方案.md`、`docs/项目概述.md`、`docs/基础速查/经验教训.md`

---

### 撤销体系 3b 实机人工验收通过（重构收官）+ 状态回填

**问题/需求：** 用户实机跑完《撤销体系人工验收场景》全部场景（含中文 IME），确认满足预期，问题记录表为空——撤销体系重构（甲-1/甲-2 止血 + 阶段 0 护网/普查/探针 + 3a 单栈快照命令制 + 3b 文档栈禁用）全部收官。

**改动要点：**

- 《撤销体系重构计划》状态头改「已收官（2026-09-05）」，后续演进指向验收场景文档 §五；《撤销调用点普查》标注使命完成留作存档；《撤销体系人工验收场景》头部记录验收结果，保留双重价值（回归参考 + §五 阶段 4 决策记录：撤销上限/历史弹窗/跨页历史等 6 项已拍板待另立计划）；项目概述索引行同步。
- 效果栈（阶段 D 重启 + 上游 §7.1 效果组缝）维持延后，等用户有空处理。

**涉及文件：** `docs/技术实现/撤销体系重构计划.md`、`docs/技术实现/撤销调用点普查.md`、`docs/技术实现/撤销体系人工验收场景.md`、`docs/项目概述.md`

---

### 撤销体系增强：步数上限一期（决策 1）+ 撤回行为名提示 + PS 式历史面板一期（决策 2，文本栈）

**问题/需求：** 撤销体系 3b 收官后的阶段 4 演进第一批：落实验收文档 §五 决策 1（Blender 式最大撤销步数）与决策 2（撤销历史可视化），另加撤回时显示行为名；用户拍板历史面板一期仅文本栈（绘制栈在窄栏无入口，搁置；撤回本身不受影响）。

**改动要点：**

- **撤销步数上限**：`utils/config.py::ProgramConfig` 新增 `undo_steps_limit`（默认 0=无限，范围 0–500，UI 直接显示数字 0 不用特殊文本）；`ui/canvas.py::apply_undo_limit` 两栈同效，`push_draw_command` 截断时同步平移绘制栈手工计数器（保存点被截落 -1 哨兵，保持「未保存」不误报）。**⚠️ Qt 限制（实测纠正）**：`setUndoLimit` 仅在空栈上生效、非空栈调用被忽略（Qt 文档化行为，Qt4 起如此；早期探针恰在空栈设置误判「惰性缩容」）——启动时栈空立即生效，会话中途改设置由下次清栈（切页/整页管线的各 `clear_*` 路径再应用）落地，UI 说明已注明。前置实测另固化：保存点被截断时 cleanIndex 落 -1、`isClean()` 恒 False，不假报「已保存」，无需自造判定。
- **命令命名清单**：活代码 26 个 QUndoCommand 类（textedit_commands/scenetext_manager/drawing_commands/canvas/fontstyle_manager_commands/mainwindow）构造时统一带 `UndoCommand` 上下文翻译文本（原先全为空名），历史面板行名与撤回 toast 共用此清单。
- **撤回 toast**：`ui/canvas.py::_notify_undo`——文本栈 undo 后通知中心显示「撤销：<行为名>」，key="undo" 去重刷新（连按不弹一排），空步不提示；历史面板跳转期间经 `_suppress_undo_toast` 抑制。Ctrl+Z 两条入口（`undo`/`undo_textedit`）都接。
- **PS 式历史面板**：新增 `ui/history_panel.py::HistoryPanel`——QUndoView 渲染（`setEmptyLabel` 首行=原始状态；探针实测行号=栈位置直接映射，当前位高亮/截断/清栈自动跟随），点击行循环调用 `canvas.undo()/redo()` 逐步跳转（复用已验收的每步记账），cleanIndex 行右缘圆点标保存点；新增 `icons/rail_history.svg`，窄栏 launcher（`ui/text_panel.py::install_history_launcher`，开合记忆 `history_dock_open`，`_iter_docks` 互斥扩五）。
- **测试**：新增 `tests/test_undo_limit.py`（10 例：Qt 截断×clean 语义固化 + 绘制栈计数镜像同步 + 非空栈 setUndoLimit 无效 + 中途改设置经切页生效）、`tests/test_history_panel.py`（6 例：命令命名抽查 / toast 守卫 / 跳转映射 / 截断后行映射）。
- **文档**：验收场景 §五 决策 1/2 回填落地记录（决策 2 形态由「历史弹窗」改定为窄栏面板，跨页分组日后并入）。
- 验证：`verify.py` 全绿（12 改动文件语法/文档/审计/i18n/qm/冒烟）；两测试文件全绿；实机已验收。

**涉及文件：** `utils/config.py`、`ui/canvas.py`、`ui/configpanel.py`、`ui/mainwindow.py`、`ui/history_panel.py`、`ui/text_panel.py`、`ui/scenetext_manager.py`、`ui/textedit_commands.py`、`ui/drawing_commands.py`、`ui/fontstyle_manager_commands.py`、`icons/rail_history.svg`、`tests/test_undo_limit.py`、`tests/test_history_panel.py`、`translate/zh_CN.ts`、`docs/技术实现/撤销体系人工验收场景.md`

---

## 2026-09-04

### 文本面板选中态与字重真值化五阶段重构落地 + 中间图截断闪退修复 + 启动日志噪音修复

**问题/需求：** 按《文本面板选中态与字重失效_问题分析/修复计划》落地已审计的五阶段修复（字重编辑有时不生效：Qt 的 styleName 精确匹配压过字重、多来源脏 face 名污染渲染）；实机验收另发现两问题：① 样式编辑器改字重后批量重渲染触发闪退（实为损坏的中间图穿透页面加载链路）；② Win10 启动终端刷 `fontTools _n_a_m_e stringOffset incorrect` ERROR ×3 与 `undefined param name: font_family` ×2。

**改动要点：**

- **阶段1 真值化基建**：新增 `utils/face_resolver.py`（`resolve_face` 就近匹配 face / `sync_face` 派生缓存 / `weight_of_face` / `invalidate_face_cache`，Qt styleStringHelper 阈值逻辑作 tie-break）；`font_weight` 成为唯一真值，`_style_name` 降级为派生显示缓存（`utils/fontformat.py::FontFormat` post_init bold 折算进字重）；`utils/shared.py::init_font_list` 尾部失效 face 缓存。
- **渲染端收口**：删 `ui/textitem.py` 的 fork set_fontformat 钉 face 补丁与 setFontFamily 的 style_name 通道（字重失效根因）；`ui/text_engine/item.py` set_fontformat 显式写数据层 face、`_sync_face_char_format` 同事务派生（char format + defaultFont 同步含字重）、get_fontformat 回读 styleName。
- **写入点重派生**：`ui/fontformat_commands.py` 包装器两处 act_ffmt 写点接 `_sync_active_face`；`utils/base_styles.py`（flatten/variant）、`utils/style_query.py`、`ui/fontstyle_manager.py`（sig/preset）undo 快照前 `sync_face`；`ui/mainwindow.py` 管线建块删 `blk.bold` 残留。
- **阶段2 多选镜像+混合态**：`ui/text_panel.py` 新增 `_active_multi_items`；`set_textblk_item` 支持 `multi_items`（优先于单选），`_set_multi_selection` 以活动块（默认最后选中）为镜像 + `_mixed_fields` 逐字段量化混合检测；编辑经包装器重定向广播到全部选中块，退出多选仅单选→闲置做整格式回写。
- **阶段3 闲置态**：无选中时面板镜像 `global_format`（标题「新块默认格式」），编辑实时落地全局默认（`_mirror_to_global_format`），新增 Reset 按钮（`_reset_global_format` 回退 FontFormat() 默认）。
- **阶段4 样式编辑器**：`ui/style_format_editor.py` font_weight 编辑器 getter 对未触碰项透传存量值（治愈 350 被静默改写成 400），"(default)"=None 语义，显式变更经 `weight_of_face`/`resolve_face`。
- **闪退修复**：`utils/proj_imgtrans.py` 修复图/无字图/遮罩三处中间图读取容错（损坏按"文件缺失"降级：修复图回退原图、遮罩置零），根因=早前写入中断留下的截断 PNG 使 `imread` 抛 `OSError: image file is truncated` 穿透 Qt 槽；`load_inpainted_by_imgname` 顺带修了 imread 返回 None 时的 `.shape` 二次崩溃。
- **启动噪音**：`ui/text_panel.py::global_mode` 加 None 守卫（`global_format` 在 mainwindow 构造尾部才注入，此前 `id(None)==id(None)` 误判全局模式，启动期字体下拉填充触发的 font_family 信号被派发到 None 上——既有行为，非本次重构引入）；`utils/font_scan.py::scan_font_faces` 扫描期临时压制 fontTools 日志（Win10 系统字体 name 表畸形只刷 ERROR 不抛错）。
- **测试**：`tests/test_face_resolver.py`（22 例：阈值锚点/就近/幂等/写入点快照保真）、`tests/test_selection_state_panel.py`（7 例多选广播/闲置跟随/回读）、`tests/test_fontfamily_style.py` 重写适配新契约、`tests/test_intermediate_img_robustness.py`（4 例截断中间图降级）。
- **i18n**：ts 新增 3 条（New Block Default Format/Reset/Reset the new-block default format）+ qm 重编译。
- ⚠️ 环境注意：测试曾误触 ultralytics 对 `PIL.Image.open` 的补丁（打开失败即 pip 装 pi-heif），pip 把 Pillow 卸到一半失败；已重装同版本 pillow==10.4.0 修复，pillow_jxl 完好。勿在测试中触达 `load_inpainted_by_imgname` 非当前页分支。
- 验证：`verify.py --full` 全绿（ruff/pytest 未装跳过）；上述 4 个测试套件 + test_font_scan 30 例 + test_batch_backup/test_page_list_dirty_click/test_dependency_startup 全过；实机已验收重构成果与闪退修复。

**涉及文件：** `utils/face_resolver.py`（新增）、`utils/fontformat.py`、`utils/shared.py`、`utils/base_styles.py`、`utils/style_query.py`、`utils/proj_imgtrans.py`、`utils/font_scan.py`、`ui/textitem.py`、`ui/text_engine/item.py`、`ui/fontformat_commands.py`、`ui/fontstyle_manager.py`、`ui/mainwindow.py`、`ui/text_panel.py`、`ui/scenetext_manager.py`、`ui/style_format_editor.py`、`scripts/audit_registry.json`、`translate/zh_CN.ts`、`translate/zh_CN.qm`、`tests/test_face_resolver.py`（新增）、`tests/test_selection_state_panel.py`（新增）、`tests/test_fontfamily_style.py`、`tests/test_intermediate_img_robustness.py`（新增）、`docs/技术实现/文本面板选中态与字重失效_修复计划.md`、`docs/技术实现/文本面板选中态与字重失效_问题分析.md`

---

### 撤销体系：效果参数并入格式化手势（一次手势=一步）+ 描边色自动跟随文字反色（含设置开关）

**问题/需求：** 实机验收发现：① 描边/行距/字距等效果参数改一次要按好几次 Ctrl+Z 才撤完（除真正修改那一下其余按撤销无视觉变化）——根因=效果类 setter 走 per-emission `push_undostack=True` 单命令（一步一压），与内容参数的手势宏聚合不一致；② 追加新功能：未手动指定的描边色自动取文字颜色反色（黑字白边/白字黑边），默认无声机制、改字色即时跟随，手动指定即置「自定义」标记永久生效（无恢复），设置面板嵌字节加全局开关默认开。

**改动要点：**

- **效果参数并入手势**：`ui/fontformat_commands.py` 删 `TextStyleUndoCommand` 与 `font_formating` 的 `push_undostack` 分支；装饰器 wrapper 在格式变更时对画布会话 `note_formatting_edit` 显式登记（幂等——效果类 setter 不触发 on_content_changed 自登记）；闭合以「基线↔终值」一条 `FormatGestureCommand` 落账（一次手势一步）。隔离调用（无画布，单测直调 ffmt_change_*）跳过手势、仅应用。
- **描边自动反色**：`utils/fontformat.py::FontFormat` 加块级标志 `stroke_color_custom` + `effective_stroke_color(*, auto_follow=True)`（默认自动取前景反色、手动则按 srgb）；`ui/text_engine/item.py` 的 set_fontformat/setFontColor/setStrokeWidth/setStrokeColorCustom 派生站点接入；`setFontColor` 改字色即时重派生反色（零延迟，面板 swatch 取色/右键应用两路径同步刷新）。
- **设置开关**：`utils/config.py::ProgramConfig` 加 `stroke_auto_follow=True`；`ui/configpanel.py` 嵌字→Text formatting 加「描边色跟随文字颜色」勾选（默认开），关闭后未手动指定的块按存档 srgb 渲染、不再联动；手动指定的块（`stroke_color_custom=True`）不受开关影响。
- **护网/测试**：`tests/test_format_gesture_undo.py` 增效果参数一次手势=一步回归用例（每参数独立单块画布隔离 QUndoStack 计数态）。
- 验证：`verify.py` 全绿（语法/docs/审计/i18n/qm/冒烟——configpanel 属启动链）；pytest 相关套件（test_format_gesture_undo / test_fontfamily_style / test_selection_state_panel / test_config_fields / test_startup_imports）全过；实机已验收。

**涉及文件：** `ui/fontformat_commands.py`、`ui/text_engine/item.py`、`ui/text_panel.py`、`ui/configpanel.py`、`utils/fontformat.py`、`utils/config.py`、`translate/zh_CN.ts`、`translate/zh_CN.qm`、`tests/test_format_gesture_undo.py`、`docs/技术实现/撤销体系人工验收场景.md`

---

### 拖拽吸附对齐失效修复 + 开关状态记忆

**问题/需求：** 用户实机反馈吸附对齐从前几天起失效——拖拽时参考线正常显示但块不吸附；另要求给饼菜单「吸附对齐」开关加状态记忆（此前每次启动默认开）。

**改动要点：**

- **失效根因（回归定位）**：c097b41（上游 v1.5.12 移植节点2a）重写 `ui/textitem.py::TextBlkItem.mouseMoveEvent` 时把 `_apply_snap()` 从 `super().mouseMoveEvent(event)` 之后挪到了之前——Qt 默认移动按事件增量覆写位置，吸附修正随即被本次增量抵消，最终停靠位永远差一个增量；compute_snap 照跑所以参考线仍显示，呈现「UI 对齐有反应、实际不吸附」。修复=吸附移回 super() 之后并注释顺序约束。
- **复现手法**：仿 `tests/test_box_select.py` 离屏 harness，QMouseEvent 直发 view 驱动真实 ItemIsMovable 拖拽链路，插桩记录 `_apply_snap` 前后 `absBoundingRect`——修复前右缘 225 不落 220，修复后精确吸附。
- **状态记忆**：`utils/config.py::ProgramConfig` 加 `snap_alignment=True`；`ui/canvas.py` 初始化 `alignment_enabled` 改读 pcfg；`ui/context_menu_config.py::_snap_alignment_run` 切换时写回 pcfg 并 `save_config()`（与 seq_badge 等饼菜单开关持久化方式一致）。
- 验证：`verify.py` 全绿；`tests/test_config_fields.py`、`tests/test_box_select.py`（18 例）通过。

**涉及文件：** `ui/textitem.py`、`utils/config.py`、`ui/canvas.py`、`ui/context_menu_config.py`

---

## 2026-09-03

### 效果栈面板阶段 D-2 重做 + 两 bug 修复 + 点角标闪现弹窗修复

**问题/需求：** 阶段 D 首版直译上游 UI 在 340px 窄栏不适配（下游反馈：Add 按钮无响应、快速预览幽灵小号文本、配色与部分控件样式不统一、混合模式/渐变交互可借鉴）。随后实机复验再反馈：加描边后点击文本框触发调整大小时必现一个"出现即消失的弹窗"。

**改动要点：**

- **面板重做（均衡裁剪）**：`ui/text_engine/effects/gradient_editor.py` 保留渐变条+时钟表盘+色块，砍停点不透明度/位置数值框，留角度+缩放；渐变编辑器卡片内联；混合模式保留上游二级菜单。
- **卡片重构**：`ui/text_engine/effects/cards.py` 头部瘦身（类型/位置选择器移入参数区），参数区对齐 TransformParameterPanel 规范（标签右对齐/22px 填充输入框/两列网格，span2=填充+色块、混合、渐变编辑器）；GroupFrame 包卡片+空栈隐藏；`_fit_effect_selector` 按自身最长条目采样宽度。
- **QSS**：`config/stylesheet.css` 重皮下划线→fork 填充风格；`QFrame#TextEffectCardsFrame`；`GradientValueEditor`（QDoubleSpinBox）也走 `TextEffectParamEditor` objectName，需补 QDoubleSpinBox 规则（QLineEdit 选择器匹配不到 spinbox）。
- **Bug① Add 无响应**：`ui/text_engine/effects/panel.py` 漏 `setMenu(add_menu)`——menu/action 都建好但没挂按钮，InstantPopup 无菜单点击无反应。
- **Bug② 幽灵小号文本**：`ui/textitem.py::_draw_effects_pixmap` 点绘制依赖 pixmap DPR，而 `renderer.py::_new_effect_pixmap` 仅在 `render_scale >= 1.0` 设 DPR → 0.5 档缓存被 1:1 画出半尺寸。修复=scale<1 时矩形拉伸绘制（对齐渲染器内部 `_draw_surface_pixmap` 语义）。
- **闪现弹窗**：`ui/text_engine/shape_control.py` 旋转角标——`ControlBlockItem.mousePressEvent` 的 rotate-zone 分支裸击就调 `updateAngleLabelPos()`（显示 "0.0°"），`mouseReleaseEvent` 再 hide，一次 press+release 无拖拽=角标闪现。修复=去掉 press 里的 `updateAngleLabelPos()`（mouseMoveEvent DRAG_ROTATE 分支已会在真拖拽时显示）。
- 聚合本批：VisitedLink 一行修复（`ui/mainwindow.py` 删 `QPalette.ColorRole.VisitedLink` 颜色覆盖）。

**涉及文件：** `ui/text_engine/effects/panel.py`、`ui/text_engine/effects/cards.py`、`ui/text_engine/effects/gradient_editor.py`、`ui/text_engine/effects/edit_session.py`、`ui/textitem.py`、`ui/text_engine/shape_control.py`、`ui/custom_widget/combobox.py`、`ui/custom_widget/view_panel.py`、`ui/style_format_editor.py`、`ui/text_panel.py`、`ui/mainwindow.py`、`ui/text_engine/rendering/shadow.py`、`ui/text_engine/rendering/__init__.py`、`ui/text_engine/editing/upstream_commands.py`、`utils/base_styles.py`、`utils/config.py`、`utils/style_query.py`、`config/stylesheet.css`、`translate/zh_CN.ts`、`translate/zh_CN.qm`、`icons/text-effect-*.svg`、`tests/*`、`scripts/audit_registry.json`、`ui/text_style_dock.py`（删除）

---
