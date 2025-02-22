<div align="center">
  <a href="https://v2.nonebot.dev/store"><img src="https://github.com/fllesser/nonebot-plugin-template/blob/master/.docs/NoneBotPlugin.svg" width="380" height="177" alt="NoneBotPluginLogo"></a>
</div>

<div align="center">

_✨ nonebot-plugin-vocu ✨_

<a href="./LICENSE">
    <img src="https://img.shields.io/github/license/owner/nonebot-plugin-vocu.svg" alt="license">
</a>
<a href="https://pypi.python.org/pypi/nonebot-plugin-vocu">
    <img src="https://img.shields.io/pypi/v/nonebot-plugin-vocu.svg" alt="pypi">
</a>
<img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="python">

</div>


## 📖 介绍

这里是插件的详细介绍部分

## 💿 安装

<details open>
<summary>使用 nb-cli 安装</summary>
在 nonebot2 项目的根目录下打开命令行, 输入以下指令即可安装

    nb plugin install nonebot-plugin-vocu --upgrade

    nb plugin install nonebot-plugin-vocu --upgrade -i "https://pypi.org/simple"


</details>

<details>
<summary>使用包管理器安装</summary>
在 nonebot2 项目的插件目录下, 打开命令行, 根据你使用的包管理器, 输入相应的安装命令

<details>
<summary>pip</summary>

    pip install nonebot-plugin-vocu --upgrade -i "https://pypi.org/simple"

</details>
<details>
<summary>pdm</summary>

    pdm add nonebot-plugin-vocu
</details>
<details>
<summary>poetry</summary>

    poetry add nonebot-plugin-vocu
</details>
<details>
<summary>conda</summary>

    conda install nonebot-plugin-vocu
</details>

打开 nonebot2 项目根目录下的 `pyproject.toml` 文件, 在 `[tool.nonebot]` 部分追加写入

    plugins = ["nonebot_plugin_vocu"]

</details>

## ⚙️ 配置

在 nonebot2 项目的`.env`文件中添加下表中的必填配置

|      配置项       |  必填  | 默认值 |                        说明                        |
| :---------------: | :----: | :----: | :------------------------------------------------: |
|   vocu_api_key    | **是** |   ""   | 请前往 https://www.vocu.ai/ 注册账号，获取 api key |
| vocu_request_type |   否   | async  |   api 请求方式，默认 async， 氪金用户可选择 sync   |
| vocu_chars_limit  |   否   |  100   |                 生成语音的字符限制                 |

## 🎉 使用
### 指令表
|              指令               | 权限  | 需要@ | 范围  |                 说明                 |
| :-----------------------------: | :---: | :---: | :---: | :----------------------------------: |
|        [角色名]说[内容]         |   -   |  否   |   -   | 例如“雷军说我要开小米苏七，创死你们” |
|       vocu.list/角色列表        |   -   |  否   |   -   |             帐户角色列表             |
| vocu.history/历史生成[条数:int] |   -   |  否   |   -   |    []表示可选，默认 10，最大值20     |
|      vocu[历史生成的序号]       |   -   |  否   |   -   |        发送指定历史生成的语音        |
