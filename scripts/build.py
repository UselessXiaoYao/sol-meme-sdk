#!/usr/bin/env python3
"""
构建和发布脚本
"""

import os
import sys
import shutil
from pathlib import Path

def clean_build():
    """清理构建目录"""
    build_dirs = ['build', 'dist', '*.egg-info']
    for pattern in build_dirs:
        for path in Path('.').glob(pattern):
            if path.is_dir():
                print(f"🧹 清理目录: {path}")
                shutil.rmtree(path)

def build_package():
    """构建包"""
    print("🔨 构建包...")
    os.system("python -m build")

def check_package():
    """检查包"""
    print("🔍 检查包...")
    os.system("twine check dist/*")

def upload_test():
    """上传到测试PyPI"""
    print("🚀 上传到测试PyPI...")
    os.system("twine upload --repository testpypi dist/*")

def upload_prod():
    """上传到正式PyPI"""
    print("🚀 上传到正式PyPI...")
    os.system("twine upload dist/*")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法: python scripts/build.py [clean|build|check|test|upload]")
        print("  clean  - 清理构建目录")
        print("  build  - 构建包")
        print("  check  - 检查包")
        print("  test   - 上传到测试PyPI")
        print("  upload - 上传到正式PyPI")
        return
    
    action = sys.argv[1]
    
    if action == "clean":
        clean_build()
    elif action == "build":
        clean_build()
        build_package()
    elif action == "check":
        check_package()
    elif action == "test":
        upload_test()
    elif action == "upload":
        upload_prod()
    else:
        print(f"未知操作: {action}")

if __name__ == "__main__":
    main()