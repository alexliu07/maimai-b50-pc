## Maimai B50 PC

在 PC 上运行的舞萌DX B50图片生成器

基于 [Yuri-YuzuChaN/maimaiDX](https://github.com/Yuri-YuzuChaN/maimaiDX) 制作

做这个的启发是本人由于太社恐，不敢加查分QQ群，又看到QQ群Bot是用Python编写的，所以就修改了一下，使其能够在电脑上直接生成B50

***

### 使用方法

1. 注册 [舞萌 DX | 中二节奏查分器 (diving-fish.com)](https://www.diving-fish.com/maimaidx/prober/) 并按照网站上的指示导入成绩
2. 前往 [Release](https://github.com/alexliu07/maimai-b50-pc/releases) 页面下载最新的可执行程序并解压
3. 使用 [私人云盘](https://share.yuzuchan.moe/d/aria/Resource.zip?sign=LOqwqDVm95dYnkEDYKX2E-VGj0xc_JxrsFnuR1BcvtI=:0) 或 [onedrive](https://yuzuai-my.sharepoint.com/:u:/g/personal/yuzuchan_yuzuai_onmicrosoft_com/EaS3jPYdMwxGiU3V_V64nRIBk6QA5Gdhs2TkJQ2bLssxbw?e=Mm6cWY) 链接（均来自 [Yuri-YuzuChaN/maimaiDX](https://github.com/Yuri-YuzuChaN/maimaiDX) ）下载资源文件并解压，将 **static** 文件夹复制到本程序根目录下的 **_internal** 目录下
4. 运行主程序，第一次启动时会询问 步骤 1 中注册账号的用户名，填入之后回车，程序会自动开始生成B50图片
5. 生成完毕后，图片会保存在运行目录下的 **output** 文件夹
6. 若要修改要生成的用户名，可删去程序目录下 **_internal** 目录下的 **user.txt** 或直接修改其中内容为要更改的用户名即可

### 使用方法(源码)

比常规的使用方法多一个步骤：使用 `pip install -r requirements.txt` 安装依赖