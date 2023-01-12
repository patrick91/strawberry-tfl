import strawberry


from .bus import BusQuery


@strawberry.type
class Query(BusQuery):
    ...


schema = strawberry.federation.Schema(Query)
