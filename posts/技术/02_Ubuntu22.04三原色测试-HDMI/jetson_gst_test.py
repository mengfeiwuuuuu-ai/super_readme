import os
import sys
import subprocess
import re
import time
import argparse

def setup_environment():
    """
    配置环境变量，确保可以在终端中连接到 X Server 显示。
    对应需求：export DISPLAY=:0
    """
    os.environ["DISPLAY"] = ":0"
    print("[Info] Environment variable DISPLAY set to :0")

def get_screen_resolution():
    """
    使用 xrandr 获取当前激活屏幕的分辨率。
    对应需求：通过 xrandr 命令获取当前显示屏分辨率
    """
    try:
        # 执行 xrandr 命令
        cmd = "xrandr"
        output = subprocess.check_output(cmd, shell=True).decode("utf-8")
        
        # 使用正则寻找带有 '*' 标记的行，这代表当前激活的分辨率
        # 输出示例行： "1920x1080     60.00*+  50.00    59.94"
        pattern = re.compile(r'(\d+)x(\d+)\s+.*\*')
        match = pattern.search(output)
        
        if match:
            width = match.group(1)
            height = match.group(2)
            print(f"[Info] Detected Screen Resolution: {width}x{height}")
            return width, height
        else:
            print("[Warning] Could not detect resolution via xrandr, defaulting to 1920x1080")
            return "1920", "1080"
            
    except subprocess.CalledProcessError:
        print("[Error] Failed to execute xrandr. Is an X server running?")
        sys.exit(1)

def run_gst_color(color_name, hex_value, width, height, duration):
    """
    执行 gst-launch-1.0 命令显示特定颜色。
    对应需求：红绿蓝测试，每色3秒
    """
    print(f"--> Displaying {color_name} (0x{hex_value}) for {duration} seconds...")
    
    # 构建 GStreamer 管道命令
    # 1. videotestsrc: 生成测试源
    # 2. pattern=solid-color: 纯色模式
    # 3. foreground-color: 设置颜色 (0xAARRGGBB 或 0xRRGGBB)
    # 4. caps: 强制指定宽高，确保全屏
    # 5. nvvidconv: Jetson 专用转换插件，提高效率
    # 6. xvimagesink: X11 显示输出 (也可以尝试 autovideosink)
    
    gst_cmd = [
        "gst-launch-1.0",
        "videotestsrc", "pattern=solid-color", f"foreground-color={hex_value}",
        "!", f"video/x-raw,width={width},height={height}",
        "!", "nvvidconv",
        "!", "xvimagesink", "force-aspect-ratio=false"
    ]
    
    # 启动子进程
    # 使用 subprocess.Popen 而不是 run，因为我们需要在 Python 中控制它何时停止
    process = subprocess.Popen(
        gst_cmd, 
        stdout=subprocess.DEVNULL, # 屏蔽冗余日志
        stderr=subprocess.DEVNULL
    )
    
    try:
        # 等待指定时间
        time.sleep(duration)
    finally:
        # 时间到，终止进程
        process.terminate()
        process.wait() # 确保资源释放

def main():
    # 参数解析，支持设置轮数
    parser = argparse.ArgumentParser(description="Jetson Display Color Test via GStreamer")
    parser.add_argument("--rounds", type=int, default=1, help="Number of test loops (default: 1)")
    parser.add_argument("--duration", type=float, default=3.0, help="Duration per color in seconds (default: 3.0)")
    args = parser.parse_args()

    # 1. 设置环境
    setup_environment()
    
    # 2. 获取分辨率
    width, height = get_screen_resolution()
    
    # 定义测试颜色 (R, G, B)
    # GStreamer color format: 0xRRGGBB
    colors = [
        ("RED",   "0xff0000"),
        ("GREEN", "0x00ff00"),
        ("BLUE",  "0x0000ff")
    ]
    
    print(f"=== Starting Color Test (Rounds: {args.rounds}) ===")
    
    try:
        for i in range(args.rounds):
            print(f"\n--- Round {i+1}/{args.rounds} ---")
            for color_name, hex_val in colors:
                run_gst_color(color_name, hex_val, width, height, args.duration)
                
        print("\n=== Test Completed Successfully ===")
        
    except KeyboardInterrupt:
        print("\n[Info] Test interrupted by user.")

if __name__ == "__main__":
    main()
