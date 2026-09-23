# 锐评大师：Orange 实体按键语音原型

上方 A 键（GPIO23）切换开始和停止。开始时响一声高音，停止后响两声低音；
每次会话最长三分钟，防止忘记关闭。下方 B 键暂不使用。

它使用 GPT-Live 1 连续收发语音；这是 Lab 3 Part 1 本地语音实验之外的扩展原型。
Orange 的 USB 麦克风与扬声器使用默认 ALSA 设备，格式为 24 kHz、单声道、16 位 PCM。

## 安装与启动

在 Orange 的仓库中，先完成 Lab 3 原有环境设置，再安装可选依赖：

```bash
cd ~/Interactive-Lab-Hub/Lab\ 3
.venv/bin/python -m pip install -r requirements-live.txt
```

将完整的 OpenAI 项目 API key 放在 `Lab 3/.env` 中，格式为 `OPENAI_API_KEY=...`。
该文件由根 `.gitignore` 忽略，不得提交。然后运行：

```bash
cd ~/Interactive-Lab-Hub
bash 'Lab 3/speech-scripts/run_roast_button.sh'
```

启动脚本会暂时停止 `piscreen.service`，以便独占按键 GPIO；正常退出时恢复它。
在终端按 Ctrl+C 可退出控制程序，且会关闭正在进行的语音会话。
如果程序被强制杀死，手动运行 `sudo systemctl start piscreen.service` 恢复开机屏幕。

耳机或拉开麦克风与扬声器距离有助于降低设备听见自己声音的回声。
GPT-Live 按会话时长计费，后端模型调用另计；不用时按 A 停止。

## 设备验证（2026-09-23）

Orange 上的 A 键启动了 GPT-Live 会话；连续三轮食物输入产生了输入转写、
输出转写和扬声器音频。再次按 A 后收到 `session.closed`，客户端以 0 退出。
控制程序退出后，`piscreen.service` 恢复为 active。USB 扬声器的 PCM 音量
已调到并保存为 100%；用户确认测试音频的音量足够。
