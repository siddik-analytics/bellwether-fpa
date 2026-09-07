# Power BI Desktop's stock base theme

`Fluent2-CY26SU08.json`, exactly as Power BI Desktop 2.157.1354.0 writes it into a project's
`StaticResources/SharedResources/BaseThemes/`. **Microsoft's content, not this project's.**

It is here because it is required, not because it is wanted. `report.json` names a base theme
under `themeCollection` and points `resourcePackages` at this path, and all three Desktop
references do so. Generating a report definition without it produces a shape none of them
produce — and a `resourcePackages` entry pointing at a file that is not there is a dangling
reference.

The generator copies this file into the report on every build rather than authoring one, so
nothing here is ours except the decision to include it.
