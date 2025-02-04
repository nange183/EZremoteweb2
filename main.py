import cv2
import mss
import numpy as np
import time
import pyautogui
import pyperclip
import os
from flask import Flask, Response, render_template, request, jsonify

app = Flask(__name__)

pyautogui.FAILSAFE = False

resolution_dict = {
    '144p': {'x': 256, 'y': 144},  # 标准低分辨率
    '360p': {'x': 640, 'y': 360},  # 标清
    '480p': {'x': 854, 'y': 480},  # 标清 DVD
    '720p': {'x': 1280, 'y': 720},  # 高清 (HD)
    '1080p': {'x': 1920, 'y': 1080},  # 全高清 (Full HD)
    '1440p': {'x': 2560, 'y': 1440},  # 2K 分辨率
    '2160p': {'x': 3840, 'y': 2160},  # 超高清 (4K)
}
local_resolution = {'x': pyautogui.size()[0], 'y': pyautogui.size()[1]}


default_resolution = resolution_dict["720p"]  # 默认分辨率
QUALITY = 80  # 质量
FPS = 30  # 帧率


def capture_screen():
    with mss.mss() as sct:
        # 获取主显示器
        monitor = sct.monitors[1]

        while True:
            start_time = time.time()

            # 截取屏幕
            screenshot = sct.grab(monitor)

            # 转换为 NumPy 数组
            img = np.array(screenshot)

            # 转换为 BGR 格式（mss 默认输出 BGRA）
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

            # 调整大小到目标分辨率
            img = cv2.resize(img, (default_resolution['x'], default_resolution['y']), interpolation=cv2.INTER_LINEAR)

            # JPEG 软编
            _, encoded_img = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, QUALITY])  # 50 质量降低以减少带宽

            # 生成 MJPEG 流
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + encoded_img.tobytes() + b'\r\n')

            # 控制帧率
            elapsed_time = time.time() - start_time
            time.sleep(max(0, 1.0 / FPS - elapsed_time))


@app.route('/stream')
def stream():
    return Response(capture_screen(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/mouse-pos', methods=['POST'])
def mouse_pos():
    data = request.json  # 获取JSON数据
    # print("Received:", data)  # 控制台打印，便于调试

    global local_resolution
    local_resolution = {'x': pyautogui.size()[0], 'y': pyautogui.size()[1]}

    target_dict = {
        'x': int(int(data['cursor_x']) / int(data['img_width']) * local_resolution['x']),
        'y': int(int(data['cursor_y']) / int(data['img_height']) * local_resolution['y']),
    }
    # print(target_dict)

    pyautogui.moveTo(target_dict['x'], target_dict['y'])
    return jsonify({"status": "success"})


@app.route('/mouse-btn', methods=['POST'])
def mouse_btn():
    data = request.json
    # time.sleep(0.05)
    # print("Received button data:", data)

    # 在这里可以根据 data['button'] 来处理不同的鼠标操作
    if data['button'] == 'left_click':
        print("Left click triggered")
        pyautogui.click(button='left')  # 左键单击
    elif data['button'] == 'right_click':
        print("Right click triggered")
        pyautogui.click(button='right')  # 右键单击
    elif data['button'] == 'middle_click':
        print("Middle click triggered")
        pyautogui.click(button='middle')  # 中键单击
    elif data['button'] == 'left_double_click':
        print("Left double click triggered")
        pyautogui.doubleClick(button='left')  # 左键双击
    elif data['button'] == 'right_double_click':
        print("Right double click triggered")
        pyautogui.doubleClick(button='right')  # 右键双击
    elif data['button'] == 'middle_double_click':
        print("Middle double click triggered")
        pyautogui.doubleClick(button='middle')  # 中键双击
    else:
        print("Unknown button action")

    return jsonify({"status": "success"})


@app.route('/scroll', methods=['POST'])
def scroll():
    data = request.get_json()
    scroll_value = data.get('value')
    print('接收到的滑条数值:', scroll_value)

    if int(scroll_value):
        pyautogui.scroll(int(scroll_value))

    return jsonify({"message": "数值已接收", "value": scroll_value})


@app.route('/press', methods=['POST'])
def receive_press_data():
    data = request.get_json()
    print('接收到的 press 数据:', data)

    pyautogui.press(data['press'])

    return jsonify({"message": "press 数据已接收", "data": data})


@app.route('/typewrite', methods=['POST'])
def receive_typewrite_data():
    # 实际上是复制黏贴
    data = request.get_json()
    print('接收到的 typewrite 数据:', data)

    # pyautogui.typewrite(data['typewrite'])
    # 然而接下来的两行证明了pyautogui.typewrite()就是垃圾
    pyperclip.copy(data['typewrite'])
    pyautogui.hotkey('ctrl', 'v')

    return jsonify({"message": "typewrite 数据已接收", "data": data})


@app.route('/hotkey', methods=['POST'])
def receive_hotkey_data():
    data = request.get_json()
    print('接收到的 hotkey 数据:', data)

    hotkey = data['hotkey']
    modifiers = data['modifiers']

    # 构建传递给 pyautogui.hotkey() 函数的参数列表
    keys = []

    if modifiers['ctrl']:
        keys.append('ctrl')
    if modifiers['shift']:
        keys.append('shift')
    if modifiers['win']:
        keys.append('win')
    if modifiers['alt']:
        keys.append('alt')
    # tab 键通常不作为修饰键使用，这里根据你的需求决定是否添加
    if modifiers['tab']:
        keys.append('tab')

    if hotkey:
        keys.append(hotkey)

    # 调用 pyautogui.hotkey() 函数
    pyautogui.hotkey(*keys)

    return jsonify({"message": "hotkey 数据已接收", "data": data})


@app.route('/python', methods=['POST'])
def receive_python_command():
    command = request.form.get('command')
    print('接收到的 Python 命令:', command)
    # 在这里处理接收到的 Python 命令

    exec(command.replace('@p.', 'pyautogui.'))

    return jsonify({"message": "Python 命令已接收", "command": command})


@app.route('/bash', methods=['POST'])
def receive_bash_command():
    command = request.form.get('command')
    print('接收到的 Bash 命令:', command)
    # 在这里处理接收到的 Bash 命令

    info = os.system(command)

    return jsonify({"message": "Bash 命令已接收", "os": info})


@app.route('/config', methods=['POST'])
def config():
    """
    "default_resolution": "144p",
    "QUALITY": "70",
    "FPS": "30"
    """

    data = request.json

    if data['default_resolution'] in resolution_dict:
        global default_resolution
        default_resolution = resolution_dict[data['default_resolution']]
        print(f"更改默认分辨率为{data['default_resolution']}")

    if data['QUALITY']:
        global QUALITY
        QUALITY = int(data['QUALITY'])
        print(f"QUALITY已更改为{QUALITY}")

    if data['FPS']:
        global FPS
        FPS = int(data['FPS'])
        print(f"FPS已更改为{FPS}")

    return jsonify({"status": "success"})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=994, threaded=True)
