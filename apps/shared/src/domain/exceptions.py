class InvalidValueObject(ValueError):
    def __init__(self, *, name: str, reason: str, value: object) -> None:
        super().__init__(f"{name}: {reason}. value={value!r}")
        self.name = name
        self.reason = reason
        self.value = value
