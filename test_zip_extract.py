import os

import libarchive.public

zip_path = r"D:\Testenv\CHD\test files\007 - The World Is Not Enough (USA).zip"
extract_dir = "test_extract_output_libarchive"
os.makedirs(extract_dir, exist_ok=True)

try:
    with libarchive.public.file_reader(zip_path) as entries:
        for entry in entries:
            out_path = os.path.join(extract_dir, entry.pathname)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            print("Extracting:", entry.pathname)
            with open(out_path, "wb") as f:
                for block in entry.get_blocks():
                    f.write(block)
    print("Extraction successful!")
except Exception as e:
    import traceback

    print("Extraction failed:", e)
    traceback.print_exc()
