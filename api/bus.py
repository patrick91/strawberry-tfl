from datetime import timedelta

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


@strawberry.type
class BusStop:
    id: strawberry.ID
    common_name: str
    buses: list[str]
    stop_letter: str
    towards: str

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


@strawberry.type
class BusQuery:
    @strawberry.field
    async def find_bus_stop(self, latitude: float, longitude: float) -> list[BusStop]:
        stops: list[BusStop] = []

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.tfl.gov.uk/StopPoint/",
                params={
                    "lat": latitude,
                    "lon": longitude,
                    "stopTypes": "NaptanPublicBusCoachTram",
                },
            )

            data = response.json()["stopPoints"]

            for stop in data:
                towards = next(
                    property["value"]
                    for property in stop["additionalProperties"]
                    if property["key"] == "Towards"
                )
                stops.append(
                    BusStop(
                        id=stop["id"],
                        common_name=stop["commonName"],
                        buses=[line["name"] for line in stop["lines"]],
                        stop_letter=stop["stopLetter"],
                        towards=towards,
                    )
                )

        return stops
