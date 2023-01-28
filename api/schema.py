import strawberry


from .bus import BusQuery
from .sentry_extension import SentryExtension


@strawberry.type
class Query(BusQuery):
    ...


schema = strawberry.federation.Schema(Query, extensions=[SentryExtension])
