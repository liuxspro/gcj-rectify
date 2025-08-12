from .plugin import GCJRectifyPlugin


def classFactory(iface):
    """QGIS Plugin"""
    return GCJRectifyPlugin(iface)
