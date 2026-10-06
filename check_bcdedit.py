import ctypes
import os
import subprocess
import sys

# 激活 Windows 10/11 控制台的 ANSI 颜色支持
os.system("")

# 定义 ANSI 颜色代码字典
class Color:
    RED_BG = "\033[41;97m"  # 红底白字（强烈高亮）
    GREEN = "\033[92m"      # 绿色文本
    YELLOW = "\033[93m"     # 黄色文本
    CYAN = "\033[96m"       # 青色文本
    RESET = "\033[0m"       # 重置所有颜色属性

def is_admin():
    """检查是否拥有管理员权限"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """如果不是管理员，自动申请提权重启脚本"""
    if not is_admin():
        script_path = os.path.abspath(sys.argv[0])
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{script_path}"', None, 1
        )
        sys.exit(0)

def check_testmode_only():
    print(f"{Color.CYAN}=== 正在读取系统启动加载器配置 ==={Color.RESET}\n")

    # 查询 bcdedit 输出
    res_query = subprocess.run(
        "bcdedit",
        capture_output=True,
        text=True,
        encoding="gbk",
        errors="replace",
        shell=True,
    )
    output = res_query.stdout

    is_testmode_on = False

    # 逐行分析输出并进行高亮处理
    for line in output.splitlines():
        if "testsigning" in line.lower():
            if "yes" in line.lower() or "是" in line.lower():
                is_testmode_on = True
                # 整行进行红底白字的高亮显示
                print(f"{Color.RED_BG}{line}{Color.RESET}")
            else:
                print(f"{Color.GREEN}{line}{Color.RESET}")
        else:
            print(line)

    print(f"\n{Color.CYAN}=================================={Color.RESET}\n")

    # 仅作提示，不执行任何关闭命令
    if is_testmode_on:
        print(f"{Color.YELLOW}⚠️ 状态报告：系统当前处于【测试模式 (Test Mode)】。{Color.RESET}")
        print(f"{Color.GREEN}💡 提示：本脚本仅作检测和高亮显示，未对系统进行任何修改。{Color.RESET}")
    else:
        print(f"{Color.GREEN}✅ 状态报告：测试模式当前处于关闭状态。{Color.RESET}")

if __name__ == "__main__":
    # 自动获取管理员权限（读取 bcdedit 仍需此权限）
    run_as_admin()

    # 仅执行检测
    check_testmode_only()

    print("\n" + "=" * 40)
    input("按回车键 (Enter) 退出...")