from dotenv import load_dotenv

from biz.cmd.func.branch import BranchReviewFunc
from biz.cmd.func.directory import DirectoryReviewFunc


def welcome_message():
    print("\n欢迎使用 Codebase Review 工具！\n")


def get_func_choice():
    print("请选择功能:")
    print("1. Review 目录结构规范")
    print("2. Review 代码分支命名规范")
    while True:
        choice = input("请输入数字 (1-2): ").strip()
        if choice in ["1", "2"]:
            return int(choice)
        print("❌ 无效的选择，请输入 1 或 2")


if __name__ == "__main__":
    load_dotenv("conf/.env")
    welcome_message()

    choice = get_func_choice()
    if choice == 1:
        func = DirectoryReviewFunc()
        func.process()

    elif choice == 2:
        func = BranchReviewFunc()
        func.process()
