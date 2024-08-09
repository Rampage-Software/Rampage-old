# The compute resolution used to report the progress. Resolution 100 will
# report progress every 1%.

# Example usage:
# params = {
#     'N': 1234567890,
#     'A': 42,
#     'T': 1000,
# }

PROGRESS_RESOLUTION = 1000

class TimeLockPuzzleSolver:
    def __init__(self, params):
        self.n = params['N']
        self.a = params['A']
        self.t = params['T']
        self.cur_base = self.a
        self.cur_t = 0

    def run(self):
        batch_size = max(1, self.t / PROGRESS_RESOLUTION)
        while not self.is_done():
            self.do_repeated_squaring(batch_size)
        return self.answer()

    def do_repeated_squaring(self, iterations):
        target_t = (
            min(self.t, self.cur_t + iterations)
            if iterations is not None
            else self.t
        )
        while self.cur_t < target_t:
            self.cur_base = self.square(self.cur_base) % self.n
            self.cur_t += 1

    def square(self, x):
        return x * x

    def answer(self):
        if not self.is_done():
            return None
        return str(self.cur_base)

    def is_done(self) -> bool:
        return self.cur_t == self.t