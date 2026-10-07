"""Static reading projections of pinned upstream archives, without scripts."""

from html.parser import HTMLParser

# The pinned renderer already declares this readable shape in its print rules.
# Apply those content rules to the archived screen view; leave the archive intact.
STATIC_SCRIPT_REPORT_STYLE = """<style data-plotloom-static-script-report>
.expo,.copy,.scmore{display:none!important}
#sec-script>.sec-h>.note,#sec-cast>.sec-h>.note{display:none!important}
.scenes.clip{max-height:none!important;overflow:visible!important}
.scenes.clip::after{display:none!important}
.cast-lines{max-height:none!important;overflow:visible!important}
</style>"""


def static_script_report(report: str) -> str:
    """Append presentation only; never interpret report data or enable handlers."""
    return report + STATIC_SCRIPT_REPORT_STYLE


STATIC_ART_REPORT_STYLE = """<style data-plotloom-static-art-report>
.expo,.copy,.lightbox{display:none!important}
.pr p{display:block!important}
.pr summary::before{content:""}
.zoom:disabled{cursor:default}
</style>"""


class _StaticPromptControls(HTMLParser):
    """Amend current Art/Cast native controls without rewriting archive text."""

    def __init__(self, report: str, *, cast: bool = False) -> None:
        super().__init__(convert_charrefs=False)
        self.report = report
        self.cast = cast
        self.line_offsets = [0]
        # HTMLParser advances its line number only at LF, not at CR or Unicode
        # text separators. Its source coordinates must share that exact model.
        self.line_offsets.extend(index + 1 for index, char in enumerate(report) if char == "\n")
        self.edits: list[tuple[int, str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = (attributes.get("class") or "").split()
        addition = None
        if tag == "details" and "pr" in classes:
            addition = "open"
        elif tag == "button" and ("zoom" in classes or self.cast and "grow" in classes):
            addition = "disabled"
        elif self.cast and tag == "div" and "graph-canvas" in classes:
            addition = "inert"
        if addition is None or addition in attributes:
            return
        raw = self.get_starttag_text()
        line, column = self.getpos()
        self.edits.append((self.line_offsets[line - 1] + column, raw, raw[:-1] + f" {addition}>"))

    def presented(self) -> str:
        self.feed(self.report)
        self.close()
        result: list[str] = []
        cursor = 0
        for offset, original, replacement in self.edits:
            if offset < cursor or self.report[offset:offset + len(original)] != original:
                raise ValueError("Prompt report control offset does not match source")
            result.extend((self.report[cursor:offset], replacement))
            cursor = offset + len(original)
        result.append(self.report[cursor:])
        return "".join(result)


def static_art_report(report: str) -> str:
    """Reveal native prompt disclosures; leave script-only image zoom disabled."""
    return _StaticPromptControls(report).presented() + STATIC_ART_REPORT_STYLE


STATIC_STORYBOARD_REPORT_STYLE = """<style data-plotloom-static-storyboard-report>
.expo,.copy,.shmore,.lightbox{display:none!important}
.shots.clip{max-height:none!important;overflow:visible!important}
.shots.clip::after{display:none!important}
.pp{display:block!important;max-height:none!important;overflow:visible!important}
img.frame,img.subf,img.bimg{cursor:default!important}
</style>"""


def static_storyboard_report(report: str) -> str:
    """Use pinned print visibility; image/prompt-copy handlers remain disabled."""
    return report + STATIC_STORYBOARD_REPORT_STYLE


STATIC_CAST_REPORT_STYLE = """<style data-plotloom-static-cast-report>
.search,.expo,.copy,.copy-img,.syn-more,.gtoggle,.glabtoggle,.roster,.roster-h,.nomatch,.lightbox{display:none!important}
.shell{display:block!important}
.side{position:static!important;height:auto!important;max-height:none!important;overflow:visible!important}
.char,.graph{display:block!important}
.graph-h .hint{display:none!important}
.syn-clamp{cursor:default}
.syn-clamp p{display:block!important;-webkit-line-clamp:unset!important;overflow:visible!important;mask-image:none!important;-webkit-mask-image:none!important}
.pr p{display:block!important}
.pr summary::before{content:""}
.grel-list{max-height:none!important;overflow:visible!important}
.gnode,.grow:disabled,.zoom:disabled{cursor:default!important}
</style>"""


def static_cast_report(report: str) -> str:
    """Reveal all pinned character/relationship content and native prompts."""
    return _StaticPromptControls(report, cast=True).presented() + STATIC_CAST_REPORT_STYLE
