<div align="center">
    <a href="https://v2.nonebot.dev/store">
    <img src="https://raw.githubusercontent.com/fllesser/nonebot-plugin-template/refs/heads/resource/.docs/NoneBotPlugin.svg" width="310" alt="logo"></a>

## ✨ Nonebot2 Vocu 语音插件 ✨

<a href="./LICENSE">
    <img src="https://img.shields.io/github/license/fllesser/none bo t.svg" alt="license">
</a>
<a href="https://pypi.python.org/pypi/nonebot-plugin-vocu">
    <img src="https://img.shields.io/pypi/v/nonebot-plugin-vocu.svg" alt="pypi">
</a>
<img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="python">
<a href="https://github.com/astral-sh/ruff">
    <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json" alt="ruff">
</a>
<a href="https://github.com/astral-sh/uv">
    <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json" alt="uv">
</a>
</div>


## 📖 介绍

nonebot2 [vocu.ai](https://www.vocu.ai/) 插件

## 💿 安装

<details open>
<summary>使用 nb-cli 安装</summary>
在 nonebot2 项目的根目录下打开命令行, 输入以下指令即可安装

    nb plugin install nonebot-plugin-vocu --upgrade
使用 **pypi** 源安装

    nb plugin install nonebot-plugin-vocu --upgrade -i "https://pypi.org/simple"
使用**清华源**安装

    nb plugin install nonebot-plugin-vocu --upgrade -i "https://pypi.tuna.tsinghua.edu.cn/simple"


</details>

<details>
<summary>使用包管理器安装</summary>
在 nonebot2 项目的插件目录下, 打开命令行, 根据你使用的包管理器, 输入相应的安装命令

<details open>
<summary>uv</summary>

    uv add nonebot-plugin-vocu
安装仓库 master 分支

    uv add git+https://github.com/fllesser/nonebot-plugin-vocu@master
</details>

<details>
<summary>pdm</summary>

    pdm add nonebot-plugin-vocu
安装仓库 master 分支

    pdm add git+https://github.com/fllesser/nonebot-plugin-vocu@master
</details>
<details>
<summary>poetry</summary>

    poetry add nonebot-plugin-vocu
安装仓库 master 分支

    poetry add git+https://github.com/fllesser/nonebot-plugin-vocu@master
</details>

打开 nonebot2 项目根目录下的 `pyproject.toml` 文件, 在 `[tool.nonebot]` 部分追加写入

    plugins = ["nonebot_plugin_vocu"]

</details>

<details open>
<summary>安装必要组件</summary>
发送语音依赖 ffmpeg

    # ubuntu/debian
    sudo apt-get install ffmpeg
    ffmpeg -version
    # 其他 linux 参考: https://gitee.com/baihu433/ffmpeg
    # Windows 参考: https://www.jianshu.com/p/5015a477de3c
</details>

## ⚙️ 配置

在 nonebot2 项目的`.env`文件中添加下表中的必填配置

|      配置项       |  必填  | 默认值 |                        说明                        |
| :---------------: | :----: | :----: | :------------------------------------------------: |
|   vocu_api_key    | **是** |   ""   | 请前往 https://www.vocu.ai/ 注册账号，获取 api key |
| vocu_request_type |   否   | async  |   api 请求方式，默认 async， 氪金用户可选择 sync   |
| vocu_chars_limit  |   否   |  100   |                 生成语音的字符限制                 |
|    vocu_proxy     |   否   |   ""   |    无法直连需填，格式： "http://127.0.0.1:7890"    |

## 🎉 使用
### 指令表
|                 指令                 | 权限  | 需要@ | 范围  |                 说明                 |
| :----------------------------------: | :---: | :---: | :---: | :----------------------------------: |
|           [角色名]说[内容]           |   -   |  否   |   -   | 例如“雷军说我要开小米苏七，创死你们” |
|       /vocu.list or /角色列表        |   -   |  否   |   -   |             帐户角色列表             |
| /vocu.history or /历史生成[条数:int] |   -   |  否   |   -   |    []表示可选，默认 20，最大值100    |
|        /vocu[历史生成的序号]         |   -   |  否   |   -   |        发送指定历史生成的语音        |
