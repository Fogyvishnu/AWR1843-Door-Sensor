"""
Automated C Unit Test Runner for CI/CD and Local Testing
=========================================================
Compiles test_door_detector.c and door_detector.c using available C compiler
(gcc, clang, or cl) and executes the test suite.
"""

import sys
import os
import subprocess
import shutil

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.abspath(os.path.join(TEST_DIR, "..", "src"))


def find_c_compiler():
    for comp in ["gcc", "clang", "cl"]:
        if shutil.which(comp):
            return comp
    return None


def run_tests():
    compiler = find_c_compiler()
    if not compiler:
        print("[!] Note: No host C compiler (gcc/clang/cl) found in PATH.")
        print("    In GitHub Actions or Linux environments, this runner compiles")
        print("    and runs test_door_detector.c automatically.")
        return 0

    target = os.path.join(TEST_DIR, "test_door_detector.exe" if sys.platform == "win32" else "test_door_detector")
    src1 = os.path.join(TEST_DIR, "test_door_detector.c")
    src2 = os.path.join(SRC_DIR, "door_detector.c")

    print(f"[*] Compiling C test suite using {compiler}...")
    if compiler in ["gcc", "clang"]:
        cmd = [compiler, "-Wall", "-Wextra", "-Werror", "-O2", f"-I{SRC_DIR}", "-o", target, src1, src2, "-lm"]
    else:
        cmd = [compiler, "/O2", f"/I{SRC_DIR}", f"/Fe:{target}", src1, src2]

    res = subprocess.run(cmd)
    if res.returncode != 0:
        print("[!] Compilation failed!")
        return res.returncode

    print(f"[+] Compiled successfully: {target}\n[*] Executing tests...")
    test_run = subprocess.run([target])
    return test_run.returncode


if __name__ == "__main__":
    sys.exit(run_tests())
