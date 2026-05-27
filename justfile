# justfile for gcj-rectify project

# read plugin version from metadata.txt
_plugin_version := `grep "^version=" gcj_rectify_plugin/metadata.txt | sed 's/version=//' | tr -d '\r\n'`

# package gcj_rectify_plugin into a versioned zip file
plugin_pack: _clean_dist
    @echo "Packaging gcj_rectify_plugin v{{_plugin_version}}..."
    python scripts/pack_plugin.py {{_plugin_version}}

_clean_dist:
    rm -rf dist
