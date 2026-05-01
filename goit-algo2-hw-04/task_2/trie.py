class TrieNode:
    def __init__(self):
        self.children = {}
        self.value = None
        self.is_terminal = False


class Trie:
    def __init__(self):
        self.root = TrieNode()
        self.size = 0

    def put(self, key, value=None):
        if not isinstance(key, str) or not key:
            raise TypeError(
                f"Illegal argument for put: key = {key} must be a non-empty string"
            )

        current = self.root
        for char in key:
            if char not in current.children:
                current.children[char] = TrieNode()
            current = current.children[char]

        if not current.is_terminal:
            self.size += 1
        current.is_terminal = True
        current.value = value

    def get(self, key):
        if not isinstance(key, str) or not key:
            raise TypeError(
                f"Illegal argument for get: key = {key} must be a non-empty string"
            )

        current = self.root
        for char in key:
            if char not in current.children:
                return None
            current = current.children[char]

        return current.value if current.is_terminal else None

    def delete(self, key):
        if not isinstance(key, str) or not key:
            raise TypeError(
                f"Illegal argument for delete: key = {key} must be a non-empty string"
            )

        deleted = False

        def _delete(node, depth):
            nonlocal deleted

            if depth == len(key):
                if not node.is_terminal:
                    return False
                node.is_terminal = False
                node.value = None
                self.size -= 1
                deleted = True
                return len(node.children) == 0

            char = key[depth]
            if char not in node.children:
                return False

            should_delete_child = _delete(node.children[char], depth + 1)
            if should_delete_child:
                del node.children[char]
                return len(node.children) == 0 and not node.is_terminal

            return False

        _delete(self.root, 0)
        return deleted

    def is_empty(self):
        return self.size == 0

    def longest_prefix_of(self, s):
        if not isinstance(s, str) or not s:
            raise TypeError(
                f"Illegal argument for longestPrefixOf: s = {s} must be a non-empty string"
            )

        current = self.root
        longest_prefix = ""
        current_prefix = ""

        for char in s:
            if char not in current.children:
                break
            current = current.children[char]
            current_prefix += char
            if current.is_terminal:
                longest_prefix = current_prefix

        return longest_prefix

    def keys_with_prefix(self, prefix):
        if not isinstance(prefix, str):
            raise TypeError(
                f"Illegal argument for keysWithPrefix: prefix = {prefix} must be a string"
            )

        current = self.root
        for char in prefix:
            if char not in current.children:
                return []
            current = current.children[char]

        result = []
        self._collect(current, list(prefix), result)
        return result

    def keys(self):
        result = []
        self._collect(self.root, [], result)
        return result

    def _collect(self, node, path, result):
        if node.is_terminal:
            result.append("".join(path))

        for char, next_node in node.children.items():
            path.append(char)
            self._collect(next_node, path, result)
            path.pop()
