# Adding an Evidence Source

Source integrations must stay outside the core verification rules.

## Interface

```python
class MyNewAlgerianSource(EvidenceSourceAdapter):
    source_id = "my_source"
    display_name = "My Algerian Source"
    source_type = "PUBLIC"
    official = False
    automation_mode = "AUTOMATED"
    supported_fields = ("rc", "nif")
    limitations = "Describe access and evidentiary limitations."

    async def health_check(self) -> SourceHealth:
        ...

    async def collect(self, claims: dict[str, str]) -> CollectionResult:
        ...
```

## Requirements

Before merging an adapter:

1. document whether the source is official/public/private;
2. confirm that automation is appropriate;
3. do not bypass authentication, CAPTCHA, paywalls or rate limits;
4. define `AVAILABLE/DEGRADED/UNAVAILABLE/MANUAL_ONLY` behavior;
5. return source URLs and snapshot hashes when lawful/practical;
6. include timeouts and rate limits;
7. add deterministic tests;
8. document which fields the source supports;
9. never convert source failure into `NOT_FOUND`;
10. never describe a mock as a real integration.

If automation is inappropriate, implement a manual workflow instead.
