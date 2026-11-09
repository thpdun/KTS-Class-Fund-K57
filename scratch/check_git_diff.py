import subprocess

cmd = ["git", "diff", "HEAD~3..HEAD", "--", "web/index.html"]
res = subprocess.run(cmd, capture_output=True, text=True)
diff = res.stdout

matches = [line for line in diff.splitlines() if 'flow-steps' in line or 'openActionModal' in line or 'Tạo Đề Xuất' in line]
print('\n'.join(matches[:50]))

