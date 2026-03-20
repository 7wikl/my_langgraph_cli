"""Market data types - Pydantic models corresponding to TypeScript Zod schemas."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class Market(str, Enum):
    SH = "SH"
    SZ = "SZ"


class ChartType(str, Enum):
    CANDLESTICK = "candlestick"
    LINE = "line"
    AREA = "area"


# ---------------------------------------------------------------------------
# Stock Data Models
# ---------------------------------------------------------------------------


class StockQuote(BaseModel):
    symbol: str
    name: str
    market: Market
    price: float
    change: float
    change_percent: float = Field(alias="changePercent")
    volume: float
    turnover: float
    open: float
    high: float
    low: float
    pre_close: float = Field(alias="preClose")
    pe_ratio: Optional[float] = Field(default=None, alias="peRatio")
    pb_ratio: Optional[float] = Field(default=None, alias="pbRatio")
    turnover_rate: Optional[float] = Field(default=None, alias="turnoverRate")
    timestamp: str

    model_config = {"populate_by_name": True}


class IndexData(BaseModel):
    code: str
    name: str
    current: float
    change: float
    change_percent: float = Field(alias="changePercent")
    volume: float
    turnover: float
    open: float
    high: float
    low: float
    timestamp: str


class ETFData(StockQuote):
    net_asset_value: Optional[float] = Field(default=None, alias="netAssetValue")
    premium_rate: Optional[float] = Field(default=None, alias="premiumRate")

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Tushare API Response
# ---------------------------------------------------------------------------


class TushareRealtimeResponse(BaseModel):
    code: str
    data: dict
    message: Optional[str] = None


# ---------------------------------------------------------------------------
# Tool Input Schemas
# ---------------------------------------------------------------------------


class RealtimeQuoteInput(BaseModel):
    symbol: str = Field(description="Stock symbol (e.g., '000001' for 平安银行)")
    market: Market = Field(description="Market: 'SH' for Shanghai, 'SZ' for Shenzhen")


class SearchStockInput(BaseModel):
    query: str = Field(description="Search query for stock name or symbol")
    market: str = Field(default="all", description="Market filter")
    limit: int = Field(default=10, ge=1, le=50)


# ---------------------------------------------------------------------------
# DH API Types
# ---------------------------------------------------------------------------


class StockRankingItem(BaseModel):
    sec: str
    fdatas: list[float]
    idatas: list[str]


class StockRankingResponse(BaseModel):
    datas: list[StockRankingItem]
    start_idx: int = Field(alias="startIdx")


class IndexDataItem(BaseModel):
    sec: str
    close: float
    prev_close: float = Field(alias="prevClose")
    total_money: float = Field(alias="totalMoney")

    model_config = {"populate_by_name": True}


class IndexResponse(BaseModel):
    datas: list[IndexDataItem]


class KLineData(BaseModel):
    time: str
    open: float
    close: float
    low: float
    high: float
    volume: str
    money: str
    iopv: float
    interest: float
    open_interest: str = Field(alias="openInterest")
    prev_close: float = Field(alias="prevClose")

    model_config = {"populate_by_name": True}


class KLineResponse(BaseModel):
    left_datas: list[KLineData] = Field(alias="leftDatas")
    left_pdp: int = Field(alias="leftPdp")
    right_datas: list[KLineData] = Field(alias="rightDatas")
    right_pdp: int = Field(alias="rightPdp")

    model_config = {"populate_by_name": True}


class TimeShareData(BaseModel):
    datas: list[float]
    trading_day: str = Field(alias="tradingday")
    prev_close: float = Field(alias="prevClose")

    model_config = {"populate_by_name": True}


class TimeShareResponse(BaseModel):
    left_datas: list[dict] = Field(alias="leftDatas")
    left_pdp: int = Field(alias="leftPdp")
    right_datas: list[TimeShareData]
    right_pdp: int = Field(alias="rightPdp")

    model_config = {"populate_by_name": True}


class FundFlowItem(BaseModel):
    sec: str
    fdatas: list[float]


class FundFlowResponse(BaseModel):
    datas: list[FundFlowItem]
    date: int


class RealtimeSnapshot(BaseModel):
    time: str
    open: float
    now: float
    high: float
    low: float
    volume: str
    money: str
    sellv: list[str]
    sellp: list[float]
    buyv: list[str]
    buyp: list[float]
    status: int
    num_trades: str = Field(alias="numTrades")
    pdp: int
    volume_ave: float = Field(alias="volumeAve")
    volume_ratio: float = Field(alias="volumeRatio")
    up_limit: float = Field(alias="upLimit")
    down_limit: float = Field(alias="downLimit")
    prev_close: float = Field(alias="prevClose")
    total_volume: str = Field(alias="totalVolume")
    total_bvol: str = Field(alias="totalBvol")
    total_svol: str = Field(alias="totalSvol")
    total_money: str = Field(alias="totalMoney")
    current_volume: str = Field(alias="currentVolume")
    interest: float
    iopv: float
    prev_iopv: float = Field(alias="prevIopv")
    open_interest: str = Field(alias="openInterest")
    prev_open_interest: str = Field(alias="prevOpenInterest")
    settle_price: float = Field(alias="settlePrice")
    sellm_all: str = Field(alias="sellmAll")
    sellm1: str = Field(alias="sellm1")
    buym_all: str = Field(alias="buymAll")
    buym1: str = Field(alias="buym1")
    up_count: list
    down_count: list
    up_all: int = Field(alias="upAll")
    down_all: int = Field(alias="downAll")
    turnover: float


class HistoricalSnapshotItem(BaseModel):
    time: str
    price: float
    volume: str
    buyv: str
    sellv: str


class HistoricalSnapshotResponse(BaseModel):
    datas: list[HistoricalSnapshotItem]
    pdp: int


class AuctionData(BaseModel):
    time: str
    price: float
    volume: str
    buyv: str
    sellv: str


class AuctionResponse(BaseModel):
    datas: list[AuctionData]
    pdp: int


# ---------------------------------------------------------------------------
# DH API Input Schemas
# ---------------------------------------------------------------------------

STOCK_SORT_FIELDS = {
    "BY_CHANGE_PERCENT": 20,
    "BY_PRICE": 1,
    "BY_VOLUME": 4,
    "BY_AMOUNT": 8,
    "BY_CHANGE_AMOUNT": 21,
    "BY_TURNOVER_RATE": 61,
    "BY_PE_TTM": 55,
    "BY_PB": 70,
    "BY_MAIN_NET_INFLOW": 38,
    "BY_MAIN_BUY_RATIO": 40,
    "BY_YEAR_CHANGE": 30,
}


class StockRankingInput(BaseModel):
    block_id: int = Field(default=2768240641, description="板块ID,2768240641为沪深A股")
    start_idx: int = Field(default=0, description="起始索引,用于分页获取数据")
    row_count: int = Field(default=10, ge=1, le=100, description="返回行数")
    sort_id: int = Field(
        default=20,
        description=(
            "排序字段ID: 0=昨收价, 1=现价, 4=总量, 5=今开, 6=最高, 7=最低, "
            "8=总成交额, 20=涨幅%, 21=涨跌额, 23=涨速%, 24=量比%, 25=振幅%, "
            "30=年初至今涨幅%, 38=主力净额, 39=主买净额, 40=主买占比%, "
            "55=市盈率(TTM), 61=换手率%, 62=主力净比%, 68=人均市值, 70=市净率"
        ),
    )
    sort_kind: int = Field(default=1, description="排序方式,1:降序 0:升序")
    filter: int = Field(default=0, description="过滤条件,0表示不过滤")


class MarketIndexInput(BaseModel):
    secs: list[str] = Field(
        default=["sh000001", "sz399001", "sh000688", "sz399006"],
        description="指数代码列表",
    )


class KLineInput(BaseModel):
    sec: str = Field(description="股票代码,市场 + 证券代码,例如:'sz000001'")
    frequency: int = Field(
        default=2,
        description="频率 0:Tick,1:分钟 2:日 3:周 4:月 5:季 6:年",
    )
    left_time: int = Field(default=0, description="历史截至时间, 传0表示从最新一条历史数据开始")
    left_count: int = Field(default=1, description="请求历史数据数量")
    right_time: int = Field(default=0, description="实时起始时间, 传0表示从最旧一条实时数据开始")
    right_count: int = Field(default=1, description="请求实时数据数量")
    freq_multiple: int = Field(default=1, description="频率倍数")
    adjust: int = Field(default=0, description="复权类型 0:不复权 1:前复权 2:后复权")
    adjust_time: int = Field(default=0, description="定点复权时间,传0表示不定点")


class TimeShareInput(BaseModel):
    sec: str = Field(description="股票代码,市场 + 证券代码,例如:'sz000001'")
    left_day_count: int = Field(default=0, description="左侧数据数量")
    left_begin: int = Field(default=0, description="起始时间(毫秒)")
    left_end: int = Field(default=1760173039220, description="左侧截止时间戳")
    right_begin: int = Field(default=0, description="起始时间(毫秒),传0表示从第一条实时数据开始")
    right_end: int = Field(default=1760173159220, description="右侧截止时间戳")


class FundFlowInput(BaseModel):
    cftype: int = Field(
        default=0,
        description="资金流向类型, 0:5日 1:10日 2:20日 3:30日 4:近3月",
    )
    sort_id: int = Field(default=0)
    sort_kind: int = Field(default=1, description="排序方式 1:降序 0:升序")


class RealtimeSnapshotInput(BaseModel):
    sec: str = Field(description="股票代码,市场 + 证券代码,例如:'sz000001'")


class HistoricalSnapshotInput(BaseModel):
    sec: str = Field(description="股票代码,市场 + 证券代码,例如:'sz000001'")
    left_begin: str = Field(default="1762508701000")
    left_end: str = Field(default="1762508761000")


class AuctionInput(BaseModel):
    sec: str = Field(description="股票代码,市场 + 证券代码,例如:'sz000001'")
