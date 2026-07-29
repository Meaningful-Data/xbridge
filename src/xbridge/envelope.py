"""Detection and unwrapping of message envelopes around XBRL-XML instances.

Some reporting applications do not deliver a bare XBRL-XML instance. Instead
they wrap the ``xbrli:xbrl`` element inside a proprietary message envelope
(for example the OneGate ``XbrlDeclarationReport`` used by the NBB). This
module gives xbridge explicit control over which of those envelope formats are
accepted: recognised envelopes are transparently unwrapped so the rest of the
pipeline sees a normal ``xbrli:xbrl`` root, while unknown roots are rejected
with a clear error instead of being parsed into a silently empty instance.
"""

from __future__ import annotations

from lxml import etree

from xbridge.exceptions import UnsupportedInstanceFormatError

#: Clark-notation tag of the XBRL instance root element.
XBRLI_XBRL_TAG = "{http://www.xbrl.org/2003/instance}xbrl"

#: Whitelist of accepted envelope roots, mapping the Clark-notation tag of the
#: envelope's document root to a human-readable format name. To accept another
#: wrapper format, add an entry here.
ACCEPTED_ENVELOPES = {
    "{http://www.onegate.eu/2010-01-01}XbrlDeclarationReport": "OneGate",
}


def _accepted_formats_description() -> str:
    """Human-readable list of the formats xbridge accepts."""
    return ", ".join(["xbrli:xbrl", *ACCEPTED_ENVELOPES.values()])


def unwrap_xbrl_root(document_root: etree._Element) -> etree._Element:
    """Return the ``xbrli:xbrl`` element, stripping a recognised envelope if present.

    :param document_root: The root element of the parsed XML document.

    :return: The ``xbrli:xbrl`` element. When *document_root* is already the
        instance root this is returned unchanged; when it is a recognised
        envelope the nested ``xbrli:xbrl`` element is returned.

    :raises UnsupportedInstanceFormatError: If the root is neither an
        ``xbrli:xbrl`` element nor a recognised envelope, or if a recognised
        envelope does not contain exactly one ``xbrli:xbrl`` element.
    """
    root_tag = document_root.tag

    # Already a bare XBRL-XML instance: nothing to unwrap.
    if root_tag == XBRLI_XBRL_TAG:
        return document_root

    # A recognised envelope: descend to the nested xbrli:xbrl element.
    if root_tag in ACCEPTED_ENVELOPES:
        format_name = ACCEPTED_ENVELOPES[root_tag]
        inner = document_root.findall(f".//{XBRLI_XBRL_TAG}")
        if len(inner) == 1:
            return inner[0]
        raise UnsupportedInstanceFormatError(
            (
                f"{format_name} envelope must contain exactly one xbrli:xbrl "
                f"element, but found {len(inner)}."
            ),
            offending_value=root_tag,
        )

    # Anything else is not an accepted input format.
    raise UnsupportedInstanceFormatError(
        (
            f"Unsupported instance format: root element is '{root_tag}'. "
            f"Accepted formats are: {_accepted_formats_description()}."
        ),
        offending_value=root_tag,
    )
