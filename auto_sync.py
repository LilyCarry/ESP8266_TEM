import os
import subprocess
import sys
import re
import time
import datetime

REPO_DIR = r"C:\Users\xu762\Documents\Github\ESP8266_TEM"
OBSUTIL_EXE = r"C:\obsutil\obsutil.exe"
BUCKET_PATH = "obs://esptemp/dht22/"
LOCAL_CSV_DIR = r".\csvs\\"

def show_toast(message):
    ps_command = (
        '[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null; '
        '[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null; '
        f'$template = "<toast><visual><binding template=\\"ToastText01\\"><text id=\\"1\\">{message}</text></binding></visual></toast>"; '
        '$xml = New-Object Windows.Data.Xml.Dom.XmlDocument; '
        '$xml.LoadXml($template); '
        '$toast = New-Object Windows.UI.Notifications.ToastNotification $xml; '
        '[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("AutoDataSync").Show($toast)'
    )
    subprocess.run(["powershell", "-WindowStyle", "Hidden", "-Command", ps_command], creationflags=subprocess.CREATE_NO_WINDOW)

def run_with_retry(cmd, cwd, max_retries=5, delay_seconds=10):
    for attempt in range(max_retries):
        try:
            subprocess.run(cmd, cwd=cwd, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            return True
        except subprocess.CalledProcessError:
            if attempt < max_retries - 1:
                time.sleep(delay_seconds)
            else:
                return False

def main():
    if datetime.date.today().day % 5 != 0:
        return

    # 1. Sync OBS (with retry)
    success = run_with_retry([OBSUTIL_EXE, "sync", BUCKET_PATH, LOCAL_CSV_DIR], cwd=REPO_DIR, max_retries=5, delay_seconds=15)
    if not success:
        show_toast("OBS同步失败，请检查网络！")
        sys.exit(1)
    
    # 2. Git Add
    subprocess.run(["git", "add", "csvs/"], cwd=REPO_DIR, creationflags=subprocess.CREATE_NO_WINDOW)
    
    # 3. Check for staged changes and get filenames
    result = subprocess.run(["git", "diff", "--name-only", "--cached"], cwd=REPO_DIR, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    staged_files = result.stdout.strip().split('\n')
    
    dates = []
    # Filenames are like "csvs/2026/08/08_06.csv" -> We can just regex out the MM_DD part.
    for file in staged_files:
        if file.endswith(".csv"):
            basename = os.path.basename(file) # "08_06.csv"
            match = re.match(r"(\d{2}_\d{2})\.csv", basename)
            if match:
                date_str = match.group(1).replace('_', '/')
                dates.append(date_str)
                
    if not dates:
        # No files changed, nothing to push
        return
        
    dates = sorted(list(set(dates)))
    if len(dates) == 1:
        commit_msg = f"[auto] update data {dates[0]}"
    else:
        commit_msg = f"[auto] update data {dates[0]} - {dates[-1]}"
        
    # 4. Commit and Push (with retry)
    subprocess.run(["git", "commit", "-m", commit_msg], cwd=REPO_DIR, creationflags=subprocess.CREATE_NO_WINDOW)
    
    success = run_with_retry(["git", "push"], cwd=REPO_DIR, max_retries=5, delay_seconds=15)
    if not success:
        show_toast("Git Push 失败，请检查网络！")
        sys.exit(1)
        
    # 5. Notify Success
    show_toast("温湿度数据推送完成")

if __name__ == "__main__":
    main()
