import pytest

from core.batch_processor import BatchProcessor
from core.chdman import CHDManager


@pytest.fixture
def processor():
    return BatchProcessor(CHDManager())


def test_batch_add_item(processor, tmp_path):
    # Create a dummy input file
    input_file = tmp_path / "in.bin"
    input_file.write_text("dummy content")

    processor.add_item(
        input_path=str(input_file),
        output_path=str(tmp_path / "out.chd"),
        media_type="cd",
        compression="zlib",
        hunk_size=2048,
        metadata={"game": "Test Game"},
    )
    assert len(processor.queue) == 1
    item = processor.queue[0]
    assert item.input_path == str(input_file)
    assert item.output_path == str(tmp_path / "out.chd")
    assert item.media_type == "cd"
