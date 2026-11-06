"""Mini DOM em cima do html.parser da biblioteca padrão (sem instalar nada)."""
from html.parser import HTMLParser

VOID = {"br", "img", "meta", "link", "input", "hr", "source", "area", "base", "col", "embed", "wbr"}
BLOCK = {"p", "div", "li", "ul", "ol", "h1", "h2", "h3", "h4", "tr", "table", "section", "article"}


class Node:
    __slots__ = ("tag", "attrs", "children", "parent")

    def __init__(self, tag, attrs=None, parent=None):
        self.tag = tag
        self.attrs = dict(attrs or {})
        self.children = []
        self.parent = parent

    # ---- consultas -------------------------------------------------------
    def classes(self):
        return (self.attrs.get("class") or "").split()

    def iter(self):
        for c in self.children:
            if isinstance(c, Node):
                yield c
                yield from c.iter()

    def find_all(self, tag=None, cls=None, **attrs):
        out = []
        for n in self.iter():
            if tag and n.tag != tag:
                continue
            if cls and cls not in n.classes():
                continue
            if any(n.attrs.get(k) != v for k, v in attrs.items()):
                continue
            out.append(n)
        return out

    def find(self, tag=None, cls=None, **attrs):
        r = self.find_all(tag, cls, **attrs)
        return r[0] if r else None

    def get(self, k, default=None):
        return self.attrs.get(k, default)

    # ---- texto -----------------------------------------------------------
    def text(self, sep_br="\n"):
        partes = []

        def walk(n):
            for c in n.children:
                if isinstance(c, str):
                    partes.append(c)
                elif c.tag == "br":
                    partes.append(sep_br)
                elif c.tag in ("script", "style"):
                    continue
                else:
                    if c.tag in BLOCK:
                        partes.append("\n")
                    walk(c)
                    if c.tag in BLOCK:
                        partes.append("\n")
        walk(self)
        txt = "".join(partes).replace("\xa0", " ")
        linhas = [" ".join(l.split()) for l in txt.split("\n")]
        return "\n".join(l for l in linhas if l)


class _Builder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root")
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs, self.cur)
        self.cur.children.append(n)
        if tag not in VOID:
            self.cur = n

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, attrs, self.cur))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is not None and n.parent is not None:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.children.append(data)


def parse(html):
    b = _Builder()
    b.feed(html)
    b.close()
    return b.root
