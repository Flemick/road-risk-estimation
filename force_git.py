import subprocess
import os

git_path = r"C:\Program Files\Git\cmd\git.exe"
cwd = r"c:\Users\LENOVO\Desktop\projects\accident_risk"

def run_git(*args):
    cmd = [git_path] + list(args)
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    with open(os.path.join(cwd, "git_log.txt"), "a") as f:
        f.write(f"Command: {' '.join(cmd)}\nStdout: {res.stdout}\nStderr: {res.stderr}\nCode: {res.returncode}\n\n")

run_git("init")
run_git("config", "user.name", "Admin")
run_git("config", "user.email", "admin@accidentrisk.local")
run_git("add", ".")
run_git("commit", "-m", "Initial commit from assistant")
