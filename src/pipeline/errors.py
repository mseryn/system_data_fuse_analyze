class StageError(RuntimeError):
    """Generic exception for pipeline stage failures."""

    def __init__(self, stage: str, dataset: str, message: str):
        self.stage = stage
        self.dataset = dataset
        super().__init__(f"[{stage}:{dataset}] {message}")
