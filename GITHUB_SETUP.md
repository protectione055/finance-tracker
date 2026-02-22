# GitHub 提交指南

## 空白配置模板已生成

配置文件模板已创建于 `config/config.template.yaml`，使用说明：

1. 复制模板到实际配置文件：
   ```bash
   cp config/config.template.yaml config/config.yaml
   ```

2. 编辑 `config/config.yaml`，填写你的实际配置（如预算、分类等）

3. `config.yaml` 已添加到 `.gitignore`，不会被提交到版本控制

## 手动创建 GitHub 仓库并推送

由于 GitHub CLI 需要认证，请按以下步骤操作：

### 方法一：通过 GitHub 网页创建

1. 登录 GitHub 账号：https://github.com/login
2. 点击右上角 `+` 按钮 → "New repository"
3. 填写仓库信息：
   - **Repository name**: `finance-tracker`
   - **Description**: `个人财务追踪与分析工具`
   - **Visibility**: Public (或 Private)
   - **Initialize this repository**: 不要勾选（已有本地仓库）
4. 点击 "Create repository"
5. 创建后，页面会显示推送命令，复制 SSH 版本的命令：

   ```bash
   git remote add origin git@github.com:protectione055/finance-tracker.git
   git branch -M master
   git push -u origin master
   ```

6. 在本地运行上述命令

### 方法二：使用 GitHub CLI 认证（推荐）

1. 运行登录命令：
   ```bash
   gh auth login
   ```

2. 按提示选择：
   - **What account do you want to log into?** GitHub.com
   - **What is your preferred protocol for Git operations?** SSH
   - **Upload your SSH public key to your GitHub account?** 选择你的密钥（如 `id_ed25519.pub`）
   - **How would you like to authenticate?** 选择 "Login with a web browser"

3. 按提示在浏览器完成登录

4. 登录后，重新运行：
   ```bash
   gh repo create finance-tracker --public --description "个人财务追踪与分析工具" --source=. --remote=origin --push
   ```

## 已完成的配置

- ✅ 空白配置模板: `config/config.template.yaml`
- ✅ Git 本地仓库已初始化
- ✅ 远程 origin 已配置为: `git@github.com:protectione055/finance-tracker.git`
- ✅ 所有文件已提交到本地 master 分支

## 本地提交记录

```
commit 93a5ab0 (HEAD -> master)
Author: zzm <zzm@example.com>
Date:   Sun Feb 22 10:15:00 2026

    Initial commit: Finance Tracker v1.0
    
    - Multi-source import (Alipay, WeChat Pay, bank CSV)
    - Smart categorization system
    - Spending analysis and reporting
    - Budget alerts
    - SQLite database support
    - Markdown/HTML report generation
```

## 推送后验证

推送完成后，访问以下地址验证：
- 仓库地址: https://github.com/protectione055/finance-tracker
