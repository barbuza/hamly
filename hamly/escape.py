# -*- coding: utf-8 -*-

try:

    from .escape_fast import escape, soft_unicode
    
    quoteattr = escape

except ImportError:
    
    soft_unicode = unicode

    def escape(s):
        return soft_unicode(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def quoteattr(at):
        return soft_unicode(at).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&#34;").replace("'", "&#39;")
