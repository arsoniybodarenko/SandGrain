class FixedTimestep:
    def __init__(self, tps, max_steps=4):
        self.dt = 1.0 / tps
        self.max_steps = max_steps
        self.accumulator = 0.0

    def advance(self, frame_seconds):
        self.accumulator += min(frame_seconds, self.dt * self.max_steps)
        steps = int(self.accumulator / self.dt + 1e-9)
        if steps > self.max_steps:
            steps = self.max_steps
        self.accumulator -= steps * self.dt
        if self.accumulator < 0.0:
            self.accumulator = 0.0
        return steps
