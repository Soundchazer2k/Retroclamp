from core.chdman import CHDTask, CHDTaskType

def test_chdtask_user_data():
    user_data = {"row": 1, "original_input": "test_input.cue", "custom_field": "test_value"}
    task = CHDTask(
        task_type=CHDTaskType.CREATE_CD,
        input_file="test_input.cue",
        output_file="test_output.chd",
        algorithms="cdlz,cdzl",
        hunk_size=2448,
        force=True,
        media_type="CD",
        user_data=user_data
    )
    assert task.user_data.get("row") == 1
    assert task.user_data.get("original_input") == "test_input.cue"
    assert task.user_data.get("custom_field") == "test_value"