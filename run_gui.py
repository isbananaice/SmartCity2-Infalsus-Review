import sys
import os
import time
import socket
import argparse
import threading
import webbrowser
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def start_server(port: int = 8765):
    import uvicorn
    from src.gui_server import app
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")

def wait_for_server(port: int = 8765, timeout: float = 8.0):
    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_port_in_use(port):
            return True
        time.sleep(0.15)
    return False

def main():
    parser = argparse.ArgumentParser(description="In Falsus AI 復盤診斷系統 GUI 啟動器")
    parser.add_argument("--port", type=int, default=8765, help="GUI 本地伺服器通訊埠 (預設: 8765)")
    parser.add_argument("--browser", action="store_true", help="強制使用預設瀏覽器開啟 (Chrome/Edge)")
    parser.add_argument("--server-only", action="store_true", help="僅啟動後端伺服器 (供後台或遠端訪問)")
    args = parser.parse_args()

    port = args.port
    url = f"http://127.0.0.1:{port}"

    print("=" * 65)
    print("  ⚡ In Falsus AI 復盤診斷系統 - GUI 應用程式")
    print(f"  本地存取網址: {url}")
    print("=" * 65)

    if not is_port_in_use(port):
        server_thread = threading.Thread(target=start_server, args=(port,), daemon=True)
        server_thread.start()
        print(f"[系統] 正在啟動 FastAPI 後台伺服器 (Port: {port})...")
        if not wait_for_server(port):
            print("[錯誤] 伺服器啟動逾時，請檢查 Port 是否衝突。")
            return
        print("[系統] 後台伺服器已就緒！")
    else:
        print(f"[提示] Port {port} 伺服器已在運行中，直接連接。")

    if args.server_only:
        print("[系統] 伺服器模式運行中，按 Ctrl+C 可停止...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[系統] 伺服器已停止。")
        return

    # 判斷是否強制瀏覽器或使用 pywebview 原生桌面視窗
    use_native_window = not args.browser
    opened_native = False

    if use_native_window:
        try:
            import webview
            print("[系統] 正在啟動原生獨立桌面視窗 (Edge WebView2 加速)...")
            webview.create_window(
                title="In Falsus AI 復盤診斷系統",
                url=url,
                width=1440,
                height=920,
                min_size=(1024, 680),
                background_color="#0b0f19"
            )
            webview.start()
            opened_native = True
        except Exception as e:
            print(f"[提示] 原生視窗載入提示 ({e})，切換至系統預設瀏覽器開啟。")
            opened_native = False

    if not opened_native:
        print(f"[系統] 正在以系統瀏覽器開啟: {url}")
        webbrowser.open(url)
        print("[系統] 復盤系統已在瀏覽器中啟動！按 Ctrl+C 可關閉服務。")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[系統] 服務已正常退出。")

if __name__ == "__main__":
    main()
