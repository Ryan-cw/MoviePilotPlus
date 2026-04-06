import re
from typing import Any, List, Dict, Tuple, Optional

import requests

from app import schemas
from app.core.config import settings
from app.core.event import eventmanager, Event
from app.core.cache import cached
from app.log import logger
from app.plugins import _PluginBase
from app.schemas import DiscoverSourceEventData
from app.schemas.types import ChainEventType

# 爱奇艺频道分类
CHANNEL_PARAMS = {
    "tv": {"catg": "1", "name": "电视剧"},
    "movie": {"catg": "2", "name": "电影"},
    "variety": {"catg": "6", "name": "综艺"},
    "anime": {"catg": "4", "name": "动漫"},
    "documentary": {"catg": "3", "name": "纪录片"},
    "children": {"catg": "15", "name": "少儿"},
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Referer": "https://www.iqiyi.com/",
}

# 各频道过滤条件静态定义
FILTER_UI_DATA = {
    "tv": [
        {
            "Id": "order",
            "Text": "排序",
            "Options": [
                {"Value": "hotScore", "Text": "人气"},
                {"Value": "publishTime", "Text": "上新"},
                {"Value": "score", "Text": "评分"},
            ],
        },
        {
            "Id": "year",
            "Text": "年份",
            "Options": [
                {"Value": "2026", "Text": "2026"},
                {"Value": "2025", "Text": "2025"},
                {"Value": "2024", "Text": "2024"},
                {"Value": "2023", "Text": "2023"},
                {"Value": "2022", "Text": "2022"},
                {"Value": "2021", "Text": "2021"},
                {"Value": "2020", "Text": "2020"},
                {"Value": "2015,2019", "Text": "2015-2019"},
                {"Value": "2010,2014", "Text": "2010-2014"},
                {"Value": "2000,2009", "Text": "2000-2009"},
            ],
        },
        {
            "Id": "area",
            "Text": "地区",
            "Options": [
                {"Value": "1", "Text": "中国大陆"},
                {"Value": "2", "Text": "美国"},
                {"Value": "3", "Text": "英国"},
                {"Value": "4", "Text": "韩国"},
                {"Value": "5", "Text": "日本"},
                {"Value": "6", "Text": "泰国"},
                {"Value": "7", "Text": "中国香港"},
                {"Value": "8", "Text": "中国台湾"},
                {"Value": "100", "Text": "其他"},
            ],
        },
        {
            "Id": "genre",
            "Text": "风格",
            "Options": [
                {"Value": "1", "Text": "剧情"},
                {"Value": "2", "Text": "情感"},
                {"Value": "3", "Text": "搞笑"},
                {"Value": "4", "Text": "悬疑"},
                {"Value": "5", "Text": "都市"},
                {"Value": "6", "Text": "家庭"},
                {"Value": "7", "Text": "古装"},
                {"Value": "8", "Text": "历史"},
                {"Value": "9", "Text": "奇幻"},
                {"Value": "10", "Text": "青春"},
                {"Value": "11", "Text": "战争"},
                {"Value": "12", "Text": "武侠"},
                {"Value": "13", "Text": "励志"},
                {"Value": "14", "Text": "短剧"},
                {"Value": "15", "Text": "科幻"},
            ],
        },
        {
            "Id": "pay",
            "Text": "付费",
            "Options": [
                {"Value": "0", "Text": "免费"},
                {"Value": "1", "Text": "VIP"},
            ],
        },
    ],
    "movie": [
        {
            "Id": "order",
            "Text": "排序",
            "Options": [
                {"Value": "hotScore", "Text": "人气"},
                {"Value": "publishTime", "Text": "上映时间"},
                {"Value": "score", "Text": "评分"},
            ],
        },
        {
            "Id": "year",
            "Text": "年份",
            "Options": [
                {"Value": "2026", "Text": "2026"},
                {"Value": "2025", "Text": "2025"},
                {"Value": "2024", "Text": "2024"},
                {"Value": "2023", "Text": "2023"},
                {"Value": "2022", "Text": "2022"},
                {"Value": "2021", "Text": "2021"},
                {"Value": "2020", "Text": "2020"},
                {"Value": "2015,2019", "Text": "2015-2019"},
                {"Value": "2010,2014", "Text": "2010-2014"},
                {"Value": "2000,2009", "Text": "2000-2009"},
            ],
        },
        {
            "Id": "area",
            "Text": "地区",
            "Options": [
                {"Value": "1", "Text": "中国大陆"},
                {"Value": "2", "Text": "美国"},
                {"Value": "3", "Text": "英国"},
                {"Value": "4", "Text": "韩国"},
                {"Value": "5", "Text": "日本"},
                {"Value": "6", "Text": "泰国"},
                {"Value": "7", "Text": "中国香港"},
                {"Value": "8", "Text": "中国台湾"},
                {"Value": "9", "Text": "法国"},
                {"Value": "10", "Text": "德国"},
                {"Value": "11", "Text": "意大利"},
                {"Value": "100", "Text": "其他"},
            ],
        },
        {
            "Id": "genre",
            "Text": "风格",
            "Options": [
                {"Value": "1", "Text": "剧情"},
                {"Value": "2", "Text": "喜剧"},
                {"Value": "3", "Text": "爱情"},
                {"Value": "4", "Text": "动作"},
                {"Value": "5", "Text": "恐怖"},
                {"Value": "6", "Text": "科幻"},
                {"Value": "7", "Text": "犯罪"},
                {"Value": "8", "Text": "惊悚"},
                {"Value": "9", "Text": "悬疑"},
                {"Value": "10", "Text": "奇幻"},
                {"Value": "11", "Text": "战争"},
                {"Value": "12", "Text": "动画"},
                {"Value": "13", "Text": "传记"},
                {"Value": "14", "Text": "家庭"},
                {"Value": "15", "Text": "历史"},
                {"Value": "16", "Text": "冒险"},
                {"Value": "17", "Text": "灾难"},
            ],
        },
        {
            "Id": "pay",
            "Text": "付费",
            "Options": [
                {"Value": "0", "Text": "免费"},
                {"Value": "1", "Text": "VIP"},
            ],
        },
    ],
    "variety": [
        {
            "Id": "order",
            "Text": "排序",
            "Options": [
                {"Value": "hotScore", "Text": "人气"},
                {"Value": "publishTime", "Text": "最新"},
                {"Value": "score", "Text": "评分"},
            ],
        },
        {
            "Id": "genre",
            "Text": "风格",
            "Options": [
                {"Value": "1", "Text": "音乐"},
                {"Value": "2", "Text": "真人秀"},
                {"Value": "3", "Text": "选秀"},
                {"Value": "4", "Text": "脱口秀"},
                {"Value": "5", "Text": "美食"},
                {"Value": "6", "Text": "旅游"},
                {"Value": "7", "Text": "晚会"},
                {"Value": "8", "Text": "演唱会"},
                {"Value": "9", "Text": "情感"},
                {"Value": "10", "Text": "喜剧"},
                {"Value": "11", "Text": "亲子"},
                {"Value": "12", "Text": "文化"},
                {"Value": "13", "Text": "体育"},
            ],
        },
    ],
    "anime": [
        {
            "Id": "order",
            "Text": "排序",
            "Options": [
                {"Value": "hotScore", "Text": "人气"},
                {"Value": "publishTime", "Text": "更新时间"},
                {"Value": "score", "Text": "评分"},
            ],
        },
        {
            "Id": "area",
            "Text": "地区",
            "Options": [
                {"Value": "1", "Text": "中国大陆"},
                {"Value": "5", "Text": "日本"},
                {"Value": "2", "Text": "美国"},
                {"Value": "100", "Text": "其他"},
            ],
        },
        {
            "Id": "genre",
            "Text": "风格",
            "Options": [
                {"Value": "1", "Text": "热血"},
                {"Value": "2", "Text": "奇幻"},
                {"Value": "3", "Text": "战斗"},
                {"Value": "4", "Text": "搞笑"},
                {"Value": "5", "Text": "日常"},
                {"Value": "6", "Text": "科幻"},
                {"Value": "7", "Text": "萌系"},
                {"Value": "8", "Text": "治愈"},
                {"Value": "9", "Text": "校园"},
                {"Value": "10", "Text": "恋爱"},
                {"Value": "11", "Text": "冒险"},
                {"Value": "12", "Text": "历史"},
                {"Value": "13", "Text": "机战"},
            ],
        },
        {
            "Id": "status",
            "Text": "状态",
            "Options": [
                {"Value": "1", "Text": "完结"},
                {"Value": "0", "Text": "连载"},
            ],
        },
    ],
    "documentary": [
        {
            "Id": "order",
            "Text": "排序",
            "Options": [
                {"Value": "hotScore", "Text": "人气"},
                {"Value": "publishTime", "Text": "最新"},
                {"Value": "score", "Text": "评分"},
            ],
        },
        {
            "Id": "genre",
            "Text": "风格",
            "Options": [
                {"Value": "1", "Text": "自然"},
                {"Value": "2", "Text": "历史"},
                {"Value": "3", "Text": "人文"},
                {"Value": "4", "Text": "科技"},
                {"Value": "5", "Text": "军事"},
                {"Value": "6", "Text": "社会"},
                {"Value": "7", "Text": "探索"},
                {"Value": "8", "Text": "美食"},
            ],
        },
    ],
    "children": [
        {
            "Id": "order",
            "Text": "排序",
            "Options": [
                {"Value": "hotScore", "Text": "人气"},
                {"Value": "publishTime", "Text": "最新"},
            ],
        },
        {
            "Id": "genre",
            "Text": "风格",
            "Options": [
                {"Value": "1", "Text": "动画片"},
                {"Value": "2", "Text": "益智"},
                {"Value": "3", "Text": "儿歌"},
                {"Value": "4", "Text": "故事"},
                {"Value": "5", "Text": "科普"},
            ],
        },
    ],
}


def build_filter_ui() -> List[dict]:
    """
    构建各频道的过滤 UI
    """
    ui = []
    for mtype, filters in FILTER_UI_DATA.items():
        for f in filters:
            chips = [
                {
                    "component": "VChip",
                    "props": {"filter": True, "tile": True, "value": opt["Value"]},
                    "text": opt["Text"],
                }
                for opt in f["Options"]
            ]
            ui.append(
                {
                    "component": "div",
                    "props": {
                        "class": "flex justify-start items-center",
                        "show": "{{mtype == '" + mtype + "'}}",
                    },
                    "content": [
                        {
                            "component": "div",
                            "props": {"class": "mr-5"},
                            "content": [{"component": "VLabel", "text": f["Text"]}],
                        },
                        {
                            "component": "VChipGroup",
                            "props": {"model": f["Id"]},
                            "content": chips,
                        },
                    ],
                }
            )
    return ui


class IqiyiDiscover(_PluginBase):
    # 插件名称
    plugin_name = "爱奇艺探索"
    # 插件描述
    plugin_desc = "让探索支持爱奇艺的数据浏览。"
    # 插件图标
    plugin_icon = "https://www.iqiyi.com/favicon.ico"
    # 插件版本
    plugin_version = "1.0.0"
    # 插件作者
    plugin_author = "Custom"
    # 作者主页
    author_url = "https://github.com"
    # 插件配置项ID前缀
    plugin_config_prefix = "iqiyidiscover_"
    # 加载顺序
    plugin_order = 99
    # 可使用的用户级别
    auth_level = 1

    _enabled = False

    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled")
        # 允许加载爱奇艺图片域名
        for domain in ["pic0.iqiyipic.com", "pic1.iqiyipic.com",
                        "pic2.iqiyipic.com", "pic3.iqiyipic.com"]:
            if domain not in settings.SECURITY_IMAGE_DOMAINS:
                settings.SECURITY_IMAGE_DOMAINS.append(domain)

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        return [
            {
                "path": "/iqiyi_discover",
                "endpoint": self.iqiyi_discover,
                "methods": ["GET"],
                "summary": "爱奇艺探索数据源",
                "description": "获取爱奇艺探索数据",
            }
        ]

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        return [
            {
                "component": "VForm",
                "content": [
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "enabled",
                                            "label": "启用插件",
                                        },
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        ], {"enabled": False}

    def get_page(self) -> List[dict]:
        pass

    @cached(region="iqiyi_discover", ttl=1800, skip_none=True)
    def __request(self, page: int, mtype: str, **kwargs) -> List[Dict]:
        """
        请求爱奇艺 API
        爱奇艺列表接口：https://mesh.if.iqiyi.com/portal/lw/videolib/data
        """
        catg = CHANNEL_PARAMS.get(mtype, {}).get("catg", "1")

        params = {
            "ret_num": 24,
            "page_id": page,
            "channel_id": catg,
            "lib_id": "1",
            "mode": "11",
            "bkt": "",
        }

        # 合并过滤参数
        for k, v in kwargs.items():
            if v is not None:
                params[k] = v

        url = "https://mesh.if.iqiyi.com/portal/lw/videolib/data"

        try:
            response = requests.get(url, params=params, headers=HEADERS, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("code") != "A00000":
                logger.error(f"爱奇艺 API 返回错误: {data.get('code')} - {data.get('msg')}")
                return []

            items = data.get("data", {}).get("list", [])
            if not items:
                logger.warning(f"爱奇艺未返回数据: mtype={mtype}, page={page}")
            return items

        except requests.RequestException as e:
            logger.error(f"爱奇艺请求失败: {str(e)}")
            return []
        except (KeyError, ValueError) as e:
            logger.error(f"爱奇艺响应解析失败: {str(e)}")
            return []

    def iqiyi_discover(
        self,
        mtype: str = "tv",
        order: str = None,
        year: str = None,
        area: str = None,
        genre: str = None,
        pay: str = None,
        status: str = None,
        page: int = 1,
        count: int = 24,
    ) -> List[schemas.MediaInfo]:
        """
        获取爱奇艺探索数据，返回 MediaInfo 列表
        """

        def _item_to_media(item: dict) -> Optional[schemas.MediaInfo]:
            try:
                title = item.get("name") or item.get("title", "")
                if not title:
                    return None

                # 封面图
                poster = (
                    item.get("imageUrl")
                    or item.get("img")
                    or item.get("image_url_2_3")
                    or ""
                )
                # 补全协议头
                if poster and poster.startswith("//"):
                    poster = "https:" + poster

                # 年份
                year_val = str(item.get("year") or item.get("publishYear") or "")

                # 媒体类型
                channel_id = str(item.get("channelId") or item.get("channel_id") or "")
                if channel_id == "2":
                    media_type = "电影"
                else:
                    media_type = "电视剧"

                # 媒体ID（爱奇艺用 albumId 或 tvId）
                media_id = str(
                    item.get("albumId")
                    or item.get("tvId")
                    or item.get("id")
                    or ""
                )

                return schemas.MediaInfo(
                    type=media_type,
                    title=title,
                    year=year_val,
                    title_year=f"{title} ({year_val})" if year_val else title,
                    mediaid_prefix="iqiyi",
                    media_id=media_id,
                    poster_path=poster,
                )
            except Exception as e:
                logger.warning(f"爱奇艺数据转换失败: {str(e)}, item={item}")
                return None

        try:
            items = self.__request(
                page=page,
                mtype=mtype,
                order=order,
                year=year,
                area=area,
                genre=genre,
                pay=pay,
                status=status,
            )
        except Exception as e:
            logger.error(f"爱奇艺探索请求异常: {str(e)}")
            return []

        results = [_item_to_media(item) for item in items]
        return [r for r in results if r is not None]

    @staticmethod
    def iqiyi_filter_ui() -> List[dict]:
        """
        构建探索页过滤 UI
        """
        # 种类选择行
        mtype_chips = [
            {
                "component": "VChip",
                "props": {"filter": True, "tile": True, "value": key},
                "text": val["name"],
            }
            for key, val in CHANNEL_PARAMS.items()
        ]

        ui = [
            {
                "component": "div",
                "props": {"class": "flex justify-start items-center"},
                "content": [
                    {
                        "component": "div",
                        "props": {"class": "mr-5"},
                        "content": [{"component": "VLabel", "text": "种类"}],
                    },
                    {
                        "component": "VChipGroup",
                        "props": {"model": "mtype"},
                        "content": mtype_chips,
                    },
                ],
            }
        ]

        # 追加各频道过滤条件
        for item in build_filter_ui():
            ui.append(item)

        return ui

    @eventmanager.register(ChainEventType.DiscoverSource)
    def discover_source(self, event: Event):
        """
        注册爱奇艺为探索数据源
        """
        if not self._enabled:
            return

        event_data: DiscoverSourceEventData = event.event_data

        iqiyi_source = schemas.DiscoverMediaSource(
            name="爱奇艺",
            mediaid_prefix="iqiyidiscover",
            api_path=f"plugin/IqiyiDiscover/iqiyi_discover?apikey={settings.API_TOKEN}",
            filter_params={
                "mtype": "tv",
                "order": None,
                "year": None,
                "area": None,
                "genre": None,
                "pay": None,
                "status": None,
            },
            filter_ui=self.iqiyi_filter_ui(),
            depends={
                "order": ["mtype"],
                "year": ["mtype"],
                "area": ["mtype"],
                "genre": ["mtype"],
                "pay": ["mtype"],
                "status": ["mtype"],
            },
        )

        if not event_data.extra_sources:
            event_data.extra_sources = [iqiyi_source]
        else:
            event_data.extra_sources.append(iqiyi_source)

    def stop_service(self):
        pass