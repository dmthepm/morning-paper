---
pdf_options:
  format: Letter
  margin: 0.6in 0.55in
  printBackground: true
  displayHeaderFooter: true
  headerTemplate: "<span></span>"
  footerTemplate: "<div style='font-size:7pt;color:#111111;font-family:Courier New,monospace;width:100%;margin:0 0.55in;'><div style='display:flex;justify-content:space-between;align-items:baseline;'><span>Date: <span class='date'></span></span><span style='text-align:center;'>Morning Paper</span><span style='text-align:right;'>Page <span class='pageNumber'></span> of <span class='totalPages'></span></span></div></div>"
css: |
  @import url('https://fonts.googleapis.com/css2?family=Courier+Prime:ital,wght@0,400;0,700;1,400&display=swap');

  :root {
    --mp-font-body: 'Courier Prime', 'Courier New', Courier, monospace;
    --mp-color-text: #000000;
    --mp-color-muted: #555;
    --mp-color-rule: #000000;
    --mp-color-surface-soft: rgba(0,0,0,0.012);
    --mp-color-surface-card: rgba(0,0,0,0.015);
    --mp-page-margin-y: 0.6in;
    --mp-page-margin-x: 0.55in;
    --mp-body-size: 9pt;
    --mp-body-line-height: 1.38;
    --mp-column-gap: 0.08in;
    --mp-section-title-size: 9pt;
    --mp-section-title-gap-top: 0.12in;
    --mp-section-title-gap-bottom: 0.03in;
    --mp-rule-weight: 1.5px;
    --mp-card-rule-weight: 2px;
    --mp-card-rule-strong: 2.5px;
    --mp-page-title-size: 22pt;
    --mp-page-date-size: 7.5pt;
    --mp-card-title-size: 9pt;
    --mp-card-body-size: 8.5pt;
    --mp-card-meta-size: 7pt;
    --mp-list-size: 7.5pt;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: var(--mp-font-body);
    font-size: var(--mp-body-size);
    line-height: var(--mp-body-line-height);
    color: var(--mp-color-text);
    background: #ffffff;
  }

  @media print {
    body { background: #ffffff !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    @page { size: Letter; margin: var(--mp-page-margin-y) var(--mp-page-margin-x); }
  }

  .page-1-header { margin-bottom: 0.08in; }
  .page-1-title {
    font-size: var(--mp-page-title-size);
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: none;
    color: var(--mp-color-text);
    font-family: var(--mp-font-body);
  }
  .page-1-date {
    font-size: var(--mp-page-date-size);
    color: var(--mp-color-muted);
    margin-top: 0.02in;
    letter-spacing: 0.03em;
  }
  .page-1-rule {
    border-bottom: var(--mp-rule-weight) solid var(--mp-color-rule);
    margin-top: 0.06in;
  }

  .info-row {
    display: flex;
    gap: 0.2in;
    margin-bottom: 0.08in;
    padding: 0.03in 0;
    border-bottom: 1px solid #ccc;
    flex-wrap: wrap;
  }
  .info-block { font-size: var(--mp-card-meta-size); line-height: 1.5; }
  .info-label { font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; font-size: 6.5pt; color: var(--mp-color-muted); }
  .info-value { color: var(--mp-color-text); }
  .info-alert { color: #8b0000; font-weight: 700; }

  h1 {
    font-family: var(--mp-font-body);
    font-size: var(--mp-section-title-size);
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-top: var(--mp-section-title-gap-top);
    margin-bottom: var(--mp-section-title-gap-bottom);
    border-bottom: 1px solid var(--mp-color-rule);
    padding-bottom: 0.02in;
    background: transparent;
    padding-right: 0.05in;
  }
  .subhead {
    font-size: 7.5pt;
    color: var(--mp-color-muted);
    font-style: italic;
    margin-bottom: 0.04in;
    letter-spacing: 0.02em;
  }

  .tweet {
    margin: 0.05in 0;
    padding: 0.04in 0.07in;
    border-left: var(--mp-card-rule-strong) solid var(--mp-color-rule);
    background: var(--mp-color-surface-card);
    break-inside: avoid;
    page-break-inside: avoid;
  }
  .tweet-header { display: flex; justify-content: space-between; margin-bottom: 0.025in; }
  .tweet-author { font-size: 7pt; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; }
  .tweet-meta { font-size: 6pt; color: var(--mp-color-muted); }
  .tweet-text { font-size: var(--mp-card-meta-size); line-height: 1.4; color: var(--mp-color-text); }
  .tweet-stats { font-size: 6pt; color: var(--mp-color-muted); margin-top: 0.02in; }

  .tweet-pair {
    display: flex;
    gap: 0.1in;
    margin: 0.05in 0;
    break-inside: avoid;
    page-break-inside: avoid;
  }
  .tweet-pair .tweet {
    flex: 1 1 calc(50% - 0.05in);
    min-width: 0;
    background: var(--mp-color-surface-card);
  }
  .tweet-pair .tweet:only-child { flex: 1 1 100%; }

  .full-read {
    margin: 0.04in 0;
    padding: 0;
    border: none;
    break-inside: avoid;
    page-break-inside: avoid;
  }
  .featured-reads {
    margin-top: 0.03in;
  }
  .featured-reads .full-read + .full-read {
    margin-top: 0.08in;
    padding-top: 0.06in;
    border-top: 1px solid #d8d8d8;
  }
  .full-read-title { font-size: var(--mp-card-title-size); font-weight: 700; color: var(--mp-color-text); margin-bottom: 0.02in; line-height: 1.3; }
  .full-read-source { font-size: var(--mp-card-meta-size); color: var(--mp-color-muted); margin-bottom: 0.04in; text-transform: uppercase; letter-spacing: 0.04em; }
  .full-read-body { font-size: var(--mp-card-body-size); line-height: 1.45; color: var(--mp-color-text); }
  .full-read-body p { margin-bottom: 0.04in; }
  .full-read-body p:last-child { margin-bottom: 0; }

  .hn-section {
    break-after: avoid;
    page-break-after: avoid;
  }
  .hn-cards {
    columns: 2;
    column-gap: var(--mp-column-gap);
  }
  .hn-section > h1,
  .hn-cards h1 {
    font-size: var(--mp-section-title-size);
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--mp-color-text);
    border-bottom: 1px solid var(--mp-color-rule);
    padding-bottom: 0.02in;
    margin-bottom: 0.03in;
    column-span: all;
  }
  .hn-cards > p {
    font-size: 7pt;
    color: var(--mp-color-muted);
    letter-spacing: 0.02em;
    margin: 0 0 0.06in 0;
    column-span: all;
  }
  .hn-card {
    break-inside: avoid;
    page-break-inside: avoid;
    margin-bottom: 0.045in;
    padding-left: 0.04in;
    border-left: var(--mp-card-rule-weight) solid var(--mp-color-rule);
    background: var(--mp-color-surface-card);
  }
  .hn-card-header {
    display: flex;
    align-items: baseline;
    margin-bottom: 0.02in;
    gap: 0.05in;
    flex-wrap: wrap;
  }
  .hn-rank { font-weight: 700; font-size: 7.5pt; }
  .hn-domain { font-size: 6pt; color: var(--mp-color-muted); text-transform: uppercase; letter-spacing: 0.03em; margin-left: auto; }
  .hn-title { font-size: var(--mp-list-size); color: var(--mp-color-text); font-weight: 700; line-height: 1.28; }
  .hn-meta { font-size: 6.1pt; color: var(--mp-color-muted); margin-top: 0.015in; }
  .hn-tag {
    display: inline-block;
    font-size: 5.5pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    padding: 0.01in 0.04in;
    background: #8b0000;
    color: #f9f7f1;
    border-radius: 2px;
  }
  .hn-desc { font-size: 6.4pt; color: var(--mp-color-text); line-height: 1.26; margin-top: 0.02in; }

  .skool-post {
    margin: 0.05in 0;
    padding: 0.04in 0.07in;
    border-left: var(--mp-card-rule-strong) solid var(--mp-color-rule);
    background: var(--mp-color-surface-card);
  }
  .skool-post-header { display: flex; justify-content: space-between; margin-bottom: 0.03in; }
  .skool-author { font-size: var(--mp-list-size); font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; }
  .skool-meta { font-size: 6.5pt; color: var(--mp-color-muted); }
  .skool-title { font-size: var(--mp-card-body-size); font-weight: 700; color: var(--mp-color-text); margin-bottom: 0.03in; }
  .skool-body { font-size: var(--mp-card-meta-size); line-height: 1.5; color: var(--mp-color-text); }
  .skool-engagement { font-size: 6.5pt; color: var(--mp-color-muted); margin-top: 0.03in; }

  .win-card {
    margin: 0.03in 0;
    padding: 0.025in 0.05in;
    background: var(--mp-color-surface-card);
    border-left: var(--mp-card-rule-weight) solid var(--mp-color-rule);
  }
  .win-header { display: flex; gap: 0.1in; margin-bottom: 0.015in; }
  .win-title { font-size: var(--mp-card-meta-size); font-weight: 700; color: var(--mp-color-text); }
  .win-body { font-size: var(--mp-list-size); color: var(--mp-color-text); line-height: 1.4; }

  ul { margin: 0.02in 0 0.04in 0.18in; padding: 0; }
  li { font-size: var(--mp-list-size); line-height: 1.4; color: var(--mp-color-text); margin-bottom: 0.015in; }
  li::marker { color: var(--mp-color-muted); }

  .content-draft {
    margin: 0.04in 0;
    padding: 0.03in 0.06in;
    border-left: var(--mp-card-rule-weight) solid var(--mp-color-rule);
    background: var(--mp-color-surface-soft);
  }
  .activity-log {
    margin: 0.04in 0;
    padding: 0.03in 0.06in;
    border-left: var(--mp-card-rule-weight) solid var(--mp-color-rule);
    background: var(--mp-color-surface-soft);
  }
  .activity-log p { margin-bottom: 0.03in; }
  .activity-log p:last-child { margin-bottom: 0; }
  .draft-label { font-size: var(--mp-card-meta-size); font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--mp-color-muted); margin-bottom: 0.02in; }
  .draft-body { font-size: var(--mp-list-size); line-height: 1.45; color: var(--mp-color-text); }
  .draft-body p { margin-bottom: 0.03in; }
  .draft-body p:last-child { margin-bottom: 0; }

  .action-required {
    margin: 0.06in 0;
    padding: 0.04in 0.07in;
    border-left: 3px solid var(--mp-color-rule);
    background: var(--mp-color-surface-card);
  }
  .action-required h2 {
    font-size: 8pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--mp-color-text);
    margin-bottom: 0.04in;
    border-bottom: none;
    background: transparent;
    padding: 0;
  }
  .action-item { margin-bottom: 0.04in; }
  .action-label { font-weight: 700; font-size: var(--mp-list-size); color: var(--mp-color-text); }
  .action-body { font-size: var(--mp-list-size); color: var(--mp-color-text); margin-top: 0.01in; }

  .ref-list { margin: 0.04in 0; }
  .ref-item { font-size: var(--mp-list-size); color: var(--mp-color-text); margin-bottom: 0.02in; }
  .ref-label { font-weight: 700; }

  .page-break { page-break-before: always; }

---

<div class="page-1-header">
  <div class="page-1-title">Morning Paper</div>
  <div class="page-1-date">{DATE} — {TIME} — {LOCATION}</div>
  <div class="page-1-rule"></div>
</div>

<div class="info-row">
  <!-- Banner, tweet count, HN count, runtime -->
</div>

## I. SIGNALS
<!-- Tweets: short ones (< 180 chars) paired 2-col, long ones full-width -->

## II. FEATURED READS
<div class="featured-reads">
<!-- Featured Reads -->
</div>

<!-- HN section: keep BOTH the section header and subhead as HTML below. Do not emit markdown ## headings or markdown italic subheads here. -->
<div class="hn-section">
  <h1>III. HACKER NEWS — TOP 20</h1>
  <p class="subhead">news.ycombinator.com — {DATE} — via HN Algolia API</p>
  <div class="hn-cards" style="columns: 2; column-gap: 0.08in;">
    <!-- HN cards go here -->
  </div>
</div>

## IV. REFERENCES
<!-- Reference links -->
