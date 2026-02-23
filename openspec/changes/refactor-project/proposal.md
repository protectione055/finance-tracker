# OpenSpec Change Proposal: refactor-project

日期: 2026-02-23  
来源: `openspec/specs/proposal-refactor.md`

## 背景
当前代码库存在两套并行实现（顶层 `core/` 与 `src/`），导致配置分叉、重复逻辑、同步链路未打通，且 README/配置描述与实现不一致。

## 目标
1. 收敛到单一实现路径（以 `src/` 为主）。
2. 打通 IMAP → 解析 → DB 入库链路。
3. 统一配置与文档描述。
4. 增加最小测试覆盖。

## 非目标
1. 实现支付宝/微信/银行 CSV 导入。
2. 完整报表系统或 Web UI。
3. 分布式存储与生产级调度。

## 方案概述
1. 以 `src/` 体系为主实现，`core/` 作为编排层或迁移为 `src/services/`。
2. CLI 统一调用 `src` 模块，完成入库去重。
3. 主配置模板以 `config/config.example.yaml` 为准，未实现内容标注为 future/experimental。
4. 增加解析器与存储层单测。

## 影响与风险
1. 影响范围：CLI、同步逻辑、配置、文档、测试。
2. 风险：路径迁移导致 CLI 失效、入库逻辑错误。
3. 缓解：分阶段合并、增加测试、短期保留旧路径兼容。

## 待决问题
1. `core/` 是否保留为编排层，或整体迁移到 `src/services/`？
2. `adapters/` 旧实现是否直接移除？
3. 旧配置字段是否需要兼容（如 `database` vs `data`）？
