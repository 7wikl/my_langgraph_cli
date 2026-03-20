"""K-line chart tool - triggers frontend rendering of stock price charts."""

from datetime import datetime, timezone
from typing import Literal, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field


class ShowKlineCardInput(BaseModel):
    sec: str = Field(description="股票代码，如 'sz000001'")
    frequency: int = Field(default=2, description="频率 0:Tick,1:分钟 2:日 3:周 4:月 5:季 6:年")
    left_time: int = Field(default=0, description="历史截至时间,0 表示最新一条历史数据")
    left_count: int = Field(default=60, description="请求历史数据数量,最低为60条")
    right_time: int = Field(default=0, description="实时起始时间,0 表示最旧实时数据")
    right_count: int = Field(default=1, description="请求实时数据数量")
    freq_multiple: int = Field(default=1, description="频率倍数")
    adjust: int = Field(default=1, description="复权类型 0:不复权 1:前复权 2:后复权")
    adjust_time: int = Field(default=0, description="定点复权时间,0 表示不定点")
    sec_name: Optional[str] = Field(default=None, description="股票名称，如 '平安银行'")
    chart_type: Optional[Literal["candlestick", "line", "area"]] = Field(
        default=None, alias="chartType", description="图表类型"
    )
    description: Optional[str] = Field(default=None, description="这个图的简单描述")

    model_config = {"populate_by_name": True}


@tool(args_schema=ShowKlineCardInput)
def show_kline_card(input: ShowKlineCardInput) -> dict:
    """K 线图展示工具（仅负责触发前端渲染，不返回行情数据）。

    当用户提出以下任何需求时，应调用此工具:
    - 查询某支股票的行情、走势、价格变化
    - 查看某股票的 K 线图、走势图、历史走势
    - 要求"画图"、"看图"、"K线图"、"趋势图"、"走势图"
    - 希望查看某股票在某周期（如 日/周/月/分钟）的表现
    - 用户只说"看看 [股票代码] 最近怎么样？" 或类似模糊的趋势类问题
    """
    chart_type = input.chart_type or "candlestick"
    description = input.description or f"股票 {input.sec} 的 K 线走势"

    return {
        "sec": input.sec,
        "sec_name": input.sec_name,
        "frequency": input.frequency,
        "left_time": input.left_time,
        "left_count": input.left_count,
        "right_time": input.right_time,
        "right_count": input.right_count,
        "freq_multiple": input.freq_multiple,
        "adjust": input.adjust,
        "adjust_time": input.adjust_time,
        "chart_type": chart_type,
        "description": description,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
