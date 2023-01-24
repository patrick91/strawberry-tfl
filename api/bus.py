from __future__ import annotations

import os

from datetime import timedelta
from typing import Any

import httpx
import humanize
import strawberry

API_KEY = os.environ["TFL_API_KEY"]


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
                f"https://api.tfl.gov.uk/StopPoint/{self.id}/Arrivals",
                params={"app_key": API_KEY},
            )

            response.raise_for_status()

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

    @staticmethod
    def find_property(data: dict[str, Any], key: str) -> str | None:
        if property := data.get(key):
            return property

        if property := next(
            (
                property["value"]
                for property in data["additionalProperties"]
                if property["key"] == key
            ),
            None,
        ):
            return property

        # TODO: this is probably not needed
        for children in data.get("children", []):
            if property := BusStop.find_property(children, key):
                return property

        return None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> BusStop:
        towards = cls.find_property(data, "Towards")
        direction = cls.find_property(data, "Direction")

        return BusStop(
            id=data["id"],
            common_name=data["commonName"],
            buses=[line["name"] for line in data.get("lines", [])],
            stop_letter=cls.find_property(data, "stopLetter"),
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

            data = next(
                children for children in data["children"] if children["id"] == id
            )

            return BusStop.from_api(data)


@strawberry.type
class BusQuery:
    @strawberry.field
    async def bus_stop(self, id: strawberry.ID) -> BusStop:
        return await BusStop.resolve_reference(id)

    @strawberry.field
    async def find_bus_stop(self, latitude: float, longitude: float) -> list[BusStop]:

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.tfl.gov.uk/StopPoint/",
                params={
                    "lat": latitude,
                    "lon": longitude,
                    "stopTypes": "NaptanPublicBusCoachTram",
                    "app_key": API_KEY,
                },
            )

            response.raise_for_status()

            data = response.json()

            stops = [BusStop.from_api(stop) for stop in data["stopPoints"]]

        return stops
