import pathlib
import sys
import zipfile

src = pathlib.Path("gcj_rectify_plugin")
version = sys.argv[1]
dist_dir = pathlib.Path("dist")
dist_dir.mkdir(exist_ok=True)
zip_name = str(dist_dir / f"gcj_rectify_plugin-v{version}.zip")

with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zf:
    for f in src.rglob("*"):
        if "__pycache__" in f.parts:
            continue
        zf.write(f, f.relative_to(src.parent))

print(f"Done: {zip_name}")
