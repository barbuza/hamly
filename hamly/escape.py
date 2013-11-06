# -*- coding: utf-8 -*-

import sys

try:

    from .escape_fast import escape, soft_unicode
    
    quoteattr = escape

except ImportError:
    
    if sys.version_info[0] < 3:
        soft_unicode = unicode
    else:
        soft_unicode = str

    def escape(s):
        return soft_unicode(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def quoteattr(at):
        return soft_unicode(at).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&#34;").replace("'", "&#39;")
