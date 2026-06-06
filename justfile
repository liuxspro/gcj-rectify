# list all available recipes
default:
    @just --list

_clean_dist:
    @rm -rf dist

# run the development server
dev:
    uv run uvicorn gcj_rectify_server:app --reload

# build the project
build: _clean_dist
    uv build

# publish the project to PyPI
publish: build
    uv publish
