class DummyWorker:
    def __init__(self):
        self.active = False

    def start(self):
        self.active = True

    def stop(self):
        self.active = False


def test_worker_start_stop():
    worker = DummyWorker()
    worker.start()
    assert worker.active  # nosec
    worker.stop()
    assert not worker.active  # nosec
