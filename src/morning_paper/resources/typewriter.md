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

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: 'Courier Prime', 'Courier New', Courier, monospace;
    font-size: 9pt;
    line-height: 1.38;
    color: #1a1a1a;
    background: #ffffff;
  }

  @media print {
    body { background: #ffffff !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    @page { size: Letter; margin: 0.6in 0.55in 0.6in 0.55in; }
  }

  .page-1-header { margin-bottom: 0.08in; }
  .page-1-title {
    font-size: 22pt;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: none;
    color: #000000;
    font-family: 'Courier Prime', 'Courier New', Courier, monospace;
  }
  .page-1-date {
    font-size: 7.5pt;
    color: #555;
    margin-top: 0.02in;
    letter-spacing: 0.03em;
  }
  .page-1-rule {
    border-bottom: 1.5px solid #000000;
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
  .info-block { font-size: 8pt; line-height: 1.5; }
  .info-label { font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; font-size: 6.5pt; color: #555; }
  .info-value { color: #000000; }
  .info-alert { color: #8b0000; font-weight: 700; }

  h1 {
    font-family: 'Courier Prime', 'Courier New', Courier, monospace;
    font-size: 9pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-top: 0.12in;
    margin-bottom: 0.03in;
    border-bottom: 1px solid #000000;
    padding-bottom: 0.02in;
    background: transparent;
    padding-right: 0.05in;
  }
  .subhead {
    font-size: 7.5pt;
    color: #555;
    font-style: italic;
    margin-bottom: 0.04in;
    letter-spacing: 0.02em;
  }

  .tweet {
    margin: 0.05in 0;
    padding: 0.04in 0.07in;
    border-left: 2.5px solid #000000;
    background: rgba(0,0,0,0.015);
    break-inside: avoid;
    page-break-inside: avoid;
  }
  .tweet-header { display: flex; justify-content: space-between; margin-bottom: 0.025in; }
  .tweet-author { font-size: 7pt; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; }
  .tweet-meta { font-size: 6pt; color: #555; }
  .tweet-text { font-size: 8pt; line-height: 1.4; color: #000000; }
  .tweet-stats { font-size: 6pt; color: #555; margin-top: 0.02in; }

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
    background: rgba(0,0,0,0.015);
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
  .full-read-title { font-size: 9pt; font-weight: 700; color: #000000; margin-bottom: 0.02in; line-height: 1.3; }
  .full-read-source { font-size: 7pt; color: #555; margin-bottom: 0.04in; text-transform: uppercase; letter-spacing: 0.04em; }
  .full-read-body { font-size: 8.5pt; line-height: 1.45; color: #000000; }
  .full-read-body p { margin-bottom: 0.04in; }
  .full-read-body p:last-child { margin-bottom: 0; }

  .hn-section {
    break-after: avoid;
    page-break-after: avoid;
  }
  .hn-cards {
    columns: 2;
    column-gap: 0.08in;
  }
  .hn-section > h1,
  .hn-cards h1 {
    font-size: 9pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #000000;
    border-bottom: 1px solid #000000;
    padding-bottom: 0.02in;
    margin-bottom: 0.03in;
    column-span: all;
  }
  .hn-cards > p {
    font-size: 7pt;
    color: #555;
    letter-spacing: 0.02em;
    margin: 0 0 0.06in 0;
    column-span: all;
  }
  .hn-card {
    break-inside: avoid;
    page-break-inside: avoid;
    margin-bottom: 0.045in;
    padding-left: 0.04in;
    border-left: 2px solid #000000;
    background: rgba(0,0,0,0.015);
  }
  .hn-card-header {
    display: flex;
    align-items: baseline;
    margin-bottom: 0.02in;
    gap: 0.05in;
    flex-wrap: wrap;
  }
  .hn-rank { font-weight: 700; font-size: 7.5pt; }
  .hn-domain { font-size: 6pt; color: #555; text-transform: uppercase; letter-spacing: 0.03em; margin-left: auto; }
  .hn-title { font-size: 7.5pt; color: #000000; font-weight: 700; line-height: 1.28; }
  .hn-meta { font-size: 6.1pt; color: #555; margin-top: 0.015in; }
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
  .hn-desc { font-size: 6.4pt; color: #000000; line-height: 1.26; margin-top: 0.02in; }

  .skool-post {
    margin: 0.05in 0;
    padding: 0.04in 0.07in;
    border-left: 2.5px solid #000000;
    background: rgba(0,0,0,0.015);
  }
  .skool-post-header { display: flex; justify-content: space-between; margin-bottom: 0.03in; }
  .skool-author { font-size: 7.5pt; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; }
  .skool-meta { font-size: 6.5pt; color: #555; }
  .skool-title { font-size: 8.5pt; font-weight: 700; color: #000000; margin-bottom: 0.03in; }
  .skool-body { font-size: 8pt; line-height: 1.5; color: #000000; }
  .skool-engagement { font-size: 6.5pt; color: #555; margin-top: 0.03in; }

  .win-card {
    margin: 0.03in 0;
    padding: 0.025in 0.05in;
    background: rgba(0,0,0,0.015);
    border-left: 2px solid #000000;
  }
  .win-header { display: flex; gap: 0.1in; margin-bottom: 0.015in; }
  .win-title { font-size: 8pt; font-weight: 700; color: #000000; }
  .win-body { font-size: 7.5pt; color: #000000; line-height: 1.4; }

  ul { margin: 0.02in 0 0.04in 0.18in; padding: 0; }
  li { font-size: 7.5pt; line-height: 1.4; color: #000000; margin-bottom: 0.015in; }
  li::marker { color: #555; }

  .content-draft {
    margin: 0.04in 0;
    padding: 0.03in 0.06in;
    border-left: 2px solid #000000;
    background: rgba(0,0,0,0.012);
  }
  .activity-log {
    margin: 0.04in 0;
    padding: 0.03in 0.06in;
    border-left: 2px solid #000000;
    background: rgba(0,0,0,0.012);
  }
  .activity-log p { margin-bottom: 0.03in; }
  .activity-log p:last-child { margin-bottom: 0; }
  .draft-label { font-size: 7pt; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #555; margin-bottom: 0.02in; }
  .draft-body { font-size: 7.5pt; line-height: 1.45; color: #000000; }
  .draft-body p { margin-bottom: 0.03in; }
  .draft-body p:last-child { margin-bottom: 0; }

  .action-required {
    margin: 0.06in 0;
    padding: 0.04in 0.07in;
    border-left: 3px solid #000000;
    background: rgba(0,0,0,0.015);
  }
  .action-required h2 {
    font-size: 8pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #000000;
    margin-bottom: 0.04in;
    border-bottom: none;
    background: transparent;
    padding: 0;
  }
  .action-item { margin-bottom: 0.04in; }
  .action-label { font-weight: 700; font-size: 7.5pt; color: #000000; }
  .action-body { font-size: 7.5pt; color: #000000; margin-top: 0.01in; }

  .ref-list { margin: 0.04in 0; }
  .ref-item { font-size: 7.5pt; color: #000000; margin-bottom: 0.02in; }
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
