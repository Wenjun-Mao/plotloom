# Chinese application copy regression

`chinese-ui-copy.test.ts` scans all handwritten TSX for ordinary static JSX text
and label/title/placeholder/description/accessibility attributes. Every exception
is an exact string at its owning file; unused exceptions fail the check.

| Exception | Reason |
| --- | --- |
| Plotloom | Product brand in workspace, reader and player |
| PLOTLOOM_IMAGE_EXCHANGE_ROOT | Exact operator configuration key in image technical setup |
| xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx | Task identity shape in specialist settings |
| sha256 / SHA-256 | Standard content digest identity in technical metadata |
| JSON | Standard structured data format in the typed value editor |

Model/brand names, standard units and protocol names embedded in clear Chinese
sentences remain useful terms. Creative prose, names, selected preset values,
source quotations, raw JSON, exact provider diagnostics/instructions and immutable
standalone report HTML retain source ownership. This test intentionally does not
translate expressions or inspect report HTML. Feature render tests and desktop
browser inspection remain necessary for dynamic labels, mixed sentences and states.
