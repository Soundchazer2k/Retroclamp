import pytest

from core.batch_processor import BatchProcessor
from core.chdman import CHDManager


@pytest.fixture
def processor():
    return BatchProcessor(CHDManager())


def test_batch_add_item(processor):
    processor.add_item(
        input_path="in.bin",
        output_path="out.chd",
        media_type="cd",
        compression="zlib",
        hunk_size=2048,
    )
    assert len(processor.items) == 1  # nosec
