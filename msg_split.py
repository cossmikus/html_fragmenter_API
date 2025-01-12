from typing import Generator, List, Tuple
from bs4 import BeautifulSoup, Tag

MAX_LEN = 4096  # default fallback max_len

class SplitMessageError(ValueError):
    """
    Raised when it's impossible to keep a fragment under max_len
    (e.g., a single chunk itself is too large).
    """
    pass

# "Блочные теги" that we can open/close across fragment boundaries.
BLOCK_TAGS = {"p", "b", "strong", "i", "ul", "ol", "div", "span"}

def split_message(source: str, max_len: int = MAX_LEN) -> Generator[str, None, None]:
    """
    Splits HTML into fragments, each <= `max_len`.

    Approach: Early flush / look-ahead logic:
      - Before adding a chunk, see if that chunk + overhead of closing 
        block tags would exceed max_len. If so, close (flush) the current fragment first.
      - If a chunk alone is bigger than max_len, raise SplitMessageError.
      - We never break “non-block” tags internally. We treat them as atomic.
      - We forcibly close block tags at fragment boundary and re-open them if still conceptually open.
    """

    soup = BeautifulSoup(source, "html.parser")

    # 1) Convert DOM into list of “chunks”:
    #    - ("block_start", (tag_name, attrs))
    #    - ("block_end", tag_name)
    #    - ("atomic", "<nonblock>...</nonblock>")
    #    - ("text", "some text")
    chunks = _dom_to_chunks(soup)

    open_blocks: List[Tuple[str, dict]] = []
    current_frag: List[str] = []
    current_len = 0

    for ctype, data in chunks:
        if ctype == "block_start":
            # e.g. ("block_start", ("p", {"class": "foo"}))
            tag_name, attrs = data
            open_tag = _make_open_tag(tag_name, attrs)
            close_tag = _make_close_tag(tag_name)
            overhead = len(open_tag) + len(close_tag)

            # if overhead alone > max_len => error
            if overhead > max_len:
                raise SplitMessageError(
                    f"Block <{tag_name}> overhead={overhead} > max_len={max_len}"
                )

            # check if adding open_tag + overhead of eventually closing 
            # all open blocks plus this new one would exceed
            if not _can_fit_chunk(current_len, open_blocks, open_tag, max_len):
                # flush early
                if current_len == 0:
                    raise SplitMessageError(
                        f"Block <{tag_name}> cannot fit in empty fragment"
                    )
                yield _finalize_fragment(current_frag, open_blocks, max_len)
                current_frag.clear()
                current_len = 0
                open_blocks = _reopen_blocks(open_blocks, current_frag)

            # now add the open tag
            current_frag.append(open_tag)
            current_len += len(open_tag)
            # push new block on stack
            open_blocks.append((tag_name, attrs))

        elif ctype == "block_end":
            tag_name = data
            close_tag = _make_close_tag(tag_name)

            # check if we can fit close_tag + overhead for the rest
            if not _can_fit_chunk(current_len, open_blocks, close_tag, max_len):
                if current_len == 0:
                    raise SplitMessageError(
                        f"Closing </{tag_name}> doesn't fit in empty fragment"
                    )
                yield _finalize_fragment(current_frag, open_blocks, max_len)
                current_frag.clear()
                current_len = 0
                open_blocks = _reopen_blocks(open_blocks, current_frag)

            # pop from stack if top
            if open_blocks and open_blocks[-1][0] == tag_name:
                open_blocks.pop()

            current_frag.append(close_tag)
            current_len += len(close_tag)

        elif ctype == "atomic":
            # entire non-block tag as a chunk
            atom_html = data
            chunk_len = len(atom_html)
            if chunk_len > max_len:
                raise SplitMessageError(
                    f"Single atomic chunk length={chunk_len} > max_len={max_len}"
                )

            if not _can_fit_chunk(current_len, open_blocks, atom_html, max_len):
                if current_len > 0:
                    yield _finalize_fragment(current_frag, open_blocks, max_len)
                    current_frag.clear()
                    current_len = 0
                    open_blocks = _reopen_blocks(open_blocks, current_frag)

            current_frag.append(atom_html)
            current_len += chunk_len

        elif ctype == "text":
            # text outside non-block tags
            text_str = data
            idx = 0
            while idx < len(text_str):
                space_left = max_len - _closing_overhead(open_blocks) - current_len
                if space_left <= 0:
                    # flush
                    yield _finalize_fragment(current_frag, open_blocks, max_len)
                    current_frag.clear()
                    current_len = 0
                    open_blocks = _reopen_blocks(open_blocks, current_frag)
                    space_left = max_len - _closing_overhead(open_blocks)

                take = min(space_left, len(text_str) - idx)
                piece = text_str[idx : idx + take]
                idx += take

                if len(piece) > max_len:
                    raise SplitMessageError(
                        f"Single text piece of length={len(piece)} > max_len={max_len}"
                    )

                current_frag.append(piece)
                current_len += len(piece)

        else:
            # unexpected
            pass

    # at end
    if current_len > 0:
        yield _finalize_fragment(current_frag, open_blocks, max_len)

#
# ---------- HELPER FUNCTIONS ----------
#

def _dom_to_chunks(soup: BeautifulSoup):
    """
    Flatten the soup tree into tokens:
      ("block_start", (tag_name, attrs))
      ("block_end", tag_name)
      ("atomic", "<non-block>...</non-block>")
      ("text", "plaintext")
    """
    result = []
    for node in soup.children:
        _extract_node(node, result)
    return result

def _extract_node(node, out_list: List[Tuple[str, object]]):
    if isinstance(node, Tag):
        tname = node.name.lower()
        if tname in BLOCK_TAGS:
            # open
            out_list.append(("block_start", (tname, dict(node.attrs))))
            # parse children
            for child in node.children:
                _extract_node(child, out_list)
            # close
            out_list.append(("block_end", tname))
        else:
            # treat entire <tag>...</tag> as atomic
            html_str = str(node)
            out_list.append(("atomic", html_str))
    else:
        # NavigableString => text
        txt = str(node).replace("\n", " ")
        txt = txt.strip()
        if txt:
            out_list.append(("text", txt))

def _make_open_tag(tag_name: str, attrs: dict) -> str:
    if not attrs:
        return f"<{tag_name}>"
    attr_str = " ".join(f'{k}="{v}"' for k, v in attrs.items())
    return f"<{tag_name} {attr_str}>"

def _make_close_tag(tag_name: str) -> str:
    return f"</{tag_name}>"

def _finish_fragment(tokens: List[str], open_blocks: List[Tuple[str, dict]]) -> str:
    # join all tokens + close
    body = "".join(tokens)
    closing = []
    for (tname, _) in reversed(open_blocks):
        closing.append(_make_close_tag(tname))
    return body + "".join(closing)

def _finalize_fragment(tokens: List[str], open_blocks: List[Tuple[str, dict]], max_len: int) -> str:
    """
    Final check that the final fragment is <= max_len
    """
    frag = _finish_fragment(tokens, open_blocks)
    if len(frag) > max_len:
        raise SplitMessageError(
            f"BUG: final fragment {len(frag)} > max_len={max_len}"
        )
    return frag

def _closing_overhead(open_blocks: List[Tuple[str, dict]]) -> int:
    """
    The total length of all closing tags for the currently open blocks.
    e.g. if open_blocks=[("p",{}),("b",{})], overhead= len("</b></p>")=7
    """
    overhead = 0
    for (tname, _) in open_blocks:
        overhead += len(_make_close_tag(tname))
    return overhead

def _reopen_blocks(prev_stack: List[Tuple[str, dict]], tokens: List[str]) -> List[Tuple[str, dict]]:
    new_stack: List[Tuple[str, dict]] = []
    for (tname, attrs) in prev_stack:
        open_t = _make_open_tag(tname, attrs)
        tokens.append(open_t)
        new_stack.append((tname, attrs))
    return new_stack

def _can_fit_chunk(
    current_len: int,
    open_blocks: List[Tuple[str, dict]],
    chunk: str,
    max_len: int
) -> bool:
    """
    True if we can append 'chunk' plus the final closing overhead
    without exceeding max_len.
    """
    overhead = _closing_overhead(open_blocks)
    needed = current_len + len(chunk) + overhead
    return (needed <= max_len)

def count_characters(html: str) -> int:
    return len(html)
