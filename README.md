# ai-finance

资金审批智能预审数字员工 Demo。第一阶段不接正式一体化平台，提供独立模拟审批页面：录入审批信息、上传发票（PDF/JPG/PNG/WEBP），系统自动提取票面字段、执行确定性财务规则、调用内网多模态大模型做语义核对，并把审核任务、附件、识别结果和规则结果保存到现有 PostgreSQL。

> 安全说明：仓库不保存真实 API Key、数据库密码或业务附件。请复制 `.env.example` 为 `.env` 后在本地填写。

## 1. V1 目标

- 模拟资金审批录入
- 支持多文件上传：PDF、JPG、JPEG、PNG、WEBP
- 默认直接调用 OpenAI 兼容的内网多模态模型进行发票结构化识别
- 可切换 PaddleOCR 路线，用于后续 A/B 测试速度与准确率
- Hybrid 路线：原生 PDF 文本直读 -> OCR -> 低质量时多模态兜底
- 确定性规则引擎：购销双方、金额勾稽、税额、税率、发票总额与申请金额等
- 大模型语义核对：发票项目/合同摘要/申请事由是否一致
- 审核结果页面显示 PASS / WARNING / FAIL / UNDETERMINED 及判断依据
- PostgreSQL 全程留痕
- Docker Compose 一键启动 Web/API；OCR 按需启用

## 2. 架构

```text
Browser
  |
  v
Vue 3 + Element Plus  (localhost:5173)
  |
  v
FastAPI  (localhost:18080)
  |------------------------------|
  |                              |
  v                              v
PostgreSQL                 Document Intelligence
现有 pgvector/pg17                |
host.docker.internal:5432         |-- multimodal: Qwen 多模态直读
                                  |-- ocr: PaddleOCR -> LLM结构化
                                  |-- hybrid: PDF文本/OCR -> 低质量VLM兜底
                                  |
                                  v
                           Finance Rule Engine
                                  |
                                  v
                           Review Result / Audit
```

### 为什么把识别和审核分开

文档识别负责回答“票上写了什么”；财务规则负责回答“这些数据是否正确”。金额计算、字段一致性等确定性规则不由大模型最终裁决，保证可解释、可测试、可审计。

## 3. 目录

```text
ai-finance/
├─ backend/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ config.py
│  │  ├─ database.py
│  │  ├─ models.py
│  │  ├─ schemas.py
│  │  └─ services/
│  │     ├─ llm.py
│  │     ├─ invoice_parser.py
│  │     ├─ ocr_client.py
│  │     ├─ pdf_utils.py
│  │     └─ rules.py
│  ├─ Dockerfile
│  └─ requirements.txt
├─ frontend/
│  ├─ src/
│  ├─ Dockerfile
│  └─ package.json
├─ ocr/
│  ├─ Dockerfile
│  ├─ requirements.txt
│  └─ app.py
├─ scripts/
│  └─ check.ps1
├─ docker-compose.yml
├─ .env.example
└─ README.md
```

## 4. 前置条件

1. Docker Desktop
2. 你现有的 PostgreSQL 容器已经运行（镜像可为 `pgvector/pgvector:pg17`）
3. PostgreSQL 端口已映射到宿主机，例如 `5432:5432`
4. API 服务能够访问你的内网模型地址

本项目 **不会再启动一个 PostgreSQL 容器**，而是通过 `host.docker.internal` 使用你已有的 PG。

## 5. 配置

复制：

```powershell
Copy-Item .env.example .env
```

编辑 `.env`：

```env
DATABASE_URL=postgresql+psycopg://<PG_USER>:<PG_PASSWORD>@host.docker.internal:5432/<PG_DATABASE>

LLM_BASE_URL=https://ai.bypc.com.cn/myopenai/v1
LLM_CHAT_COMPLETIONS_URL=https://ai.bypc.com.cn/myopenai/v1/chat/completions
LLM_API_KEY=<填写真实Key>
LLM_MODEL=zx/Qwen3.8-27B

PARSER_MODE=multimodal
OCR_URL=http://ocr:8090
UPLOAD_DIR=/data/uploads
MAX_PDF_PAGES=3
REQUEST_TIMEOUT_SECONDS=120
```

### API Key

不要把真实 Key 写进 `.env.example`、README、源码或 Git 提交。真实 Key 只放本地 `.env`。

## 6. 启动：默认多模态模式

第一次建议先不启动 PaddleOCR，直接验证完整主链路：

```powershell
docker compose up -d --build
```

访问：

- Web: http://localhost:5173
- API Docs: http://localhost:18080/docs
- API Health: http://localhost:18080/api/health

查看日志：

```powershell
docker compose logs -f api
docker compose logs -f web
```

## 7. 启动 PaddleOCR

PaddleOCR 被封装在独立 Docker 服务中，不污染本机 Python 环境。

启动：

```powershell
docker compose --profile ocr up -d --build ocr
```

然后将 `.env` 改为：

```env
PARSER_MODE=ocr
```

重启 API：

```powershell
docker compose up -d --build api
```

也可以：

```env
PARSER_MODE=hybrid
```

Hybrid 的目标是减少通用多模态模型调用：PDF 有文本层则直接解析；图片/扫描件先 OCR；当 OCR 内容不足或失败时才调用多模态模型。

> OCR 镜像首次构建会下载 Paddle/PaddleOCR Python 依赖，体积和构建时间明显高于普通 API 容器。生产内网部署时应提前构建镜像并把模型缓存到内网镜像仓库/制品库。

## 8. Demo 操作

1. 打开 http://localhost:5173
2. 填写模拟审批信息
3. 上传一张或多张发票 PDF/图片
4. 点击“开始智能审核”
5. 后端：
   - 保存审批输入快照
   - 保存附件 SHA-256
   - 解析发票字段
   - 执行财务规则
   - 执行语义核对
   - 保存审核结果
6. 页面显示：
   - 发票提取字段
   - 每条规则 PASS/WARNING/FAIL/UNDETERMINED
   - 异常摘要
   - 模型/解析模式
   - 总耗时

## 9. 当前发票结构化字段

```json
{
  "invoice_type": "",
  "invoice_number": "",
  "invoice_date": "",
  "buyer_name": "",
  "buyer_tax_id": "",
  "seller_name": "",
  "seller_tax_id": "",
  "items": [{"name": "", "amount": null, "tax_rate": null}],
  "amount_ex_tax": null,
  "tax_rate": null,
  "tax_amount": null,
  "total_amount": null,
  "amount_uppercase": "",
  "currency": "CNY",
  "confidence": 0.0
}
```

## 10. V1 内置规则

- FIN-INVOICE-001：发票购买方 vs 审批购买方
- FIN-INVOICE-002：发票销售方 vs 审批收款单位
- FIN-AMOUNT-001：不含税金额 + 税额 = 价税合计
- FIN-TAX-001：不含税金额 × 税率 ≈ 税额
- FIN-TAX-002：审批税率 vs 发票税率
- FIN-AMOUNT-002：所有发票价税合计之和 vs 申请金额
- FIN-DUP-001：发票号码是否在历史审核数据中重复
- FIN-SEM-001：发票项目与申请事由/合同摘要语义一致性

金额默认容差由 `MONEY_TOLERANCE` 控制。

## 11. 数据表

应用启动时自动创建：

- `finance_review_jobs`
- `finance_review_documents`
- `finance_rule_results`

V1 为 Demo 使用 SQLAlchemy `create_all`。进入正式系统前建议切换 Alembic 管理迁移，并增加规则版本、Prompt版本、人工确认、规则库等表。

## 12. 并发设计

V1 Web 请求会创建审核任务并同步等待结果，便于演示。正式接入业务系统时应升级为：

```text
审批事件 -> Queue -> Review Worker Pool -> OCR/VLM受控并发 -> DB -> 页面轮询/SSE
```

原因是多模态模型单张票据可能需要 10 秒以上，不能让业务并发直接冲击 GPU。建议生产阶段测量 GPU 上的安全并发数，再给 Worker 设置固定并发，而不是无限并发。

## 13. 与正式一体化平台接入时的替换点

当前模拟界面提交：

```text
审批表单 + 上传附件
```

正式接入后替换成：

```text
一体化平台流程事件
  -> GET approval
  -> GET attachments
  -> 创建 review job
  -> 审核
  -> POST ai-review summary
```

审核工作台本身可以保持独立部署，通过 `approval_id` 打开；原审批页只展示“智能审核摘要 + 查看智能审核”入口。

## 14. 验证

PowerShell：

```powershell
.\scripts\check.ps1
```

手动：

```powershell
Invoke-RestMethod http://localhost:18080/api/health
```

## 15. 下一阶段

- 财务规则 Excel 导入和版本管理
- 支持更多票据类型
- OCR/VLM A/B 测试台
- 异步任务队列
- 财务审核独立工作台
- 人工确认和反馈闭环
- 一体化平台 API Adapter
- 影子运行与历史数据回放
- Prometheus/OpenTelemetry 监控
