# TestMode_CheckTOOL 技术开发文档

> 适用版本：`main` 分支（构建方式：Nuitka）　|　平台：**仅限 Windows 10 / 11**

## 目录

1. [项目概述](#1-项目概述)
2. [仓库结构](#2-仓库结构)
3. [运行环境与依赖](#3-运行环境与依赖)
4. [整体架构与执行流程](#4-整体架构与执行流程)
5. [代码详解](#5-代码详解)
6. [本地开发与调试](#6-本地开发与调试)
7. [构建与发布（CI/CD）](#7-构建与发布cicd)
8. [已知限制与注意事项](#8-已知限制与注意事项)
9. [扩展指南](#9-扩展指南)
10. [安全说明](#10-安全说明)
11. [常见问题（FAQ）](#11-常见问题faq)

---

## 1. 项目概述

`check_bcdedit.py` 是一个**只读**的 Windows 检测工具，用于判断系统是否开启了**测试模式（Test Mode / `testsigning`）**。

| 项目 | 说明 |
| --- | --- |
| 核心功能 | 读取 `bcdedit` 输出，定位 `testsigning` 行并判断其值 |
| 展示方式 | ANSI 彩色输出：开启 → 红底白字；关闭 → 绿色 |
| 权限要求 | 管理员（读取 BCD 存储需要） |
| 是否修改系统 | **否**，不会执行任何写入、关闭测试模式的命令 |
| 外部依赖 | 无第三方运行时依赖，仅用 Python 标准库 |

## 2. 仓库结构

```
TestMode_ChechTOOL/
├── check_bcdedit.py            # 主程序（单文件）
├── README_脚本简介.txt          # 脚本简介
├── docs/
│   └── DEVELOPMENT.md          # 本文档
├── .github/workflows/build.yml # CI：Nuitka 编译 + 发布 Release
└── .gitignore                  # 忽略 build/ dist/ *.spec *.build/ *.dist/ 等
```

## 3. 运行环境与依赖

**运行（源码方式）**

- Windows 10 / 11
- Python 3.8+（CI 使用 3.12）
- 仅标准库：`ctypes`、`os`、`subprocess`、`sys`

**构建**

- Nuitka（`pip install nuitka ordered-set zstandard`）
- C 编译器：MSVC（GitHub `windows-latest` 自带）或 MinGW64（Nuitka 可自动下载）

> 程序依赖 `ctypes.windll` 与 `bcdedit.exe`，在 Linux / macOS 上无法运行。

## 4. 整体架构与执行流程

```
启动
 │
 ├─ run_as_admin()
 │    ├─ is_admin() == True  → 继续
 │    └─ is_admin() == False → ShellExecuteW("runas") 以管理员重启自身 → 当前进程 sys.exit(0)
 │
 ├─ check_testmode_only()
 │    ├─ subprocess.run("bcdedit")  # 编码 gbk
 │    ├─ 逐行扫描输出
 │    │    ├─ 含 "testsigning" 且含 "yes"/"是" → 红底白字，标记 is_testmode_on = True
 │    │    ├─ 含 "testsigning" 其他值         → 绿色
 │    │    └─ 其他行                          → 原样输出
 │    └─ 打印状态报告（开启 / 关闭）
 │
 └─ input("按回车键 (Enter) 退出...")  # 防止窗口一闪而过
```

## 5. 代码详解

### 5.1 ANSI 颜色初始化

```python
os.system("")
```

在 Windows 10+ 的控制台中，执行一次空的 `os.system` 会使控制台启用虚拟终端序列处理（VT mode），从而让 `\033[...m` 颜色码生效。这是一个常见的轻量技巧。

### 5.2 `Color` 类

| 常量 | 转义序列 | 用途 |
| --- | --- | --- |
| `RED_BG` | `\033[41;97m` | 红底白字，高亮测试模式开启 |
| `GREEN` | `\033[92m` | 绿色，表示正常 / 已关闭 |
| `YELLOW` | `\033[93m` | 黄色，警告提示 |
| `CYAN` | `\033[96m` | 青色，标题与分隔线 |
| `RESET` | `\033[0m` | 重置样式 |

### 5.3 `is_admin() -> int | bool`

调用 `ctypes.windll.shell32.IsUserAnAdmin()`，返回非 0 表示当前进程已具管理员权限。任何异常（例如非 Windows 环境）都被捕获并返回 `False`。

### 5.4 `run_as_admin() -> None`

若非管理员：

1. 取 `os.path.abspath(sys.argv[0])` 为脚本路径；
2. 调用 `ShellExecuteW(None, "runas", sys.executable, '"<script>"', None, 1)` 触发 UAC 提权并以新进程重启；
3. 当前（低权限）进程 `sys.exit(0)`。

### 5.5 `check_testmode_only() -> None`

- 通过 `subprocess.run("bcdedit", capture_output=True, text=True, encoding="gbk", errors="replace", shell=True)` 获取输出；
- 逐行判断：行内（转小写后）包含 `testsigning` 才进入判定；值为 `yes` 或 `是` 视为开启；
- 仅做打印，**不写入任何系统配置**。

### 5.6 入口

```python
if __name__ == "__main__":
    run_as_admin()
    check_testmode_only()
    input("按回车键 (Enter) 退出...")
```

## 6. 本地开发与调试

```powershell
# 1) 以管理员身份打开 PowerShell / 终端，直接运行
python check_bcdedit.py

# 2) 非管理员运行也可，会弹出 UAC 并在新窗口重启
```

**调试建议**

- 在**管理员终端**里运行，可直接看到输出而不会因重启新窗口而丢失。
- 想查看原始输出，可单独执行 `bcdedit /enum {current}`。
- 手动开关测试模式（用于验证脚本，**本工具自身不会执行**）：
  ```powershell
  bcdedit /set testsigning on    # 需重启生效
  bcdedit /set testsigning off
  ```

## 7. 构建与发布（CI/CD）

### 7.1 工作流概览（`.github/workflows/build.yml`）

| 项 | 值 |
| --- | --- |
| 触发条件 | push 到 `main` / `master`；手动 `workflow_dispatch` |
| 运行环境 | `windows-latest` |
| Python | 3.12 |
| 编译器 | Nuitka（MSVC） |
| 权限 | `contents: write`（用于发布 Release） |
| 产物 | `TestMode_Check.exe`（Artifact + Release `latest`） |

### 7.2 核心编译命令

```powershell
pip install nuitka ordered-set zstandard
python -m nuitka --onefile --assume-yes-for-downloads --windows-uac-admin `
  --output-dir=dist --output-filename=TestMode_Check.exe check_bcdedit.py
```

| 参数 | 作用 |
| --- | --- |
| `--onefile` | 打包为单个 exe |
| `--windows-uac-admin` | 在 exe 清单中写入 `requireAdministrator`，双击即弹 UAC |
| `--assume-yes-for-downloads` | 自动下载所需组件，避免 CI 交互阻塞 |
| `--output-dir` / `--output-filename` | 指定输出目录与文件名 |

### 7.3 本地编译（Windows）

```powershell
pip install nuitka ordered-set zstandard
python -m nuitka --onefile --windows-uac-admin --output-filename=TestMode_Check.exe check_bcdedit.py
```

> 需要已安装 Visual Studio Build Tools（C++ 工作负载）或允许 Nuitka 下载 MinGW64。

### 7.4 发布流程

1. 修改代码并 push 到 `main`；
2. Actions 自动编译；
3. 在 Releases 的 `latest` 标签下获取最新 `TestMode_Check.exe`。

> 当前所有版本共用 `latest` 标签。如需版本化发布，可改为 `tag_name: v${{ github.run_number }}` 或基于 Git tag 触发。

## 8. 已知限制与注意事项

1. **输出编码硬编码为 `gbk`**：适用于中文 Windows。英文或其他语言系统的 `bcdedit` 输出编码不同，可能出现乱码（已用 `errors="replace"` 防止崩溃）。可改为 `locale.getpreferredencoding()` 或使用 `chcp` 查询系统代码页。
2. **本地化文本判断较粗糙**：仅匹配 `yes` / `是`，其他语言的"开启"字样不会被识别，会被当作关闭。
3. **仅检查 `{current}` 默认条目的可见输出**：直接执行 `bcdedit`（不带参数）显示的是启动管理器与当前启动加载器；如果测试模式仅设置在其他条目上不会被覆盖。
4. **未设置 `testsigning` 项时**：输出中根本没有该行，程序判定为关闭，这是正确行为，但与"显式设置为 No"在显示上不同。
5. **Secure Boot**：启用 Secure Boot 的系统通常无法设置 `testsigning`，`bcdedit` 也可能提示"受 Secure Boot 策略保护"，这类错误文本会被原样打印。
6. **编译后 exe 的提权逻辑**：exe 带 `requireAdministrator` 清单，启动即已提权，`run_as_admin()` 正常情况下不会再触发；该函数主要服务于源码运行方式。
7. **杀毒软件**：涉及 `bcdedit` 与提权的 exe 偶尔会被启发式误报，Nuitka 编译比 PyInstaller 通常更少，但仍可能发生。

## 9. 扩展指南

**改进编码处理**

```python
import locale
enc = locale.getpreferredencoding(False)   # 例如 cp936 / cp1252
subprocess.run(["bcdedit"], capture_output=True, text=True, encoding=enc, errors="replace")
```

**去掉 `shell=True`**：改为列表参数 `["bcdedit"]`，避免不必要的 shell 解析。

**增加退出码**（便于脚本化调用）：开启返回 `1`，关闭返回 `0`。

**增加命令行参数**：用 `argparse` 添加 `--no-pause`（不等待回车）、`--no-color`（关闭颜色）、`--json`（输出结构化结果）。

**新增检测项**：如 `nointegritychecks`（禁用驱动签名强制）、`debug`、`bootstatuspolicy` 等，可复用现有"逐行匹配 + 高亮"结构，抽成一个 `highlight(line, keyword, bad_values)` 函数。

**代码风格**：保持标准库依赖为零；新增函数请写简明的中文 docstring。

## 10. 安全说明

- 程序**只读**：不调用 `bcdedit /set`、`/deletevalue` 等任何写命令；
- 仅申请管理员权限用于读取启动配置；
- 不联网、不写文件、不收集或上传任何信息；
- **不要把 GitHub Token 等凭据提交到仓库或贴到公共场合**；CI 发布使用的是 Actions 内置的 `GITHUB_TOKEN`，无需额外配置。

## 11. 常见问题（FAQ）

**Q：为什么运行后弹出新窗口？**
A：源码方式在非管理员下会通过 UAC 提权并重新启动自身，旧窗口随即退出。

**Q：输出乱码怎么办？**
A：见第 8 节第 1 条，调整 `encoding`。

**Q：测试模式开启了，桌面右下角有水印，如何关闭？**
A：本工具不做修改。需在管理员终端手动执行 `bcdedit /set testsigning off` 并重启。

**Q：编译后的 exe 能在 Linux / macOS 运行吗？**
A：不能，仅限 Windows。

**Q：为什么用 Nuitka 而不是 PyInstaller？**
A：Nuitka 将 Python 编译为 C 再生成原生二进制，体积更小（约 4 MB）、更难反解源码，通常误报也更少；代价是 CI 编译时间更长。
