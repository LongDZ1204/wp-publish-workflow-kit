# Image preparation standards

Project-specific image rules in the selected profile inside `projects/<client>/publish-context.json`
override these defaults.

## Filename

- Use lowercase ASCII words separated by hyphens.
- Describe the visible subject and its role; do not stuff keywords.
- Keep the original extension unless the project explicitly allows conversion.
- Never rename an existing live-media URL during an AUDIT run without approval.

## Alternative text

- Describe what is visibly useful in the image and why it matters in context.
- Keep it concise and unique within the article.
- Use `alt=""` for decorative images.
- Do not begin with “image of” or “picture of”.
- Do not infer details that are not visible or supplied by the source.

## Caption

- Add a caption only when it contributes information not already stated nearby.
- Keep it to one or two short sentences.
- Do not use a caption as a place for keyword repetition.

## Technical defaults

- Maximum width: 1200 px.
- Target maximum file size: 150 KB, unless legibility requires more.
- Preserve aspect ratio and use the sRGB colour profile.
- Do not overwrite source files; write optimized files to a separate output path.
- Include `width` and `height` attributes in final HTML to reduce layout shift.
- Lazy-load body images; do not lazy-load the main above-the-fold image.
