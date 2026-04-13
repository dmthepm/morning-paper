---
pdf_options:
  format: Letter
  margin: 0.6in 0.55in
  printBackground: true
  headerTemplate: "<span></span>"
  footerTemplate: "<div style='font-size:7pt;font-family:Courier New,monospace;width:100%;padding:0 0.2in;box-sizing:border-box;'><div style='float:left;'>Morning Paper</div><div style='float:right;'>Page <span class='pageNumber'></span></div></div>"
css: |
  @import url('https://fonts.googleapis.com/css2?family=Courier+Prime:ital,wght@0,400;0,700;1,400&display=swap');

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: 'Courier Prime', 'Courier New', Courier, monospace;
    font-size: 9.5pt;
    line-height: 1.3;
    color: #000000;
    background: #ffffff;
    column-count: 2;
    column-gap: 0.25in;
    column-fill: auto;
  }

  .brief-title {
    column-span: all;
    text-align: center;
    font-size: 36pt;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding-top: 1.5in;
    padding-bottom: 8pt;
  }

  .brief-date {
    column-span: all;
    text-align: center;
    font-size: 18pt;
    font-weight: 700;
    color: #000;
    margin-bottom: 8pt;
  }

  .brief-tagline {
    column-span: all;
    text-align: center;
    font-size: 9pt;
    color: #666;
    letter-spacing: 0.05em;
    border-bottom: 2px solid #000;
    padding-bottom: 12pt;
    margin-bottom: 18pt;
  }

  h2 {
    font-size: 14pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-top: 10pt;
    margin-bottom: 0;
    padding-bottom: 0;
    break-after: avoid;
    break-before: avoid;
  }

  .meta-bar {
    display: flex;
    gap: 8pt;
    padding: 5pt 8pt;
    margin-bottom: 10pt;
    border: 1px solid #000;
    align-items: flex-start;
  }

  .meta-bar-photo {
    width: 30pt;
    height: 30pt;
    border-radius: 3px;
    border: 1px solid #000;
    object-fit: cover;
    flex-shrink: 0;
  }

  .meta-bar-content {
    flex: 1;
    min-width: 0;
  }

  .meta-bar-name {
    font-weight: 700;
    font-size: 8.5pt;
    letter-spacing: 0.02em;
    line-height: 1.2;
  }

  .meta-bar-handle {
    font-size: 7pt;
    color: #555;
    line-height: 1.2;
  }

  .meta-bar-stats {
    font-size: 7pt;
    color: #444;
    line-height: 1.2;
    margin-top: 2pt;
  }

  .article-body p {
    font-size: 9pt;
    line-height: 1.35;
    color: #000;
    margin-bottom: 0;
    text-indent: 0.2in;
    text-align: justify;
    hyphens: auto;
  }

  .article-body > p:first-of-type::first-letter {
    font-size: 22pt;
    font-weight: 700;
    float: left;
    line-height: 0.8;
    margin-right: 2pt;
    margin-top: 2pt;
  }

  img {
    float: left;
    width: 98%;
    height: auto;
    border: 1px solid #000;
    margin: 6pt 6pt 8pt 0;
    break-inside: avoid;
  }

  .article-divider {
    column-span: all;
    border-top: 2px solid #000;
    margin: 10pt 0 4pt 0;
    position: relative;
  }

  .article-divider::after {
    content: "◆";
    position: absolute;
    left: 50%;
    top: -8pt;
    transform: translateX(-50%);
    background: #fff;
    padding: 0 6pt;
    font-size: 8pt;
  }

  .source-line {
    column-span: all;
    font-size: 7pt;
    color: #555555;
    margin-top: 8pt;
    margin-bottom: 10pt;
  }
---

<div class="brief-title">Morning Paper</div>
<div class="brief-date">{{ date_human }}</div>
<div class="brief-tagline">{{ tagline }}</div>

## {{ article_1_title }}

<div class="meta-bar">
  <img src="{{ article_1_author_image }}" class="meta-bar-photo" alt="{{ article_1_author }}">
  <div class="meta-bar-content">
    <div class="meta-bar-name">{{ article_1_author }}</div>
    <div class="meta-bar-handle">{{ article_1_handle_role }}</div>
    <div class="meta-bar-stats">{{ article_1_stats }}</div>
  </div>
</div>

<div class="article-body">

{{ article_1_body_markdown }}

</div>

<div class="source-line">{{ article_1_source_line }}</div>

<div class="article-divider"></div>

## {{ article_2_title }}

<div class="meta-bar">
  <img src="{{ article_2_author_image }}" class="meta-bar-photo" alt="{{ article_2_author }}">
  <div class="meta-bar-content">
    <div class="meta-bar-name">{{ article_2_author }}</div>
    <div class="meta-bar-handle">{{ article_2_handle_role }}</div>
    <div class="meta-bar-stats">{{ article_2_stats }}</div>
  </div>
</div>

<div class="article-body">

{{ article_2_body_markdown }}

</div>

<div class="source-line">{{ article_2_source_line }}</div>

<div class="article-divider"></div>

## {{ article_3_title }}

<div class="meta-bar">
  <img src="{{ article_3_author_image }}" class="meta-bar-photo" alt="{{ article_3_author }}">
  <div class="meta-bar-content">
    <div class="meta-bar-name">{{ article_3_author }}</div>
    <div class="meta-bar-handle">{{ article_3_handle_role }}</div>
    <div class="meta-bar-stats">{{ article_3_stats }}</div>
  </div>
</div>

<div class="article-body">

{{ article_3_body_markdown }}

</div>

<div class="source-line">{{ article_3_source_line }}</div>
