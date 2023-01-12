from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

import httpx
import humanize
import strawberry


@strawberry.type
class Arrival:
    id: strawberry.ID
    line_name: str
    time_to_station_: strawberry.Private[int]

    @strawberry.field
    def time_to_station(self) -> str:
        return humanize.naturaldelta(timedelta(seconds=self.time_to_station_))


@strawberry.federation.type(keys=["id"])
class BusStop:
    id: strawberry.ID
    common_name: str
    buses: list[str]
    stop_letter: str | None
    towards: str | None
    direction: str | None

    @strawberry.field
    async def arrivals(self) -> list[Arrival]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.tfl.gov.uk/StopPoint/{self.id}/Arrivals"
            )

            data = response.json()

            arrivals = [
                Arrival(
                    id=arrival["id"],
                    line_name=arrival["lineName"],
                    time_to_station_=arrival["timeToStation"],
                )
                for arrival in data
            ]

        return sorted(arrivals, key=lambda arrival: arrival.time_to_station_)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> BusStop:
        towards = next(
            (
                property["value"]
                for property in data["additionalProperties"]
                if property["key"] == "Towards"
            ),
            None,
        )

        direction = next(
            (
                property["value"]
                for property in data["additionalProperties"]
                if property["key"] == "Direction"
            ),
            None,
        )

        return BusStop(
            id=data["id"],
            common_name=data["commonName"],
            buses=[line["name"] for line in data.get("lines", [])],
            stop_letter=data.get("stopLetter"),
            towards=towards,
            direction=direction,
        )

    @staticmethod
    async def resolve_reference(id: strawberry.ID) -> BusStop:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.tfl.gov.uk/StopPoint/{id}",
            )

            data = response.json()

            return BusStop.from_api(data)


@strawberry.type
class BusQuery:
    @strawberry.field
    async def find_bus_stop(self, latitude: float, longitude: float) -> list[BusStop]:

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.tfl.gov.uk/StopPoint/",
                params={
                    "lat": latitude,
                    "lon": longitude,
                    "stopTypes": "NaptanPublicBusCoachTram",
                },
            )

            data = response.json()

            stops = [BusStop.from_api(stop) for stop in data["stopPoints"]]

        return stops
