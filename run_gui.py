"""
In Falsus AI 復盤診斷系統 - 本機獨立桌面應用程式 (Local Desktop GUI)
完全離線運作、純本機執行、無網路伺服器、無通訊埠開放、無遠端連線。
透過 Microsoft Edge WebView2 與原生硬體加速進行離線影片復盤。
"""

import sys
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from src.gui_bridge import LocalReplayBridge


def main():
    print("=" * 65)
    print("  In Falsus AI 復盤診斷系統 (本機獨立桌面版)")
    print("  完全離線運行 | GPU 硬體加速 | 無需任何網路伺服器與連線")
    print("=" * 65)

    try:
        import webview
        from webview.platforms import edgechromium
        import Microsoft.Web.WebView2.Core as webview2_core
    except ImportError as e:
        print(f"[錯誤] 缺少桌面渲染元件: {e}")
        print("請執行: pip install pywebview")
        return

    bridge = LocalReplayBridge()

    # 攔截並設置本機虛擬主機映射 (Virtual Host Name Mapping)
    # 將 https://infalsus.local/ 映射至本機專案目錄，完全在記憶體與進程內部處理
    # 支援 H.264 硬體解碼與全功能 Byte-Range 影片逐幀跳轉，不開啟任何 TCP 連接埠
    orig_on_ready = edgechromium.EdgeChrome.on_webview_ready

    def hooked_on_ready(self, sender, args):
        if args.IsSuccess:
            sender.CoreWebView2.SetVirtualHostNameToFolderMapping(
                "infalsus.local",
                str(ROOT_DIR),
                webview2_core.CoreWebView2HostResourceAccessKind.Allow
            )
        return orig_on_ready(self, sender, args)

    edgechromium.EdgeChrome.on_webview_ready = hooked_on_ready

    entry_url = "https://infalsus.local/src/gui_static/index.html"

    print("[系統] 正在啟動原生獨立桌面視窗 (Edge WebView2 離線加速)...")
    window = webview.create_window(
        title="In Falsus AI 復盤診斷系統",
        url=entry_url,
        js_api=bridge,
        width=1440,
        height=920,
        min_size=(1024, 680),
        background_color="#0b0f19"
    )
    bridge.set_window(window)

    # 啟動原生視窗迴圈
    webview.start()
    print("[系統] 復盤系統已正常關閉。")


if __name__ == "__main__":
    main()
