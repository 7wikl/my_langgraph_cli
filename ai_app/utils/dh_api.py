"""DH API client - wraps the internal stock data API."""

from __future__ import annotations

from typing import Optional

import httpx

from ai_app.types.market import (
    AuctionInput,
    AuctionResponse,
    FundFlowInput,
    FundFlowResponse,
    HistoricalSnapshotInput,
    HistoricalSnapshotResponse,
    KLineInput,
    KLineResponse,
    MarketIndexInput,
    RealtimeSnapshot,
    RealtimeSnapshotInput,
    StockRankingInput,
    StockRankingResponse,
    TimeShareInput,
    TimeShareResponse,
)


class DHAPI:
    """Client for the internal DH stock data API."""

    def __init__(self, base_url: str = "http://106.15.1.254:2380"):
        self.base_url = base_url

    async def _request(self, endpoint: str, data: Optional[dict] = None) -> dict:
        url = f"{self.base_url}{endpoint}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, json=data)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise RuntimeError(f"DH API request failed for {endpoint}: {e}")

    async def get_stock_ranking(
        self, input_data: Optional[StockRankingInput] = None
    ) -> StockRankingResponse:
        params = input_data or StockRankingInput()
        result = await self._request("/dh/r", params.model_dump(by_alias=True))
        return StockRankingResponse(**result)

    async def get_market_index(
        self, input_data: Optional[MarketIndexInput] = None
    ) -> dict:
        params = input_data or MarketIndexInput()
        result = await self._request("/dh/i", params.model_dump(by_alias=True))
        return result

    async def get_kline_data(self, input_data: KLineInput) -> KLineResponse:
        result = await self._request("/dh/k", input_data.model_dump(by_alias=True))
        return KLineResponse(**result)

    async def get_time_share_data(self, input_data: TimeShareInput) -> TimeShareResponse:
        result = await self._request("/dh/m", input_data.model_dump(by_alias=True))
        return TimeShareResponse(**result)

    async def get_fund_flow(
        self, input_data: Optional[FundFlowInput] = None
    ) -> FundFlowResponse:
        params = input_data or FundFlowInput()
        result = await self._request("/dh/cf", params.model_dump(by_alias=True))
        return FundFlowResponse(**result)

    async def get_realtime_snapshot(
        self, input_data: RealtimeSnapshotInput
    ) -> RealtimeSnapshot:
        result = await self._request("/dh/s", input_data.model_dump(by_alias=True))
        return RealtimeSnapshot(**result)

    async def get_historical_snapshot(
        self, input_data: Optional[HistoricalSnapshotInput] = None
    ) -> HistoricalSnapshotResponse:
        params = input_data or HistoricalSnapshotInput()
        result = await self._request("/dh/hs", params.model_dump(by_alias=True))
        return HistoricalSnapshotResponse(**result)

    async def get_auction_data(self, input_data: AuctionInput) -> AuctionResponse:
        result = await self._request("/dh/a", input_data.model_dump(by_alias=True))
        return AuctionResponse(**result)
