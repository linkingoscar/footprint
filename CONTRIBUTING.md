# 参与贡献 Footprint (足迹)

感谢您对 **Footprint (足迹)** 开源项目的关注与支持！无论是提交 Bug 报告、优化交互体验、撰写文档还是贡献新特性，我们都非常欢迎。

为了保证项目长期保持轻量、极速和易维护性，请在提交代码前仔细阅读本贡献指引。

---

## 🏗️ 核心架构与设计原则

Footprint 是一款专为旅行、美食打卡与情侣记录设计的轻量自托管应用。我们在技术选型上坚守以下核心准则：

1. **纯原生前端零构建工具（Zero-Build Vanilla JS）**
   - 前端采用原生 HTML5 + CSS3 + 现代原生 ES6+ JavaScript，不引入 Webpack、Vite、Node.js 运行时或重型前端框架（如 React/Vue/Angular）。
   - 用户双击即可通过浏览器离线体验；自建用户部署后开箱即用。
2. **“只出不进”代码治理守则**
   - `frontend/index.html` 保持主界面结构清晰，不再向其追加特定业务的大段内联逻辑；
   - 新增或重构的功能特性请抽离至 `frontend/js/` 目录中的独立模块文件（例如 `frontend/js/xxx.js`），并通过 `<script>` 按需引入。
3. **彻底的安全防线**
   - 前端渲染任何用户录入的数据（如标题、感想、地点等），必须经过 `escapeHtml()` 转义，严禁未经处理直接塞入 `innerHTML`。
   - 静态媒体资源访问严格使用短期受限的 Media Token，禁止把主登录凭据暴露在 URL 参数中。
4. **严格的向下兼容性**
   - 任何存储结构的更新都必须保障老版本用户数据的无损平滑迁移，绝不允许破坏用户在 `localStorage` 或 `IndexedDB` 中的历史足迹资产。

---

## 💻 本地开发环境准备

### 1. 环境依赖
- Python 3.10 或更高版本
- Git
- 现代浏览器（Chrome、Edge、Safari、Firefox）

### 2. 克隆与初始化
```bash
# 克隆仓库
git clone https://github.com/your-username/footprint.git
cd footprint

# 创建并激活 Python 虚拟环境 (推荐)
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# 安装开发依赖
pip install -r requirements.txt
pip install pytest pytest-cov
```

### 3. 本地启动服务
```bash
# 推荐使用模块化启动方式
python -m backend.app

# 亦兼容根目录快捷启动
python app.py
```
服务启动后，在浏览器访问 `http://localhost:5000` 即可进入足迹主页。

---

## 🧪 自动化测试规范

本项目后端拥有完整的单元测试套件覆盖。在提交 PR 之前，请务必保证本地测试全部通过：

```bash
# 运行完整测试套件
pytest tests/ -v --basetemp=.pytest_temp

# 运行覆盖率测试
pytest tests/ -v --cov=backend --cov-report=term-missing --basetemp=.pytest_temp
```

> [!NOTE]
> 在 Windows 环境下，若遇到临时目录权限异常，请始终附带 `--basetemp=.pytest_temp` 参数。

若为您新增的功能编写了后端接口，请在 `tests/` 目录下同步补充对应的测试用例。

---

## 🚀 提交 Pull Request 流程

1. **Fork 本仓库** 到您个人的 GitHub 空间；
2. **创建新特性分支**：
   ```bash
   git checkout -b feature/amazing-feature
   # 或
   git checkout -b fix/bug-description
   ```
3. **提交修改**：
   - 提交信息请使用清晰明了的描述（建议采用规范格式如 `feat: xxx`、`fix: xxx`、`docs: xxx`）；
4. **验证代码**：运行 `pytest` 确认全部通过；
5. **推送到远程**：
   ```bash
   git push origin feature/amazing-feature
   ```
6. **创建 Pull Request**：
   - 清晰描述本次修改所解决的问题、设计思路及测试验证方式。

再次感谢您为打造更好的足迹体验所做出的贡献！❤️
