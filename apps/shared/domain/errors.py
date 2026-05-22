class PredictionJobNotFoundError(LookupError):
    def __init__(self, *, job_id: object) -> None:
        super().__init__(f"Prediction job not found: {job_id}")
        self.job_id = job_id
