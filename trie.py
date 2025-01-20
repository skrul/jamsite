from pprint import pprint
import json


class Node:
    def __init__(self):
        self.ids = []
        self.children = {}

    def __repr__(self):
        return ", ".join(str(i) for i in self.ids)


class Trie:
    def __init__(self):
        self.root = {}

    def add_doc(self, doc_id, terms):
        for term in terms:
            self._add_c(doc_id, self.root, term)

    def _add_c(self, doc_id, children, s):
        c, s = s[:1], s[1:]
        if c in children:
            node = children[c]
        else:
            node = Node()
            children[c] = node
        node.ids.append(doc_id)
        if len(s) > 0:
            self._add_c(doc_id, node.children, s)

    def to_dict(self):
        d = {}
        self._to_dict(d, self.root)
        return d

    def _to_dict(self, d, children):
        for k, node in children.items():
            d_children = {}
            self._to_dict(d_children, node.children)
            d[k] = {"i": node.ids, "c": d_children}

    def search(self, s):
        n = self.root
        ids = []
        for c in s:
            if c in n:
                ids = n[c].ids
                n = n[c].children
            else:
                return []
        return ids

    def dump(self):
        print(self.root)


if __name__ == "__main__":
    t = Trie()
    # t.add_doc(1, ['hello', 'word'])
    # t.add_doc(2, ['world', 'peace'])
    t.add_doc(1, ["abcd"])
    t.add_doc(2, ["abdd"])
    print(t.search("abddd"))
