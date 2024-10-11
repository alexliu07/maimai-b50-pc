import json
import datetime
import math
import os
import asyncio
import traceback
from io import BytesIO
from typing import Tuple, overload, Dict, Any
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from aiohttp import ClientSession, ClientTimeout

from tools.maimaidx_error import *
from tools.maimaidx_model import *
from tools.tool import openfile, writefile

# 文件路径
Root: Path = Path(__file__).parent
static: Path = Root / 'static'
output = './output/'
if not os.path.exists(output):
    os.mkdir(output)
config_json: Path = static / 'config.json'
music_file: Path = static / 'music_data.json'
chart_file: Path = static / 'music_chart.json'

# 静态资源路径
maimaidir: Path = static / 'mai' / 'pic'
coverdir: Path = static / 'mai' / 'cover'
platedir: Path = static / 'mai' / 'plate'

# 字体路径
MEIRYO: Path = static / 'meiryo.ttc'
SIYUAN: Path = static / 'SourceHanSansSC-Bold.otf'
TBFONT: Path = static / 'Torus SemiBold.otf'

# 常用变量
score_Rank_l: Dict[str, str] = {'d': 'D', 'c': 'C', 'b': 'B', 'bb': 'BB', 'bbb': 'BBB', 'a': 'A', 'aa': 'AA',
                                'aaa': 'AAA', 's': 'S', 'sp': 'Sp', 'ss': 'SS', 'ssp': 'SSp', 'sss': 'SSS',
                                'sssp': 'SSSp'}
fcl: Dict[str, str] = {'fc': 'FC', 'fcp': 'FCp', 'ap': 'AP', 'app': 'APp'}
fsl: Dict[str, str] = {'fs': 'FS', 'fsp': 'FSp', 'fsd': 'FSD', 'fdx': 'FSD', 'fsdp': 'FSDp', 'fdxp': 'FSDp',
                       'sync': 'Sync'}

# maimaidx_music.py
class MusicList(List[Music]):
    def by_id(self, music_id: Union[str, int]) -> Optional[Music]:
        for music in self:
            if music.id == str(music_id):
                return music
        return None


async def get_music_list() -> MusicList:
    """获取所有数据"""
    # MusicData
    try:
        try:
            music_data = await maiApi.music_data()
            await writefile(music_file, music_data)
        except asyncio.exceptions.TimeoutError:
            print('从diving-fish获取maimaiDX曲目数据超时，正在使用yuzuapi中转获取曲目数据')
            music_data = await maiApi.transfer_music()
            await writefile(music_file, music_data)
        except UnknownError:
            print('从diving-fish获取maimaiDX曲目数据失败，请检查网络环境。已切换至本地暂存文件')
            music_data = await openfile(music_file)
        except Exception:
            print(f'Error: {traceback.format_exc()}')
            print('maimaiDX曲目数据获取失败，请检查网络环境。已切换至本地暂存文件')
            music_data = await openfile(music_file)
    except FileNotFoundError:
        print(
            f'未找到文件，请自行使用浏览器访问 "https://www.diving-fish.com/api/maimaidxprober/music_data" 将内容保存为 "music_data.json" 存放在 "static" 目录下并重启bot')
        raise
    # ChartStats
    try:
        try:
            chart_stats = await maiApi.chart_stats()
            await writefile(chart_file, chart_stats)
        except asyncio.exceptions.TimeoutError:
            print('从diving-fish获取maimaiDX数据获取超时，正在使用yuzuapi中转获取单曲数据')
            chart_stats = await maiApi.transfer_chart()
            await writefile(chart_file, chart_stats)
        except UnknownError:
            print('从diving-fish获取maimaiDX单曲数据获取错误。已切换至本地暂存文件')
            chart_stats = await openfile(chart_file)
        except Exception:
            print(f'Error: {traceback.format_exc()}')
            print('maimaiDX数据获取错误，请检查网络环境。已切换至本地暂存文件')
            chart_stats = await openfile(chart_file)
    except FileNotFoundError:
        print(
            f'未找到文件，请自行使用浏览器访问 "https://www.diving-fish.com/api/maimaidxprober/chart_stats" 将内容保存为 "chart_stats.json" 存放在 "static" 目录下并重启bot')
        raise

    total_list: MusicList = MusicList()
    for music in music_data:
        if music['id'] in chart_stats['charts']:
            _stats = [_data if _data else None for _data in chart_stats['charts'][music['id']]] if {} in chart_stats[
                'charts'][music['id']] else chart_stats['charts'][music['id']]
        else:
            _stats = None
        total_list.append(Music(stats=_stats, **music))

    return total_list


class MaiMusic:
    total_list: MusicList
    hot_music_ids: List = []

    def __init__(self) -> None:
        """封装所有曲目信息以及猜歌数据，便于更新"""

    async def get_music(self) -> None:
        """获取所有曲目数据"""
        self.total_list = await get_music_list()


mai = MaiMusic()


# maimaidx_api_data.py
class MaimaiAPI:
    MaiAPI = 'https://www.diving-fish.com/api/maimaidxprober'
    MaiCover = 'https://www.diving-fish.com/covers'
    MaiAliasAPI = 'https://api.yuzuchan.moe/maimaidx'

    def __init__(self) -> None:
        self.token = self.load_token()
        self.headers = {'developer-token': self.token}

    def load_token(self) -> str:
        return json.load(open(config_json, 'r', encoding='utf-8'))['token']

    async def _request(self, method: str, url: str, **kwargs) -> Any:
        session = ClientSession(timeout=ClientTimeout(total=30))
        res = await session.request(method, url, **kwargs)

        data = None

        if self.MaiAPI in url:
            if res.status == 200:
                data = await res.json()
            elif res.status == 400:
                raise UserNotFoundError
            elif res.status == 403:
                raise UserDisabledQueryError
            else:
                raise UnknownError
        elif self.MaiAliasAPI in url:
            if res.status == 200:
                data = (await res.json())['content']
            elif res.status == 400:
                raise EnterError
            elif res.status == 500:
                raise ServerError
            else:
                raise UnknownError
        await session.close()
        return data

    async def music_data(self):
        """获取曲目数据"""
        return await self._request('GET', self.MaiAPI + '/music_data')

    async def chart_stats(self):
        """获取单曲数据"""
        return await self._request('GET', self.MaiAPI + '/chart_stats')

    async def query_user(self, project: str, *, username: Optional[str] = None,
                         version: Optional[List[str]] = None):
        """
        请求用户数据

        - `project`: 查询的功能
            - `player`: 查询用户b50
            - `plate`: 按版本查询用户游玩成绩
        - `username`: 查分器用户名
        """
        json = {}
        if username:
            json['username'] = username
        if version:
            json['version'] = version
        if project == 'player':
            json['b50'] = True
        return await self._request('POST', self.MaiAPI + f'/query/{project}', json=json)

    async def transfer_music(self):
        """中转查分器曲目数据"""
        return await self._request('GET', self.MaiAliasAPI + '/maimaidxmusic')

    async def transfer_chart(self):
        """中转查分器单曲数据"""
        return await self._request('GET', self.MaiAliasAPI + '/maimaidxchartstats')

    async def download_music_pictrue(self, song_id: Union[int, str]) -> Union[Path, BytesIO]:
        try:
            if (file := coverdir / f'{song_id}.png').exists():
                return file
            song_id = int(song_id)
            if song_id > 100000:
                song_id -= 100000
                if (file := coverdir / f'{song_id}.png').exists():
                    return file
            if 1000 < song_id < 10000 or 10000 < song_id <= 11000:
                for _id in [song_id + 10000, song_id - 10000]:
                    if (file := coverdir / f'{_id}.png').exists():
                        return file
            pic = await self._request('GET', self.MaiCover + f'/{song_id:05d}.png')
            return BytesIO(pic)
        except CoverError:
            return coverdir / '11000.png'
        except Exception:
            return coverdir / '11000.png'


maiApi = MaimaiAPI()


# image.py
class DrawText:

    def __init__(self, image: ImageDraw.ImageDraw, font: Path) -> None:
        self._img = image
        self._font = str(font)

    def draw(self,
             pos_x: int,
             pos_y: int,
             size: int,
             text: Union[str, int, float],
             color: Tuple[int, int, int, int] = (255, 255, 255, 255),
             anchor: str = 'lt',
             stroke_width: int = 0,
             stroke_fill: Tuple[int, int, int, int] = (0, 0, 0, 0),
             multiline: bool = False):

        font = ImageFont.truetype(self._font, size)
        if multiline:
            self._img.multiline_text((pos_x, pos_y), str(text), color, font, anchor, stroke_width=stroke_width,
                                     stroke_fill=stroke_fill)
        else:
            self._img.text((pos_x, pos_y), str(text), color, font, anchor, stroke_width=stroke_width,
                           stroke_fill=stroke_fill)


# maimai_best_50.py
class Draw:
    basic = Image.open(maimaidir / 'b50_score_basic.png')
    advanced = Image.open(maimaidir / 'b50_score_advanced.png')
    expert = Image.open(maimaidir / 'b50_score_expert.png')
    master = Image.open(maimaidir / 'b50_score_master.png')
    remaster = Image.open(maimaidir / 'b50_score_remaster.png')
    title_bg = Image.open(maimaidir / 'title2.png').resize((600, 120))
    design_bg = Image.open(maimaidir / 'design.png').resize((1320, 120))
    _diff = [basic, advanced, expert, master, remaster]

    def __init__(self, image: Image.Image = None) -> None:
        self._im = image
        dr = ImageDraw.Draw(self._im)
        self._mr = DrawText(dr, MEIRYO)
        self._sy = DrawText(dr, SIYUAN)
        self._tb = DrawText(dr, TBFONT)

    async def whiledraw(self, data: Union[List[ChartInfo], List[PlayInfoDefault], List[PlayInfoDev]], best: bool,
                        height: int = 0) -> None:
        # y为第一排纵向坐标，dy为各排间距
        dy = 170
        if data and isinstance(data[0], ChartInfo):
            y = 430 if best else 1700
        else:
            y = height
        TEXT_COLOR = [(255, 255, 255, 255), (255, 255, 255, 255), (255, 255, 255, 255), (255, 255, 255, 255),
                      (138, 0, 226, 255)]
        x = 70
        await mai.get_music()
        for num, info in enumerate(data):
            if num % 5 == 0:
                x = 70
                y += dy if num != 0 else 0
            else:
                x += 416

            cover = Image.open(await maiApi.download_music_pictrue(info.song_id)).resize((135, 135))
            version = Image.open(maimaidir / f'{info.type.upper()}.png').resize((55, 19))
            if info.rate.islower():
                rate = Image.open(maimaidir / f'UI_TTR_Rank_{score_Rank_l[info.rate]}.png').resize((95, 44))
            else:
                rate = Image.open(maimaidir / f'UI_TTR_Rank_{info.rate}.png').resize((95, 44))

            self._im.alpha_composite(self._diff[info.level_index], (x, y))
            self._im.alpha_composite(cover, (x + 5, y + 5))
            self._im.alpha_composite(version, (x + 80, y + 141))
            self._im.alpha_composite(rate, (x + 150, y + 98))
            if info.fc:
                fc = Image.open(maimaidir / f'UI_MSS_MBase_Icon_{fcl[info.fc]}.png').resize((45, 45))
                self._im.alpha_composite(fc, (x + 246, y + 99))
            if info.fs:
                fs = Image.open(maimaidir / f'UI_MSS_MBase_Icon_{fsl[info.fs]}.png').resize((45, 45))
                self._im.alpha_composite(fs, (x + 291, y + 99))

            dxscore = sum(mai.total_list.by_id(str(info.song_id)).charts[info.level_index].notes) * 3
            dxnum = dxScore(info.dxScore / dxscore * 100)
            if dxnum:
                self._im.alpha_composite(Image.open(maimaidir / f'UI_GAM_Gauge_DXScoreIcon_0{dxnum}.png'),
                                         (x + 335, y + 102))

            self._tb.draw(x + 40, y + 148, 20, info.song_id, TEXT_COLOR[info.level_index], anchor='mm')
            title = info.title
            if coloumWidth(title) > 18:
                title = changeColumnWidth(title, 17) + '...'
            self._sy.draw(x + 155, y + 20, 20, title, TEXT_COLOR[info.level_index], anchor='lm')
            self._tb.draw(x + 155, y + 50, 32, f'{info.achievements:.4f}%', TEXT_COLOR[info.level_index], anchor='lm')
            self._tb.draw(x + 338, y + 82, 20, f'{info.dxScore}/{dxscore}', TEXT_COLOR[info.level_index], anchor='mm')
            self._tb.draw(x + 155, y + 82, 22, f'{info.ds} -> {info.ra}', TEXT_COLOR[info.level_index], anchor='lm')


class DrawBest(Draw):

    def __init__(self, UserInfo: UserInfo) -> None:
        super().__init__(Image.open(maimaidir / 'b50_bg.png').convert('RGBA'))
        self.userName = UserInfo.nickname
        self.plate = UserInfo.plate
        self.addRating = UserInfo.additional_rating
        self.Rating = UserInfo.rating
        self.sdBest = UserInfo.charts.sd
        self.dxBest = UserInfo.charts.dx
        # self.qqId = qqId

    def _findRaPic(self) -> str:
        if self.Rating < 1000:
            num = '01'
        elif self.Rating < 2000:
            num = '02'
        elif self.Rating < 4000:
            num = '03'
        elif self.Rating < 7000:
            num = '04'
        elif self.Rating < 10000:
            num = '05'
        elif self.Rating < 12000:
            num = '06'
        elif self.Rating < 13000:
            num = '07'
        elif self.Rating < 14000:
            num = '08'
        elif self.Rating < 14500:
            num = '09'
        elif self.Rating < 15000:
            num = '10'
        else:
            num = '11'
        return f'UI_CMN_DXRating_{num}.png'

    def _findMatchLevel(self) -> str:
        if self.addRating <= 10:
            num = f'{self.addRating:02d}'
        else:
            num = f'{self.addRating + 1:02d}'
        return f'UI_DNM_DaniPlate_{num}.png'

    async def draw(self) -> Image.Image:

        logo = Image.open(maimaidir / 'logo.png').resize((378, 172))
        dx_rating = Image.open(maimaidir / self._findRaPic()).resize((300, 59))
        Name = Image.open(maimaidir / 'Name.png')
        MatchLevel = Image.open(maimaidir / self._findMatchLevel()).resize((134, 55))
        ClassLevel = Image.open(maimaidir / 'UI_FBR_Class_00.png').resize((144, 87))
        rating = Image.open(maimaidir / 'UI_CMN_Shougou_Rainbow.png').resize((454, 50))

        self._im.alpha_composite(logo, (5, 130))
        if self.plate:
            plate = Image.open(platedir / f'{self.plate}.png').resize((1420, 230))
        else:
            plate = Image.open(maimaidir / 'UI_Plate_300501.png').resize((1420, 230))
        self._im.alpha_composite(plate, (390, 100))
        icon = Image.open(maimaidir / 'UI_Icon_309503.png').resize((214, 214))
        self._im.alpha_composite(icon, (398, 108))
        self._im.alpha_composite(dx_rating, (620, 122))
        Rating = f'{self.Rating:05d}'
        for n, i in enumerate(Rating):
            self._im.alpha_composite(Image.open(maimaidir / f'UI_NUM_Drating_{i}.png').resize((28, 34)),
                                     (760 + 23 * n, 137))
        self._im.alpha_composite(Name, (620, 200))
        self._im.alpha_composite(MatchLevel, (935, 205))
        self._im.alpha_composite(ClassLevel, (926, 105))
        self._im.alpha_composite(rating, (620, 275))

        self._sy.draw(635, 235, 40, self.userName, (0, 0, 0, 255), 'lm')
        sdrating, dxrating = sum([_.ra for _ in self.sdBest]), sum([_.ra for _ in self.dxBest])
        self._tb.draw(847, 295, 28, f'B35: {sdrating} + B15: {dxrating} = {self.Rating}', (0, 0, 0, 255), 'mm', 3,
                      (255, 255, 255, 255))
        self._mr.draw(900, 2465, 35, f'Designed by Yuri-YuzuChaN & BlueDeer233 | Generated by Maimai B50 PC',
                      (0, 50, 100, 255), 'mm', 3, (255, 255, 255, 255))

        await self.whiledraw(self.sdBest, True)
        await self.whiledraw(self.dxBest, False)

        return self._im.resize((1760, 2000))


def dxScore(dx: int) -> int:
    """
    返回值为 `Tuple`： `(星星种类，数量)`
    """
    if dx <= 85:
        result = 0
    elif dx <= 90:
        result = 1
    elif dx <= 93:
        result = 2
    elif dx <= 95:
        result = 3
    elif dx <= 97:
        result = 4
    else:
        result = 5
    return result


def getCharWidth(o) -> int:
    widths = [
        (126, 1), (159, 0), (687, 1), (710, 0), (711, 1), (727, 0), (733, 1), (879, 0), (1154, 1), (1161, 0),
        (4347, 1), (4447, 2), (7467, 1), (7521, 0), (8369, 1), (8426, 0), (9000, 1), (9002, 2), (11021, 1),
        (12350, 2), (12351, 1), (12438, 2), (12442, 0), (19893, 2), (19967, 1), (55203, 2), (63743, 1),
        (64106, 2), (65039, 1), (65059, 0), (65131, 2), (65279, 1), (65376, 2), (65500, 1), (65510, 2),
        (120831, 1), (262141, 2), (1114109, 1),
    ]
    if o == 0xe or o == 0xf:
        return 0
    for num, wid in widths:
        if o <= num:
            return wid
    return 1


def coloumWidth(s: str) -> int:
    res = 0
    for ch in s:
        res += getCharWidth(ord(ch))
    return res


def changeColumnWidth(s: str, len: int) -> str:
    res = 0
    sList = []
    for ch in s:
        res += getCharWidth(ord(ch))
        if res <= len:
            sList.append(ch)
    return ''.join(sList)


@overload
def computeRa(ds: float, achievement: float) -> int:
    """
    - `ds`: 定数
    - `achievement`: 成绩
    """


@overload
def computeRa(ds: float, achievement: float, *, onlyrate: bool = False) -> str:
    """
    - `ds`: 定数
    - `achievement`: 成绩
    - `onlyrate`: 返回评价
    """


@overload
def computeRa(ds: float, achievement: float, *, israte: bool = False) -> Tuple[int, str]:
    """
    - `ds`: 定数
    - `achievement`: 成绩
    - `israte`: 返回元组 (底分, 评价)
    """


def computeRa(ds: float, achievement: float, *, onlyrate: bool = False, israte: bool = False) -> Union[
    int, Tuple[int, str]]:
    if achievement < 50:
        baseRa = 7.0
        rate = 'D'
    elif achievement < 60:
        baseRa = 8.0
        rate = 'C'
    elif achievement < 70:
        baseRa = 9.6
        rate = 'B'
    elif achievement < 75:
        baseRa = 11.2
        rate = 'BB'
    elif achievement < 80:
        baseRa = 12.0
        rate = 'BBB'
    elif achievement < 90:
        baseRa = 13.6
        rate = 'A'
    elif achievement < 94:
        baseRa = 15.2
        rate = 'AA'
    elif achievement < 97:
        baseRa = 16.8
        rate = 'AAA'
    elif achievement < 98:
        baseRa = 20.0
        rate = 'S'
    elif achievement < 99:
        baseRa = 20.3
        rate = 'Sp'
    elif achievement < 99.5:
        baseRa = 20.8
        rate = 'SS'
    elif achievement < 100:
        baseRa = 21.1
        rate = 'SSp'
    elif achievement < 100.5:
        baseRa = 21.6
        rate = 'SSS'
    else:
        baseRa = 22.4
        rate = 'SSSp'

    if israte:
        data = (math.floor(ds * (min(100.5, achievement) / 100) * baseRa), rate)
    elif onlyrate:
        data = rate
    else:
        data = math.floor(ds * (min(100.5, achievement) / 100) * baseRa)

    return data


async def generate(username: Optional[str] = None) -> str:
    try:
        obj = await maiApi.query_user('player', username=username)

        mai_info = UserInfo(**obj)
        draw_best = DrawBest(mai_info)

        pic = await draw_best.draw()
        path = output + (datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S') + '.png')
        pic.save(path, "PNG")
        msg = '图片保存成功'
    except Exception as e:
        msg = f'错误：{traceback.format_exc()}'
    return msg


if __name__ == '__main__':
    userPath : Path = Root / 'user.txt'
    if not os.path.exists(userPath):
        username = input('请输入Diving-Fish查分器网站用户名：')
        with open(userPath,'w+',encoding='utf-8') as f:
            f.write(username)
    with open(userPath,'r',encoding='utf-8') as f:
        username = f.read()
    print('开始生成B50')
    result = asyncio.run(generate(username=username))
    print(result)
