import subprocess
import sys
import os

git_path = r"C:\Program Files\Git\cmd\git.exe"

try:
    # Try running git status
    result = subprocess.run([git_path, "status"], capture_output=True, text=True, cwd=r"c:\Users\LENOVO\Desktop\projects\accident_risk")
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    print("RETURN CODE:", result.returncode)
except Exception as e:
    print("Error:", e)
